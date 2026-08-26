{{ config(materialized='view') }}

select
    sales_fact_key,
    order_id,
    order_item_id,
    customer_key,
    product_key,
    seller_key,
    order_date_key,
    location_key,
    order_item_quantity,
    item_price,
    freight_value,
    gross_item_value,
    total_item_value,
    order_year_month
from {{ source('gold', 'fact_sales') }}
