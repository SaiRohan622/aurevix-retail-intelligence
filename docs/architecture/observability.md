# AUREVIX — Platform Observability & Telemetry

## 1. Observability Datastore
- **Path:** `data/monitoring/pipeline_run_history.jsonl`
- **Format:** Append-only JSON Lines with execution timestamp, duration, status, row counts, and data quality status.
- **Reports:**
  - `ingestion_manifest.json` (Bronze Ingestion audit)
  - `silver_quality_report.json` (Silver DQ & Quarantine audit)
  - `gold_quality_report.json` (Gold Fact Grain & Revenue reconciliation)
  - `streaming_metrics.json` (Real-Time Kafka Streaming audit)
  - `airflow_quality_report.json` (Master Airflow cross-layer audit)
