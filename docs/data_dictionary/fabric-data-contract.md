# AUREVIX — Microsoft Fabric Cloud Data Contract

## 1. Contract Overview
- **Target Lakehouse:** `AUREVIX_Lakehouse`
- **Schema Version:** `1.0.0`
- **Ownership:** AUREVIX Platform Data Engineering Team

---

## 2. Primary Entities & Schemas

### `fact_sales`
- **Grain:** One row per `(order_id, order_item_id)`
- **Primary Key:** `sales_fact_key` (SHA-256 surrogate key)
- **Foreign Keys:**
  - `customer_key` -> `dim_customer.customer_key`
  - `product_key` -> `dim_product.product_key`
  - `seller_key` -> `dim_seller.seller_key`
  - `order_date_key` -> `dim_date.date_key`
  - `location_key` -> `dim_location.location_key`
- **Measures:** `item_price` (Decimal), `freight_value` (Decimal), `total_item_value` (Decimal)
- **Validated Fact Count:** 112,650 rows ($15,843,553.24 gross revenue).

### `dim_customer`
- **Grain:** One row per customer version (SCD Type 2)
- **Primary Key:** `customer_key`
- **Columns:** `customer_id`, `customer_unique_id`, `customer_city`, `customer_state`, `is_current`, `effective_start_date`, `effective_end_date`

### `dim_product`
- **Grain:** One row per SKU
- **Primary Key:** `product_key`
- **Columns:** `product_id`, `product_category_name`, `product_category_name_english`, `product_volume_cm3`

### `dim_seller`
- **Grain:** One row per merchant
- **Primary Key:** `seller_key`
- **Columns:** `seller_id`, `seller_city`, `seller_state`, `location_key`

### `dim_date`
- **Grain:** One row per calendar day
- **Primary Key:** `date_key` (Format: `YYYYMMDD`)
- **Columns:** `full_date`, `year`, `quarter`, `month_number`, `month_name`, `day_of_month`, `day_name`, `is_weekend`

### `dim_location`
- **Grain:** One row per geographic postal node
- **Primary Key:** `location_key`
- **Columns:** `zip_code_prefix`, `city`, `state`, `latitude`, `longitude`
