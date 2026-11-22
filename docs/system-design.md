# European Services Trade Analytics — System Design

## 1. Architecture

```text
Eurostat API
     |
     v
Python Extractor
     |
     v
Azure Data Lake Storage Gen2
     |
     v
Fivetran
     |
     v
Snowflake
     |
     v
dbt Core (models + Semantic Layer / MetricFlow)
     |
     v
Snowflake Analytics
     |
     v
Power BI
```

**GitHub Actions** manages pipeline orchestration and CI/CD across the project.

## 2. Technology Stack

| Technology           | Responsibility                               |
| -------------------- | -------------------------------------------- |
| Python               | Eurostat API extraction and ADLS integration |
| Azure Data Lake Gen2 | Raw data storage                             |
| Fivetran             | ADLS-to-Snowflake ingestion                  |
| Snowflake            | Cloud data warehouse                         |
| dbt Core             | Data transformation and modeling             |
| GitHub Actions       | Workflow automation and CI/CD                |
| Power BI             | Analytics and visualization                  |
| Docker Dev Container | Development environment                      |

## 3. Snowflake Architecture

Separate warehouses for workload isolation:

| Warehouse      | Responsibility            |
| -------------- | ------------------------- |
| `INGEST_WH`    | Fivetran ingestion        |
| `TRANSFORM_WH` | dbt transformations       |
| `ANALYTICS_WH` | BI and analytical queries |

Data architecture:

```text
RAW → STAGING → INTERMEDIATE → MARTS
```

- **RAW:** Source data ingested through Fivetran.
- **STAGING:** Source-level transformations.
- **MARTS:** Analytical datasets for BI consumption. Star schema: `dim_year` (doubles
  as the MetricFlow time spine via `year_start`),
  `dim_service` (BPM6 hierarchy + ICT flag), `dim_partner`, `dim_geo`, `dim_flow`,
  `dim_nace_activity`, `dim_enterprise_characteristic`, fed by
  `fct_bop_services_trade` (year × service × flow × partner × geo) and
  `fct_stec_services_trade` (year × characteristic × NACE × flow × partner × geo).
  Facts are long-grain, values in EUR.

### Semantic layer (dbt Semantic Layer / MetricFlow)

Every mart model carries an inline `semantic_model` block (dbt v1.12+ spec) in
`dbt/models/marts/**/_*.yml`. Entities join facts to dims; `year_start` (Jan 1) on
`dim_year` is both the time dimension and the MetricFlow time spine.

The two facts carry 21 metrics: gross trade, observation and missing-observation
counts; exports/imports/balance (via `flow__flow_direction`); derived net balance
and YoY growth (`offset_window: 1 year`); three share metrics; a partner breakdown;
and two EU27 aggregate-row variants.

Five rules govern every value metric. They are all baked into the metric
definitions, never left to BI:

| Rule                                                          | Why                                                                                                                                                                                                                                                                              |
| ------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `*__is_reporting_level` flags (service, NACE, characteristic) | Each dimension nests totals over their members. `SOX` sits beside the 13 BPM6 sections; `TOTAL`/`A_B`/`UNK` beside the NACE sections; the STEC `size_class` and `enterprise_control` partitions are alternative cuts of the same population. Summing across a level over-counts. |
| `geo__is_eu_aggregate = false`                                | `EU27_2020` is a pre-computed row that overlaps the member rows.                                                                                                                                                                                                                 |
| `partner__partner_code = 'WRL_REST'`                          | `WRL_REST`, `EXT_EU27_2020`, `EU27_2020` and the regional aggregates all overlap.                                                                                                                                                                                                |
| A `flow__flow_direction` filter                               | The fact stores CRE, DEB and BAL as separate rows. A metric without a flow filter sums all three: the balance is already exports minus imports, so it is counted twice and two opposite directions are added.                                                                      |
| NULL `value_eur`                                              | Marks confidential/missing. SUM skips it; never coalesce to 0.                                                                                                                                                                                                                   |

The flags are **declared in the seeds**, not inferred from position. `SOX` is a
level-1 child of `S` but duplicates its 11 siblings, so deriving the flag from
`service_level = 1` would over-count BOP exports by ~42%.

Reporter and partner are **populations, not hierarchies**, so no boolean can
express them — the filter is the grain definition. Pinning `WRL_REST` (present for
every reporter: 38/38 BOP, 30/30 STEC) rather than `partner_type = 'country'`
(available for only 5 of 30 STEC reporters) is what keeps STEC from silently
dropping 25 reporters. Partner-country detail lives in the `*_by_partner` metric,
and the `*_eu27` variants read the pre-computed EU27 row for headline cards.

#### Surrogate keys

Both facts use `observation_key`, a `dbt_utils.generate_surrogate_key` over the full
grain plus `frequency`/`currency` (bop) or `frequency`/`unit` (stec). The inputs are
deliberately wider than the mart grain so the key survives those columns varying.
Uniqueness and non-null are enforced by `data_tests` on the column;
`unique_combination_of_columns` guards the natural grain.

#### Unit conversion safeguards

The EUR conversion is a `LEFT JOIN` to `units.csv`
(`obs_value * multiplier_to_eur`). An unmapped unit code produces a NULL multiplier,
so `value_eur` becomes NULL and silently vanishes from every SUM — indistinguishable
from a legitimately missing observation.

The single guard is `accepted_values: [MIO_EUR, THS_EUR]` on both `currency` (bop)
and `unit` (stec), so a new Eurostat unit fails the build instead of under-reporting.
`tests/mart_value_eur_flag_consistency.sql` already covers the downstream symptom: it
fails on any row where `value_eur IS NULL` disagrees with `is_value_missing`, which
is exactly what a NULL multiplier produces.

#### Deduplication

Staging deduplicates Fivetran re-ingestion by recency
(`ORDER BY _fivetran_synced DESC, _file DESC`), which is correct — the same Eurostat
file re-delivered under a new checksum must collapse to one row.

The facts do **not** deduplicate. An earlier `ROW_NUMBER()` guard partitioned by the
natural grain and preferred `MIO_EUR`, but the intermediate grain already includes
`currency`/`unit`, so two rows differing only by unit are legitimately distinct —
not duplicates. The guard was a no-op that would have silently discarded a real
anomaly if it ever fired; `unique_combination_of_columns` on the fact grain now
covers genuine grain violations loudly.

Dimensions keep natural keys and are Type 1 (overwrite), not SCD2: they are Eurostat
reference/code-list data with no history worth tracking. If history is ever needed it
belongs on the raw snapshot (`snap_bop_observations`), not the marts.

#### Known Apache Ossie limitations

`dbt/target/osi_document.json` (written at parse time by dbt's MSI→OSI converter)
is lossy. MetricFlow queries are unaffected, but consumers of the Ossie document
should know:

| Limitation                                                             | Effect                                                                                                                                                                        |
| ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Entities export as plain unmarked fields                               | Snowflake Semantic Views read join keys as measures. Not fixable in YAML — dbt rejects a name used as both entity and dimension. Declare join keys as dimensions in the view. |
| `offset_window` is dropped (OSI 0.1.1)                                 | YoY metrics export as `(x - x) / x` → always 0. Treat YoY as MetricFlow-only.                                                                                                 |
| All 9 semantic models merge into one document                          | Adds 4 fact↔fact relationships on shared entities. Do not consume those edges.                                                                                                |
| `value_eur` / `is_value_missing` appear only inside metric expressions | Not queryable as dimensions.                                                                                                                                                  |
| Rewritten only when the semantic manifest validates                    | Needs dbt Cloud / CI with `dbt_cloud.yml`; a local `dbt parse` leaves the file stale.                                                                                         |

`dbt parse`/`dbt build` validate the semantic manifest, and
`dbt ls --resource-type semantic_model --resource-type metric` runs in CI
(`dbt-pr.yml`, `dbt.yml`) so a broken definition fails the pipeline.

The compiled `dbt/target/manifest.json` (uploaded as the `prod-manifest` artifact)
carries all `semantic_models` and `metrics` nodes — this is what BI tools read to
query governed metrics by name.

### dbt targets: dev vs prod

dbt runs against two targets defined in the profile (template `dbt/profiles.example.yml`,
copied to `~/.dbt/profiles.yml` on the host; all secrets via environment variables):

| Target | Warehouse      | Schemas written in `EUROPEAN_SERVICES_ANALYTICS` | Used by                                 |
| ------ | -------------- | ------------------------------------------------ | --------------------------------------- |
| `dev`  | `TRANSFORM_WH` | `dev_staging`, `dev_intermediate`, `dev_marts`   | local development only (default target) |
| `prod` | `TRANSFORM_WH` | `staging`, `intermediate`, `marts`               | CI/CD on merge to `main` only           |

- `dev` is the default target (`target: dev` in the profile), so a plain `dbt build` in the
  container can never write the prod schemas.
- The `dev_` prefix is applied by `dbt/macros/generate_schema_name.sql` whenever
  `target.name == 'dev'`; the layer schemas come from the `+schema` configs in `dbt_project.yml`.
- Both targets read sources from the shared, Fivetran-owned `RAW` database (read-only).
- Production deploys **only** via GitHub Actions on `main` (`.github/workflows/dbt.yml` runs
  `dbt build --target prod` and uploads `target/manifest.json` as the `prod-manifest` artifact).
  The workflow's `workflow_dispatch` is restricted to `main` and the job has an
  `if: github.ref == 'refs/heads/main'` guard, so a manual run on a feature branch can never
  reach prod. On paid plans, add required reviewers to the GitHub `production` environment.
- **Slim CI on pull requests** (`.github/workflows/dbt-pr.yml`): runs ruff, black --check,
  pytest and `dbt parse`, then a Slim CI build —
  `dbt build --target dev --select state:modified+ --defer --state <prod manifest>` —
  so only models changed in the PR plus their downstream dependents are built (into
  `DEV_*` schemas), while unchanged upstream refs are deferred (read from prod, not rebuilt).
  The prod manifest is downloaded cross-workflow from the latest successful `dbt.yml` run
  on `main` (`dawidd6/action-download-artifact`, needs `actions: read`); until that exists,
  the PR job falls back to a full dev-target build.
  Lint/tests must pass before the Slim CI job starts (`needs:`).
  Required GitHub secrets: `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_ROLE`,
  `DBT_SNOWFLAKE_PRIVATE_KEY`, `DBT_PRIVATE_KEY_PASSPHRASE`.

## 4. Data Sources

Primary source:

- `bop_its6_det` — International trade in services (BPM6).

Additional datasets:

- `ext_stec01` — Trade by enterprise size.
- `ext_stec02` — Trade by enterprise activity.
- `ext_stec03` — Trade by enterprise ownership.

The analytical focus is European international trade in services, particularly computer, telecommunications and information services.

### Reference seeds (`dbt/seeds/`)

The intermediate layer joins seed-backed dimensions (service items, partners, geo
areas, flows, units, frequencies, NACE, stec characteristics). The CSVs are static
reference data checked into the repo, labelled from the official Eurostat codelists.
If a new code appears in the data, the `relationships` tests on the intermediate
models fail the build — extend the relevant CSV by hand in that case.

## 5. Pipeline Workflow

GitHub Actions coordinates the execution of the pipeline:

1. GitHub Actions (monthly cron or manual dispatch) runs the Python extractor.
2. Extracted files are uploaded to ADLS Gen2.
3. Fivetran polls ADLS Gen2 on its own schedule (managed Azure Blob Storage connector) and loads new files into the Snowflake RAW database.
4. dbt transforms the data and compiles the semantic manifest.
5. The BI tool consumes the marts and governed metrics.

CI/CD runs alongside it: `.github/workflows/dbt-pr.yml` lints and builds on pull
requests, and `dbt.yml` deploys with `dbt build --target prod` on merges to `main`
and manual dispatch only.

## 6. Repository Structure

```text
european-services-trade-analytics/
├── .github/
│   └── workflows/
├── assets/
├── config/
├── src/
│   └── extract/
│       └── eurostat/
├── dbt/
├── tests/
├── docs/
├── Dockerfile
├── docker-compose.yaml
├── .gitignore
├── pyproject.toml
├── README.md
└── uv.lock
```

## 7. Engineering Principles

- Modular and maintainable implementation.
- Clear separation of pipeline responsibilities.
- Reproducible development environment.
- Version-controlled code and configuration.
- Automated testing and validation.
- Secure credential management.
- Cost-conscious cloud resource usage.

## 8. Power BI Layer

The report layer mirrors the semantic layer's grain rules (see §3) — every value
measure bakes in the same reporting-level, reporter and partner filters, and never
sums an aggregate row together with the members it contains. Beyond that:

- Share measures cannot inherit MetricFlow's protection: a metric filter scopes only
  the numerator, so a share sliced on its own axis collapses to 100%. In DAX the
  denominator needs `REMOVEFILTERS` on the sliced dimension.
- BOP and STEC measures are never mixed in one visual.
- The report is saved as PBIP so it is version-controlled alongside the dbt project.
