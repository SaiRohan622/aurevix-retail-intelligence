# AUREVIX - Airflow Orchestration Specification

```mermaid
flowchart TD
    START([Start Pipeline]) --> INGEST[ingest_raw_data]
    INGEST --> DQ_BRONZE[validate_bronze_quality]
    DQ_BRONZE --> SPARK_SILVER[spark_bronze_to_silver_transform]
    SPARK_SILVER --> DQ_SILVER[validate_silver_quality]
    DQ_SILVER --> DBT_RUN[dbt_run_models]
    DBT_RUN --> DBT_TEST[dbt_test_models]
    DBT_TEST --> PG_LOAD[load_gold_to_postgres]
    PG_LOAD --> METRICS[refresh_analytical_metrics]
    METRICS --> END([Pipeline Complete])
```

## DAG: `aurevix_batch_pipeline`
- **Schedule:** `@daily`
- **Catchup:** `False`
- **Retries:** 2 retries with 5-minute exponential backoff
- **SLA & Alerting:** Built-in task execution tracking and failure callbacks
