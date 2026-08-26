# AUREVIX — Data Directory & Dataset Specification

## 1. Dataset Selection: Olist Brazilian E-Commerce Dataset

**AUREVIX** uses the **Olist Brazilian E-Commerce Public Dataset** as its primary batch benchmark dataset.

- **Source:** Brazilian E-Commerce Public Dataset by Olist (hosted on Kaggle).
- **Source URL:** `https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce`
- **License:** Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0).
- **Characteristics:** ~100,000 real-world commercial orders placed between 2016 and 2018 across Brazilian marketplaces, with multi-item transactions, localized geolocations, payment installments, product dimensional metadata, and customer review scores.

---

## 2. Required Source Files & Placement

When downloaded, place raw CSV files directly into `data/raw/` with exact filenames:

| Source File Name | Entity Description | Key Columns |
| :--- | :--- | :--- |
| `olist_orders_dataset.csv` | Primary order events & lifecycle timestamps | `order_id`, `customer_id`, `order_status`, `order_purchase_timestamp` |
| `olist_order_items_dataset.csv` | Line-item detail per order | `order_id`, `order_item_id`, `product_id`, `seller_id`, `price`, `freight_value` |
| `olist_products_dataset.csv` | Product dimensions, categories, and physical attributes | `product_id`, `product_category_name`, `product_weight_g` |
| `olist_customers_dataset.csv` | Customer identifiers and geographical mapping | `customer_id`, `customer_unique_id`, `customer_zip_code_prefix`, `customer_city`, `customer_state` |
| `olist_order_payments_dataset.csv` | Payment methods, installments, and values | `order_id`, `payment_sequential`, `payment_type`, `payment_installments`, `payment_value` |
| `olist_order_reviews_dataset.csv` | Customer feedback and review scores | `review_id`, `order_id`, `review_score`, `review_creation_date` |
| `olist_sellers_dataset.csv` | Merchant registry and geolocation | `seller_id`, `seller_zip_code_prefix`, `seller_city`, `seller_state` |
| `olist_geolocation_dataset.csv` | Brazilian postal code geolocation coordinates | `geolocation_zip_code_prefix`, `geolocation_lat`, `geolocation_lng`, `geolocation_city`, `geolocation_state` |
| `product_category_name_translation.csv` | Portuguese to English category taxonomy | `product_category_name`, `product_category_name_english` |

---

## 3. Acquisition Workflow

### Option A: Kaggle CLI (Recommended)
```powershell
# Ensure kaggle.json is placed in ~/.kaggle/kaggle.json
kaggle datasets download -d olistbr/brazilian-ecommerce -p data/raw/ --unzip
```

### Option B: Manual Download
1. Navigate to `https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce`.
2. Download the dataset zip archive.
3. Extract all CSV files into `D:\Projects\aurevix\data\raw\`.

---

## 4. Medallion Directory Structure & Storage Strategy

- `data/raw/`: Immutable raw source CSVs downloaded from source.
- `data/bronze/`: Snappy-compressed Parquet files containing raw source records enriched with technical audit metadata (`_ingested_at`, `_source_file`, `_source_system`, `_schema_version`).
- `data/silver/`: Cleaned, strongly typed, normalized, deduplicated Parquet datasets partitioned by `order_year_month` or `event_date`.
- `data/gold/`: Business-ready Kimball Star Schema Parquet and PostgreSQL warehouse tables (`fact_sales`, `dim_customer` SCD2, `dim_product`, `dim_date`, `dim_location`).
- `data/quarantine/`: Defective records violating schema or Data Quality Firewall rules, partitioned by `rejection_date` with violation error codes and failure descriptions.
- `data/monitoring/`: Operational pipeline run metrics, data quality score logs, streaming lag records, and anomaly telemetry.
- `data/checkpoints/`: Spark Structured Streaming state checkpoints ensuring fault tolerance and exactly-once processing guarantees.

> [!NOTE]
> All raw CSVs, parquet partitions, and checkpoints are excluded from Git commits via `.gitignore`.
