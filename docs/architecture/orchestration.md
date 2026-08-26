# AUREVIX — Master Orchestration Architecture (Apache Airflow)

## 1. Batch Master DAG Pipeline (`aurevix_batch_pipeline`)

```mermaid
flowchart TD
    start([Start]) --> V1[validate_raw_data]
    V1 --> B1[bronze_ingestion]
    B1 --> B2[bronze_validation]
    B2 --> S1[silver_transformation]
    S1 --> S2[silver_quality_validation]
    S2 --> G1[gold_transformation]
    G1 --> G2[gold_reconciliation]
    G2 --> P1[load_postgres]
    P1 --> D1[dbt_run]
    D1 --> D2[dbt_test]
    D2 --> success([pipeline_success])
```

## 2. DAG Topology & Responsibilities
- **`aurevix_batch_pipeline`**: End-to-end daily batch orchestrator running raw validation, PySpark Medallion transforms, PostgreSQL warehouse loading, and dbt analytics mart compilation.
- **`aurevix_streaming_monitor`**: Monitors Kafka topic latency, consumer freshness, and streaming metrics report.
- **`aurevix_data_quality`**: Evaluates cross-layer data quality thresholds and generates `data/monitoring/airflow_quality_report.json`.
