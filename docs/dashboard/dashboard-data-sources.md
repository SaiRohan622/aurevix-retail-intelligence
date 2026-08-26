# AUREVIX — Dashboard Data Sources

1. **PostgreSQL Analytics Warehouse:** `gold.fact_sales`, `gold.dim_customer`, `gold.dim_product`, `gold.dim_seller`, `gold.dim_date`, `gold.dim_location`.
2. **dbt Analytics Marts:** `analytics.mart_daily_sales`, `analytics.mart_sales_summary`, `analytics.mart_regional_sales`, `analytics.mart_product_performance`, `analytics.mart_customer_value`.
3. **Real-Time Streaming Telemetry:** `data/monitoring/streaming_metrics.json`.
4. **Pipeline Audit Datastore:** `data/monitoring/pipeline_run_history.jsonl`.
