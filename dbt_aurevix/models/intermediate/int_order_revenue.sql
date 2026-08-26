{{ config(materialized='view') }}

select
    order_id,
    count(order_item_id) as total_items_count,
    sum(order_item_quantity) as total_quantity,
    sum(item_price) as product_revenue,
    sum(freight_value) as freight_revenue,
    sum(total_item_value) as gross_order_revenue
from {{ ref('stg_order_items') }}
group by order_id
