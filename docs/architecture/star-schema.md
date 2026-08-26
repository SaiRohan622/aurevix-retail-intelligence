# AUREVIX — Star Schema Dimensional Model (Kimball Architecture)

## 1. Fact Table Grain
- **Table Name:** `fact_sales`
- **Fact Grain:** **Exactly ONE row per order-item line transaction (`order_id`, `order_item_id`)**.
- **Primary Key:** `sales_fact_key` (SHA-256 hash of `order_id || order_item_id`)
- **Row Count:** **112,650 rows** (0 grain violations, 0 variance against `silver_order_items`).

---

## 2. Entity-Relationship Diagram (Mermaid)

```mermaid
erDiagram
    fact_sales }o--|| dim_customer : "customer_key"
    fact_sales }o--|| dim_product : "product_key"
    fact_sales }o--|| dim_seller : "seller_key"
    fact_sales }o--|| dim_date : "order_date_key"
    fact_sales }o--|| dim_location : "location_key"

    fact_sales {
        string sales_fact_key PK
        string order_id
        int order_item_id
        string customer_key FK
        string product_key FK
        string seller_key FK
        int order_date_key FK
        string location_key FK
        string order_status
        timestamp order_purchase_timestamp
        timestamp order_delivered_customer_date
        timestamp order_estimated_delivery_date
        int delivery_days
        boolean is_delayed
        int order_item_quantity
        decimal item_price
        decimal freight_value
        decimal gross_item_value
        decimal total_item_value
        string order_year_month "Partition Key"
        timestamp _gold_processed_at
    }

    dim_customer {
        string customer_key PK
        string customer_id
        string customer_unique_id
        string customer_zip_code_prefix
        string customer_city
        string customer_state
        string location_key FK
        boolean is_current "SCD2 Flag"
        timestamp effective_start_date "SCD2 Start"
        timestamp effective_end_date "SCD2 End"
        timestamp _gold_processed_at
    }

    dim_product {
        string product_key PK
        string product_id
        string product_category_name
        string product_category_name_pt
        int product_name_length
        int product_description_length
        int product_photos_qty
        decimal product_weight_g
        decimal product_length_cm
        decimal product_height_cm
        decimal product_width_cm
        decimal product_volume_cm3
        timestamp _gold_processed_at
    }

    dim_seller {
        string seller_key PK
        string seller_id
        string seller_zip_code_prefix
        string seller_city
        string seller_state
        string location_key FK
        timestamp _gold_processed_at
    }

    dim_date {
        int date_key PK
        date full_date
        int day_of_month
        int day_of_week
        string day_name
        int week_of_year
        int month_number
        string month_name
        int quarter
        int year
        boolean is_weekend
        timestamp _gold_processed_at
    }

    dim_location {
        string location_key PK
        string zip_code_prefix
        string state
        string city
        double latitude
        double longitude
        long coordinate_samples_count
        timestamp _gold_processed_at
    }
```
