{{ config(materialized='table') }}

select
    order_date_key,
    order_year_month,
    daily_orders,
    daily_units_sold,
    daily_product_revenue,
    daily_freight_revenue,
    daily_gross_revenue,
    round(daily_gross_revenue / nullif(daily_orders, 0), 2) as daily_aov
from {{ ref('int_daily_sales') }}
