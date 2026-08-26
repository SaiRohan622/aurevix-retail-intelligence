{{ config(materialized='table') }}

select
    c.customer_unique_id,
    count(distinct i.order_id) as lifetime_orders_count,
    sum(i.total_item_value) as observed_clv,
    min(i.order_year_month) as first_order_month,
    max(i.order_year_month) as latest_order_month
from {{ ref('stg_order_items') }} i
join {{ ref('stg_customers') }} c on i.customer_key = c.customer_key
group by c.customer_unique_id
