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
dbt Core
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
- **MARTS:** Analytical datasets for BI consumption.

## 4. Data Sources

Primary source:

- `bop_its6_det` — International trade in services (BPM6).

Additional datasets:

- `ext_stec01` — Trade by enterprise size.
- `ext_stec02` — Trade by enterprise activity.
- `ext_stec03` — Trade by enterprise ownership.
- `ext_ser_mos` — Trade by mode of supply.

The analytical focus is European international trade in services, particularly computer, telecommunications and information services.

## 5. Pipeline Workflow

GitHub Actions coordinates the execution of the pipeline:

1. GitHub Actions (monthly cron or manual dispatch) runs the Python extractor.
2. Extracted files are uploaded to ADLS Gen2.
3. Fivetran polls ADLS Gen2 on its own schedule (managed Azure Blob Storage connector) and loads new files into Snowflake RAW database.
4. dbt transforms data within Snowflake.
5. Power BI consumes the analytical models.

CI/CD workflows independently validate project code and dbt models.

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
├── scripts/
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
