# AUREVIX — Phase 6 Test Plan & Verification Strategy

- **Airflow Unit Tests:** `tests/unit/test_airflow_dags.py` (DAG defaults, task execution).
- **Observability Unit Tests:** `tests/unit/test_observability.py` (JSONL run logging).
- **DQ Threshold Unit Tests:** `tests/unit/test_dq_thresholds.py` (Threshold enforcement).
- **Integration Tests:** `tests/integration/test_airflow_pipeline.py` & `tests/integration/test_dbt_pipeline.py`.
