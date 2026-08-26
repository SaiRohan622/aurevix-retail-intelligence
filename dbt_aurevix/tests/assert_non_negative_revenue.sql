-- Measure validation: gross revenue must not be negative
select
    sales_fact_key,
    total_item_value
from {{ ref('stg_order_items') }}
where total_item_value < 0.00
