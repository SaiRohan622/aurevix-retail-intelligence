{{ config(materialized='view') }}

select
    customer_key,
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state,
    location_key,
    is_current
from {{ source('gold', 'dim_customer') }}
