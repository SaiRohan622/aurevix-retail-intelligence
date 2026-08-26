# AUREVIX Data Dictionary — Silver Schema Specification

## 1. Overview
The Silver Layer contains cleaned, typed, normalized, deduplicated, and quality-controlled datasets processed by PySpark. All records have passed the Data Quality Firewall (DQ001-DQ012) or have been isolated in Quarantine.

Storage Format: Apache Parquet (Snappy Compressed)
Location: `data/silver/<entity_name>/`

---

## 2. Silver Entities & Schemas

### `silver_orders` (Partitioned by `order_year_month`)
| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `order_id` | String | No | Unique order identifier (Primary Key) |
| `customer_id` | String | No | Customer transaction identifier (Foreign Key) |
| `order_status` | String | No | Lowercase order lifecycle status |
| `order_purchase_timestamp` | Timestamp | No | Order placement timestamp (UTC) |
| `order_approved_at` | Timestamp | Yes | Payment approval timestamp (UTC) |
| `order_delivered_carrier_date` | Timestamp | Yes | Carrier handoff timestamp (UTC) |
| `order_delivered_customer_date`| Timestamp | Yes | Final customer delivery timestamp (UTC) |
| `order_estimated_delivery_date`| Timestamp | Yes | Estimated delivery deadline (UTC) |
| `order_year_month` | String | No | Partition key (`YYYY-MM`) |
| `delivery_days` | Integer | Yes | Calculated delivery duration in days |
| `is_delayed` | Boolean | Yes | True if delivered after estimated date |
| `_silver_processed_at` | Timestamp | No | Processing ingestion timestamp |

### `silver_order_items` (Partitioned by `order_year_month`)
| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `order_id` | String | No | Order identifier (Foreign Key) |
| `order_item_id` | Integer | No | Sequential item number within order |
| `product_id` | String | No | Product identifier (Foreign Key) |
| `seller_id` | String | No | Seller identifier (Foreign Key) |
| `shipping_limit_date` | Timestamp | Yes | Seller shipping deadline (UTC) |
| `price` | Decimal(10,2)| No | Item item price in BRL |
| `freight_value` | Decimal(10,2)| No | Freight/shipping fee in BRL |
| `total_item_amount` | Decimal(10,2)| No | Calculated sum of price + freight |
| `order_year_month` | String | No | Partition key (`YYYY-MM`) |
| `_silver_processed_at` | Timestamp | No | Processing ingestion timestamp |

### `silver_customers`
| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `customer_id` | String | No | Customer order-level key (Primary Key) |
| `customer_unique_id` | String | No | Unique physical customer identifier |
| `customer_zip_code_prefix` | String | Yes | 5-digit zip code prefix |
| `customer_city` | String | Yes | Normalized city name (InitCap) |
| `customer_state` | String | No | 2-letter Brazilian state code (Upper) |
| `_silver_processed_at` | Timestamp | No | Processing timestamp |

### `silver_products`
| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `product_id` | String | No | Product identifier (Primary Key) |
| `product_category_name` | String | No | English translated category name |
| `product_category_name_pt` | String | Yes | Original Portuguese category name |
| `product_name_length` | Integer | Yes | Character length of product name |
| `product_description_length` | Integer | Yes | Character length of description |
| `product_photos_qty` | Integer | Yes | Number of published photos |
| `product_weight_g` | Decimal(10,2)| Yes | Weight in grams |
| `product_length_cm` | Decimal(10,2)| Yes | Length in centimeters |
| `product_height_cm` | Decimal(10,2)| Yes | Height in centimeters |
| `product_width_cm` | Decimal(10,2)| Yes | Width in centimeters |
| `product_volume_cm3` | Decimal(12,2)| Yes | Calculated volume (L * H * W) |
| `_silver_processed_at` | Timestamp | No | Processing timestamp |

### `silver_sellers`
| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `seller_id` | String | No | Seller identifier (Primary Key) |
| `seller_zip_code_prefix` | String | Yes | 5-digit zip code prefix |
| `seller_city` | String | Yes | Normalized city name (InitCap) |
| `seller_state` | String | No | 2-letter Brazilian state code (Upper) |
| `_silver_processed_at` | Timestamp | No | Processing timestamp |

### `silver_order_payments`
| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `order_id` | String | No | Order identifier (Foreign Key) |
| `payment_sequential` | Integer | No | Payment sequence number |
| `payment_type` | String | No | Lowercase payment method |
| `payment_installments` | Integer | No | Number of installments |
| `payment_value` | Decimal(10,2)| No | Payment transaction amount in BRL |
| `_silver_processed_at` | Timestamp | No | Processing timestamp |

### `silver_order_reviews`
| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `review_id` | String | No | Review identifier |
| `order_id` | String | No | Associated order identifier (Foreign Key) |
| `review_score` | Integer | No | Customer satisfaction score (1 to 5) |
| `review_comment_title` | String | Yes | Review title |
| `review_comment_message` | String | Yes | Review comment body |
| `review_creation_date` | Timestamp | Yes | Review invitation sent timestamp |
| `review_answer_timestamp` | Timestamp | Yes | Review response timestamp |
| `_silver_processed_at` | Timestamp | No | Processing timestamp |

### `silver_geolocation`
| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `geolocation_zip_code_prefix` | String | No | 5-digit zip code prefix |
| `geolocation_state` | String | No | Brazilian state code |
| `geolocation_city` | String | Yes | Associated city name |
| `latitude` | Double | No | Spatial centroid average latitude |
| `longitude` | Double | No | Spatial centroid average longitude |
| `_coordinate_samples_count` | Long | No | Number of coordinate samples aggregated |
| `_silver_processed_at` | Timestamp | No | Processing timestamp |

### `silver_category_translation`
| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `product_category_name` | String | No | Normalized Portuguese category name |
| `product_category_name_english` | String | No | Normalized English translated category name |
| `_silver_processed_at` | Timestamp | No | Processing timestamp |
