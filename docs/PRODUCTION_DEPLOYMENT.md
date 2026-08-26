# AUREVIX — Production Deployment Runbook

## 1. Production Architecture Overview
- Containerized multi-service deployment orchestrating PostgreSQL 16, Zookeeper, Apache Kafka, Airflow, and Streamlit Operations Dashboard.
- Immutable Snappy Parquet storage mounted from volume or lakehouse object store.

## 2. Production Security Hardening
- Mandate strong `POSTGRES_PASSWORD` (fail-fast validator rejects default password in production mode).
- Enable `AUREVIX_STRUCTURED_LOGGING=true` for JSON logging to central aggregation tools (Datadog/Elastic).
- Ensure port bindings are bound to internal network interfaces.
