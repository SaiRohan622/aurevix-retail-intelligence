"""
AUREVIX — Source and Bronze Schema Specifications
Defines required source column sets and types for the 9 Olist tables.
"""

from typing import Dict, List, Set

# Expected column names for raw CSV files
EXPECTED_SOURCE_SCHEMAS: Dict[str, List[str]] = {
    "olist_orders_dataset.csv": [
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date"
    ],
    "olist_order_items_dataset.csv": [
        "order_id",
        "order_item_id",
        "product_id",
        "seller_id",
        "shipping_limit_date",
        "price",
        "freight_value"
    ],
    "olist_products_dataset.csv": [
        "product_id",
        "product_category_name",
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm"
    ],
    "olist_customers_dataset.csv": [
        "customer_id",
        "customer_unique_id",
        "customer_zip_code_prefix",
        "customer_city",
        "customer_state"
    ],
    "olist_order_payments_dataset.csv": [
        "order_id",
        "payment_sequential",
        "payment_type",
        "payment_installments",
        "payment_value"
    ],
    "olist_order_reviews_dataset.csv": [
        "review_id",
        "order_id",
        "review_score",
        "review_comment_title",
        "review_comment_message",
        "review_creation_date",
        "review_answer_timestamp"
    ],
    "olist_sellers_dataset.csv": [
        "seller_id",
        "seller_zip_code_prefix",
        "seller_city",
        "seller_state"
    ],
    "olist_geolocation_dataset.csv": [
        "geolocation_zip_code_prefix",
        "geolocation_lat",
        "geolocation_lng",
        "geolocation_city",
        "geolocation_state"
    ],
    "product_category_name_translation.csv": [
        "product_category_name",
        "product_category_name_english"
    ]
}

# Target Bronze entity names mapping
RAW_FILE_TO_BRONZE_ENTITY: Dict[str, str] = {
    "olist_orders_dataset.csv": "bronze_orders",
    "olist_order_items_dataset.csv": "bronze_order_items",
    "olist_products_dataset.csv": "bronze_products",
    "olist_customers_dataset.csv": "bronze_customers",
    "olist_order_payments_dataset.csv": "bronze_order_payments",
    "olist_order_reviews_dataset.csv": "bronze_order_reviews",
    "olist_sellers_dataset.csv": "bronze_sellers",
    "olist_geolocation_dataset.csv": "bronze_geolocation",
    "product_category_name_translation.csv": "bronze_category_translation"
}

# Partitioning specification for Bronze Parquet output
BRONZE_PARTITION_COLUMNS: Dict[str, List[str]] = {
    "bronze_orders": ["ingestion_year_month"],
    "bronze_order_items": ["ingestion_year_month"],
    "bronze_products": [],
    "bronze_customers": [],
    "bronze_order_payments": [],
    "bronze_order_reviews": [],
    "bronze_sellers": [],
    "bronze_geolocation": [],
    "bronze_category_translation": []
}
