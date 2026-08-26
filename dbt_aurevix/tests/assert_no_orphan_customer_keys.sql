-- Referential integrity: all customer keys in fact must exist in dim_customer
select
    i.sales_fact_key,
    i.customer_key
from {{ ref('stg_order_items') }} i
left join {{ ref('stg_customers') }} c on i.customer_key = c.customer_key
where c.customer_key is null
