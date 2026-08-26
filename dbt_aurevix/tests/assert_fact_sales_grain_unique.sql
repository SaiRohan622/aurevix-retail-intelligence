-- Grain test: order_id + order_item_id must be unique
select
    order_id,
    order_item_id,
    count(*) as occurrences
from {{ source('gold', 'fact_sales') }}
group by order_id, order_item_id
having count(*) > 1
