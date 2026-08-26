# AUREVIX — Bronze Data Layer Schema (Implemented)

## 1. Bronze Layer Principles
- **Format:** Apache Parquet (Snappy compressed, partitioned where applicable).
- **Semantics:** Raw, append-only ingestion preserving source structure without transformation.
- **Audit Columns Injected:**
  - `_ingested_at` (TIMESTAMP/STRING): ISO-8601 UTC timestamp of ingestion.
  - `_source_file` (VARCHAR): Source CSV filename.
  - `_source_system` (VARCHAR): Ingestion system origin (`olist_ecommerce_batch`).
  - `_schema_version` (VARCHAR): Ingestion schema version (`1.0.0`).
  - `ingestion_year_month` (VARCHAR): Partitioning key for time-series datasets.

---

## 2. Bronze Table Implementation Inventory

| Bronze Entity | Source File | Partition Key | Compression | Idempotency Strategy |
| :--- | :--- | :--- | :--- | :--- |
| `bronze_orders` | `olist_orders_dataset.csv` | `ingestion_year_month` | SNAPPY | Deterministic dataset partition overwrite |
| `bronze_order_items` | `olist_order_items_dataset.csv` | `ingestion_year_month` | SNAPPY | Deterministic dataset partition overwrite |
| `bronze_products` | `olist_products_dataset.csv` | *Unpartitioned* | SNAPPY | Atomic table overwrite |
| `bronze_customers` | `olist_customers_dataset.csv` | *Unpartitioned* | SNAPPY | Atomic table overwrite |
| `bronze_order_payments`| `olist_order_payments_dataset.csv` | *Unpartitioned* | SNAPPY | Atomic table overwrite |
| `bronze_order_reviews` | `olist_order_reviews_dataset.csv` | *Unpartitioned* | SNAPPY | Atomic table overwrite |
| `bronze_sellers` | `olist_sellers_dataset.csv` | *Unpartitioned* | SNAPPY | Atomic table overwrite |
| `bronze_geolocation` | `olist_geolocation_dataset.csv` | *Unpartitioned* | SNAPPY | Atomic table overwrite |
| `bronze_category_translation` | `product_category_name_translation.csv` | *Unpartitioned* | SNAPPY | Atomic table overwrite |

---

## 3. Observability & Manifest
Every raw-to-bronze ingestion run generates an Ingestion Manifest at `data/monitoring/ingestion_manifest.json` capturing execution duration, row counts, and status per entity.
