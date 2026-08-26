# AUREVIX — Airflow Disaster Recovery Guide

1. **Raw Validation Failure:** Check source CSV file paths and non-zero byte size.
2. **Bronze/Silver/Gold Failures:** Rerun the respective PySpark batch pipeline; idempotency ensures zero row inflation.
3. **dbt Failure:** Inspect `dbt_aurevix/target/run_results.json` and verify PostgreSQL connection.
