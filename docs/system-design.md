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
  Facts are long-grain, values in EUR; NULL `value_eur` marks confidential/missing
  observations and is never coalesced to 0. Aggregate levels (EU27, service total,
  partner aggregates) overlap their members — BI must filter to one level.

### Semantic layer (dbt Semantic Layer / MetricFlow)

Every mart model carries an inline `semantic_model` block (dbt v1.12+ spec) in
`dbt/models/marts/**/_*.yml`: entities join facts to dims (`observation`,
`calendar_year`, `service`, `flow`, `partner`, `geo`, `nace`, and the composite
`characteristic` for stec), and `year_start` (Jan 1 of the year) on `dim_year` is
both the time dimension and the time spine (one row per year at day granularity is
enough for annual data). On top of the two facts, 18 metrics are
defined: trade value / observations / missing observations, exports / imports /
balance (via `flow__flow_direction` filters), derived net balance and YoY growth
(`offset_window: 1 year`), and ratio metrics for ICT share of exports and extra-EU
share (stec: NACE section J share). Metric and dimension descriptions carry the two
data rules: NULL `value_eur` = confidential/missing (SUM ignores it, never coalesce
to 0) and aggregate levels must never be summed together with their members.

- `dbt parse`/`dbt build` validate the semantic manifest; `dbt ls --resource-type
  semantic_model --resource-type metric` is run in CI (`dbt-pr.yml`, `dbt.yml`) so a
  broken metric definition fails the pipeline.
- The compiled `dbt/target/manifest.json` (uploaded as the `prod-manifest` artifact)
  contains all `semantic_models` and `metrics` nodes — this is what BI tools consume
  to query governed metrics by name (the certified Power BI connector requires
  dbt Cloud; self-hosted tools like Lightdash OSS read the dbt project/manifest
  directly against Snowflake).

### dbt targets: dev vs prod

dbt runs against two targets defined in the profile (template `dbt/profiles.example.yml`,
copied to `~/.dbt/profiles.yml` on the host; all secrets via environment variables):

| Target | Warehouse      | Schemas written in `EUROPEAN_SERVICES_ANALYTICS` | Used by                              |
| ------ | -------------- | ---------------------------------------------- | --------------------------------------- |
| `dev`  | `TRANSFORM_WH` | `dev_staging`, `dev_intermediate`, `dev_marts` | local development only (default target) |
| `prod` | `TRANSFORM_WH` | `staging`, `intermediate`, `marts`             | CI/CD on merge to `main` only           |

- `dev` is the default target (`target: dev` in the profile), so a plain `dbt build` in the
  container can never write the prod schemas.
- The `dev_` prefix is applied by `dbt/macros/generate_schema_name.sql` whenever
  `target.name == 'dev'`; the layer schemas come from the `+schema` configs in `dbt_project.yml`.
- Both targets read sources from the shared, Fivetran-owned `RAW` database (read-only).
- Local loop (from the repo root):
  `docker compose run --rm dbt dbt build --select <model>`,
  `dbt test --select <model>`, `dbt show --select <model> --limit 20` — all land in `dev_*`.
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
- One-time Snowflake setup for the dev environment (run as `ACCOUNTADMIN`, replace `DBT_ROLE`):

  ```sql
  -- The dbt role already owns EUROPEAN_SERVICES_ANALYTICS, so it can create the
  -- dev_* schemas itself. Both targets use TRANSFORM_WH (see the table above).
  ```

## 4. Data Sources

Primary source:

- `bop_its6_det` — International trade in services (BPM6).

Additional datasets:

- `ext_stec01` — Trade by enterprise size.
- `ext_stec02` — Trade by enterprise activity.
- `ext_stec03` — Trade by enterprise ownership.
- `ext_ser_mos` — Trade by mode of supply.

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
3. Fivetran polls ADLS Gen2 on its own schedule (managed Azure Blob Storage connector) and loads new files into Snowflake RAW database.
4. dbt transforms data within Snowflake and compiles the semantic manifest
   (semantic models + metrics in `dbt/target/manifest.json`).
5. The BI tool consumes the analytical models / governed metrics.

CI/CD workflows independently validate project code and dbt models: `.github/workflows/dbt.yml`
deploys with `dbt build --target prod` on merges to `main` (and manual dispatch) only.

## 6. Repository Structure

```text
european-services-trade-analytics/
├── .github/
│   └── workflows/
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

Directories and implementation files will be introduced as development progresses.

## 7. Implementation Sequence

1. Python project and Dev Container setup.
2. Eurostat API client and extractor.
3. ADLS Gen2 integration.
4. Fivetran connector configuration.
5. Snowflake setup and ingestion validation.
6. dbt project initialization.
7. Data transformation and modeling.
8. GitHub Actions orchestration and CI/CD.
9. Power BI semantic model and dashboards.

## 8. Engineering Principles

- Modular and maintainable implementation.
- Clear separation of pipeline responsibilities.
- Reproducible development environment.
- Version-controlled code and configuration.
- Automated testing and validation.
- Secure credential management.
- Cost-conscious cloud resource usage.
