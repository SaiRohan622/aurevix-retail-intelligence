# AUREVIX — Failure Recovery & Retry Policies

## 1. Retry Policies
- **Airflow Tasks:** `retries=2`, `retry_delay=timedelta(minutes=5)`.
- **Idempotency Strategy:** PySpark `mode("overwrite")` on partition levels prevents duplicate row creation during pipeline retries.
