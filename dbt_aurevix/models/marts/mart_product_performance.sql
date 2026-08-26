{{ config(materialized='table') }}

select
    p.product_category_name as category_name,
    count(distinct i.order_id) as orders_count,
    sum(i.order_item_quantity) as units_sold,
    sum(i.total_item_value) as category_revenue
from {{ ref('stg_order_items') }} i
join {{ ref('stg_products') }} p on i.product_key = p.product_key
group by p.product_category_name
