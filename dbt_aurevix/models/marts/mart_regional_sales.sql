{{ config(materialized='table') }}

select
    c.customer_state as state,
    count(distinct i.order_id) as total_orders,
    sum(i.order_item_quantity) as units_sold,
    sum(i.total_item_value) as regional_gross_revenue
from {{ ref('stg_order_items') }} i
join {{ ref('stg_customers') }} c on i.customer_key = c.customer_key
group by c.customer_state
