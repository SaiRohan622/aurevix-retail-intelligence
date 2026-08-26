# AUREVIX — Disaster Recovery & Backup Runbook

## 1. Database Backup & Restore
- **Backup Command:** `powershell scripts/backup_postgres.ps1`
- **Restore Command:** `pg_restore -h localhost -p 5432 -U aurevix_admin -d aurevix_dw < backup_file.sql`

## 2. Idempotent Data Lakehouse Rebuild
If the data lakehouse is corrupted, re-execute the batch pipelines in order:
```powershell
python src/batch/ingest_raw.py
python src/batch/spark_bronze_to_silver.py
python src/batch/spark_silver_to_gold.py
```
PySpark `mode("overwrite")` ensures exact reconstruction with zero row inflation.
