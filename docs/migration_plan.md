# Migration Plan: UN Comtrade → Eurostat (International Trade in Services)

## Decision
Switch the data provider from UN Comtrade (paid bulk) to **Eurostat –
International trade in services**. Eurostat data is free (public SDMX/TSV bulk
download) and the pipeline architecture stays unchanged:

```
Eurostat (bulk/API) → Python extractor → ADLS Gen2 → Fivetran → Snowflake (raw) → dbt → BI
```

## 1. Do we need to delete anything?
**Short answer: nothing to delete right now.** The repository only contains an
empty `README.md`. There is no UN Comtrade code, secrets or assets to remove.

If/when UN Comtrade code is present on `main`, delete these instead of editing:
- `src/extract/comtrade/` (or equivalent) and its tests
- UN Comtrade API key/secret references (`.env`, Key Vault entries, CI vars)
- Fivetran/HVR source configs pointing at the Comtrade ADLS path
- dbt sources/models tagged `comtrade`
- BI datasets/dashboards titled "UN Comtrade …"
- Any Comtrade-specific docs under `docs/`

Rule of thumb: **remove, don't rename**, then regenerate from the Eurostat side.

## 2. Eurostat source & datasets
- Domain: International trade in services
  https://ec.europa.eu/eurostat/web/international-trade-in-services/database
- Key datasets (TSV/SDMX):
  - `bop_its` – historical international trade in services (BPM5/BPM6 era)
  - `bop_its6_det` – detailed trade in services since 2010 (BPM6) — **primary**
  - `bop_its6_geo` – geographical breakdown (if used)
- Access: Eurostat bulk download (TSV) or SDMX 2.1 REST API
  `https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/<dataset>`
- No API key required (public). Respect Eurostat download/cache guidance.

## 3. ADLS Gen2 layout (unchanged concept, new source path)
```
adls://<account>/raw/eurostat/
  ├─ bop_its/       yyyy=....  (tsv + metadata)
  ├─ bop_its6_det/  yyyy=...
  └─ manifest.json  (dataset code, retrieved_at, checksum, rowcount)
```
Use immutable, partitioned folders so Fivetran can detect new files.

## 4. Step-by-step implementation
1. **Confirm scope** – which datasets, countries/regions, service categories,
   years. (Country list: EU27 + EEA; partner = WORLD/rest of world.)
2. **Python extractor**
   - Add dependency `eurostat` (or use `requests` + SDMX URL).
   - Script `src/extract/eurostat/fetch.py`:
     - resolve datasets from config (YAML)
     - download TSV/SDMX, validate columns & types
     - write partitioned parquet/CSV + manifest to ADLS
     - retry/backoff + logging
   - Unit tests for parsing/mapping.
3. **Secrets/config** – move dataset list & ADLS creds to env / Key Vault;
   remove any Comtrade keys.
4. **Fivetran** – point an ADLS Gen2 connector to
   `raw/eurostat/...`, schema naming `eurostat_raw`.
5. **Snowflake raw** – create `RAW_EUROSTAT` database/schema; grant roles.
6. **dbt**
   - `sources.yml` for eurostat tables
   - staging models (rename to common column names)
   - marts (facts/dims: service_category, reporter, partner, period)
   - tests (unique, not_null, relationships, freshness)
7. **BI** – repoint datasets to new marts; update KPIs labels.
8. **CI/CD** – add extractor job to scheduler (cron), data freshness checks.
9. **Docs** – update `docs/architecture.md` and README; deprecate Comtrade docs.

## 5. Validation before cutover
- Row-count reconciliation vs Eurostat source for a sample period
- Null checks on keys (reporter, partner, service, period)
- Re-run dbt `--full-refresh` on a dev schema first
- BI smoke test on a staging dashboard

## 6. Effort & owners (fill in)
| Step | Owner | Est. |
|------|-------|------|
| Extractor script | data-eng | 2d |
| dbt models | analytics-eng | 2d |
| BI update | BI | 1d |
| Testing/cutover | QA | 1d |

## 7. Rollback
Keep last UN Comtrade snapshot in ADLS (read-only, 30 days) and keep old BI
dashboard version pinned until Eurostat dashboard validated.
