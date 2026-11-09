# European Services Trade Analytics — Architecture Design

**Status:** Planning baseline. Implementation starts with the Eurostat extractor.

## 1. Confirmed architecture

```text
Eurostat bulk/API
        ↓
Python extractor
        ↓
ADLS Gen2
        ↓
Fivetran
        ↓
Snowflake
        ↓
dbt
        ↓
Power BI
```

- **Source:** Eurostat international trade in services datasets.
- **Ingestion:** Python extractor writing partitioned files to ADLS Gen2, followed by Fivetran.
- **Warehouse:** Snowflake.
- **Transformation:** dbt.
- **BI:** Power BI, to be implemented later.
- **Development:** Docker Dev Container.
- **Automation:** GitHub Actions.

## 2. Snowflake workload separation

The project will use separate warehouses for workload isolation:

| Warehouse      | Workload                  |
| -------------- | ------------------------- |
| `INGEST_WH`    | Fivetran ingestion        |
| `TRANSFORM_WH` | dbt execution             |
| `ANALYTICS_WH` | Power BI and read traffic |

Final sizing and auto-suspend settings will be validated from observed usage.

## 3. Snowflake data zones

The initial data-zone design is:

```text
RAW → dbt-managed transformation schemas → BI-facing schemas
```

- **RAW:** Data loaded by Fivetran.
- **Transformation schemas:** Data modeled by dbt.
- **BI-facing schemas:** Data exposed to Power BI after the model design is approved.

Exact schema names, materializations, and retention policies remain to be decided.

## 4. Eurostat extraction and ingestion

The extractor and ingestion flow will:

- Download Eurostat TSV or SDMX data.
- Validate columns and types, then write partitioned files and a manifest to ADLS Gen2.
- Handle retries, caching, and sync state.
- Load the ADLS files into Snowflake through Fivetran.
- Prevent duplicate records and log failures without exposing credentials.

The extractor will be developed and tested before Snowflake modeling begins.

## 5. Repository structure

```text
global-trade-analytics/
├── .devcontainer/
├── .github/workflows/
├── ingestion/fivetran_connector/
├── dbt/
├── infrastructure/
├── scripts/
├── docs/
├── .gitignore
├── pyproject.toml
└── README.md
```

The exact contents of each directory will be created incrementally.

## 6. Development and delivery standards

### Dev Container

The Dev Container will provide a consistent environment for:

- Python connector development.
- Fivetran SDK dependencies.
- dbt and Snowflake adapter tooling.
- Tests, linting, and formatting.

### GitHub Actions

GitHub Actions will eventually validate:

- Python formatting, linting, and unit tests.
- Fivetran connector packaging.
- dbt parsing, compilation, and tests.
- Deployment workflows after the project is implemented.

The workflow details will be defined when each implementation area is added.

## 7. Decisions intentionally deferred

The following are not finalized yet:

- Raw table names and column contracts.
- Whether raw API payloads are preserved as `VARIANT`.
- dbt staging, intermediate, and mart model names.
- Final dimensional or star-schema design.
- Fact-table grain and unique key.
- Incremental strategy and clustering keys.
- Power BI storage mode, relationships, and refresh strategy.
- Environment and schema naming conventions.
- Final warehouse sizes and cost thresholds.

These decisions will be made from the actual API response structure and tested data volume rather than assumed in advance.

## 8. Implementation sequence

1. Set up the Python project and Dev Container.
2. Implement the API client.
3. Implement pagination and sync state.
4. Add the Fivetran connector entry point.
5. Test a small API extraction.
6. Configure the Snowflake destination.
7. Inspect and document the loaded source data.
8. Design the dbt models from the observed data.
9. Add CI/CD checks.
10. Design the Power BI model and dashboards.
