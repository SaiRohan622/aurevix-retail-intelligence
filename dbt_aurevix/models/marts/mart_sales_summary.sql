{{ config(materialized='table') }}

select
    count(distinct order_id) as total_orders,
    sum(order_item_quantity) as total_units_sold,
    sum(item_price) as total_product_revenue,
    sum(freight_value) as total_freight_revenue,
    sum(total_item_value) as total_gross_revenue,
    round(sum(total_item_value) / nullif(count(distinct order_id), 0), 2) as average_order_value
from {{ ref('stg_order_items') }}
