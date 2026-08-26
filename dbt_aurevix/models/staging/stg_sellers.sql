{{ config(materialized='view') }}

select
    seller_key,
    seller_id,
    seller_zip_code_prefix,
    seller_city,
    seller_state,
    location_key
from {{ source('gold', 'dim_seller') }}
