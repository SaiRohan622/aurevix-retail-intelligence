# AUREVIX — End-to-End Data Flow Specification

## 1. Batch Processing Flow (Bronze -> Silver)
1. **Bronze Ingestion:** PySpark ingests raw CSVs, preserves 100% source fidelity, and writes Snappy-compressed Parquet with audit headers (`_ingested_at`, `_source_file`, `_source_system`, `_schema_version`, `ingestion_year_month`).
2. **Dimension Transformation:** Normalizes and deduplicates `silver_category_translation`, `silver_customers`, `silver_sellers`, `silver_geolocation`, and `silver_products`.
3. **Orders Transformation:** Parses timestamps, cleans status codes, derives delivery metrics (`delivery_days`, `is_delayed`), and enforces foreign key integrity to customers.
4. **Fact & Child Entities:** Cleans `silver_order_items`, `silver_order_payments`, and `silver_order_reviews` with referential joins to valid parent entities.
5. **Quality Firewall Evaluation:** Evaluates rules DQ001-DQ012. Passes valid records to `data/silver/` and routes defective records to `data/quarantine/`.
6. **Observability:** Writes execution metrics to `data/monitoring/silver_quality_report.json`.
