{{ config(materialized='view') }}

select
    order_date_key,
    order_year_month,
    count(distinct order_id) as daily_orders,
    sum(order_item_quantity) as daily_units_sold,
    sum(item_price) as daily_product_revenue,
    sum(freight_value) as daily_freight_revenue,
    sum(total_item_value) as daily_gross_revenue
from {{ ref('stg_order_items') }}
group by order_date_key, order_year_month
