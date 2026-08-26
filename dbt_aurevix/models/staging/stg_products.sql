{{ config(materialized='view') }}

select
    product_key,
    product_id,
    product_category_name,
    product_category_name_pt,
    product_weight_g,
    product_volume_cm3
from {{ source('gold', 'dim_product') }}
