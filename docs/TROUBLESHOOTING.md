# AUREVIX — Platform Troubleshooting Guide

| Symptom | Diagnostic Step | Resolution |
| :--- | :--- | :--- |
| **PostgreSQL Connection Refused** | `python scripts/health_check.py` | Start postgres container: `docker compose up -d postgres` |
| **Kafka Topic Unavailable** | `docker compose logs kafka` | Ensure Zookeeper is healthy before Kafka broker start |
| **Dashboard Fallback Triggered** | Check Streamlit status banner | Dashboard automatically switches to Gold Parquet storage with zero downtime |
| **Data Stale Warning** | Inspect `data/monitoring/silver_quality_report.json` | Re-run Airflow batch master DAG |
