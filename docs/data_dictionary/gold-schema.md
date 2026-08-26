# AUREVIX Data Dictionary — Gold Schema Specification

## 1. Overview
The Gold Layer contains business-ready, highly optimized Kimball star schema dimensional models and fact tables. All Gold models are stored as Snappy-compressed Apache Parquet datasets at `data/gold/`.

---

## 2. Table Specifications

### `fact_sales` (Partitioned by `order_year_month`)
- **Grain:** Exactly ONE row per order-item line transaction.
- **Storage Path:** `data/gold/fact_sales/`

| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `sales_fact_key` | String | No | Surrogate Primary Key (SHA-256 of `order_id \|\| order_item_id`) |
| `order_id` | String | No | Business order identifier |
| `order_item_id` | Integer | No | Line item sequence number within order |
| `customer_key` | String | No | Surrogate foreign key referencing `dim_customer` |
| `product_key` | String | No | Surrogate foreign key referencing `dim_product` |
| `seller_key` | String | No | Surrogate foreign key referencing `dim_seller` |
| `order_date_key` | Integer | No | Foreign key referencing `dim_date` (`YYYYMMDD`) |
| `location_key` | String | No | Foreign key referencing `dim_location` |
| `order_status` | String | No | Order lifecycle status (e.g. `delivered`, `shipped`) |
| `order_purchase_timestamp` | Timestamp | No | Purchase datetime in UTC |
| `order_delivered_customer_date` | Timestamp | Yes | Actual customer delivery datetime |
| `order_estimated_delivery_date` | Timestamp | Yes | Carrier estimated delivery datetime |
| `delivery_days` | Integer | Yes | Actual delivery transit duration in days |
| `is_delayed` | Boolean | Yes | True if delivered after estimated date |
| `order_item_quantity` | Integer | No | Measure: item line quantity (literal 1) |
| `item_price` | Decimal(10,2) | No | Measure: item unit selling price in BRL |
| `freight_value` | Decimal(10,2) | No | Measure: freight fee allocated to item in BRL |
| `gross_item_value` | Decimal(10,2) | No | Measure: gross product value (`item_price`) |
| `total_item_value` | Decimal(10,2) | No | Measure: total transaction value (`price + freight`) |
| `order_year_month` | String | No | Partition key (`YYYY-MM`) |
| `_gold_processed_at` | Timestamp | No | Ingestion timestamp |

### `dim_customer`
| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `customer_key` | String | No | Surrogate Primary Key |
| `customer_id` | String | No | Order-level customer natural key |
| `customer_unique_id` | String | No | Physical customer unique natural key |
| `customer_zip_code_prefix`| String | Yes | 5-digit zip code |
| `customer_city` | String | Yes | Normalized city name |
| `customer_state` | String | No | 2-letter state code |
| `location_key` | String | No | Foreign key referencing `dim_location` |
| `is_current` | Boolean | No | SCD2 active record flag |
| `effective_start_date` | Timestamp | No | SCD2 validity start timestamp |
| `effective_end_date` | Timestamp | No | SCD2 validity expiration timestamp |
| `_gold_processed_at` | Timestamp | No | Ingestion timestamp |

### `dim_product`
| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `product_key` | String | No | Surrogate Primary Key (SHA-256 of `product_id`) |
| `product_id` | String | No | Product natural key |
| `product_category_name` | String | No | English translated category name |
| `product_category_name_pt` | String | Yes | Original Portuguese category name |
| `product_name_length` | Integer | Yes | Name character length |
| `product_description_length` | Integer | Yes | Description character length |
| `product_photos_qty` | Integer | Yes | Number of published photos |
| `product_weight_g` | Decimal(10,2) | Yes | Product weight in grams |
| `product_length_cm` | Decimal(10,2) | Yes | Length in centimeters |
| `product_height_cm` | Decimal(10,2) | Yes | Height in centimeters |
| `product_width_cm` | Decimal(10,2) | Yes | Width in centimeters |
| `product_volume_cm3` | Decimal(12,2) | Yes | Calculated volume (L * H * W) |
| `_gold_processed_at` | Timestamp | No | Ingestion timestamp |

### `dim_seller`
| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `seller_key` | String | No | Surrogate Primary Key (SHA-256 of `seller_id`) |
| `seller_id` | String | No | Seller natural key |
| `seller_zip_code_prefix`| String | Yes | 5-digit zip code |
| `seller_city` | String | Yes | Normalized city name |
| `seller_state` | String | No | 2-letter state code |
| `location_key` | String | No | Foreign key referencing `dim_location` |
| `_gold_processed_at` | Timestamp | No | Ingestion timestamp |

### `dim_date`
| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `date_key` | Integer | No | Surrogate Primary Key (`YYYYMMDD`) |
| `full_date` | Date | No | Calendar date |
| `day_of_month` | Integer | No | Day number (1-31) |
| `day_of_week` | Integer | No | Day of week number (1=Sunday..7=Saturday) |
| `day_name` | String | No | Full day name (e.g. `Monday`) |
| `week_of_year` | Integer | No | ISO week number (1-53) |
| `month_number` | Integer | No | Month number (1-12) |
| `month_name` | String | No | Full month name (e.g. `January`) |
| `quarter` | Integer | No | Quarter of year (1-4) |
| `year` | Integer | No | 4-digit calendar year |
| `is_weekend` | Boolean | No | True if Saturday or Sunday |
| `_gold_processed_at` | Timestamp | No | Ingestion timestamp |

### `dim_location`
| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `location_key` | String | No | Surrogate Primary Key (SHA-256 of `zip_code \|\| state`) |
| `zip_code_prefix` | String | No | 5-digit zip code prefix |
| `state` | String | No | 2-letter Brazilian state code |
| `city` | String | Yes | City name |
| `latitude` | Double | No | Spatial centroid average latitude |
| `longitude` | Double | No | Spatial centroid average longitude |
| `coordinate_samples_count`| Long | No | Number of samples aggregated |
| `_gold_processed_at` | Timestamp | No | Ingestion timestamp |
