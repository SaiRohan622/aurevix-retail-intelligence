{{ config(materialized='view') }}

select
    order_id,
    order_status,
    order_purchase_timestamp,
    order_delivered_customer_date,
    order_estimated_delivery_date,
    delivery_days,
    is_delayed,
    order_year_month
from {{ source('gold', 'fact_sales') }}
group by 1, 2, 3, 4, 5, 6, 7, 8
