-- Catalogue des produits de crédit.
select
    product_code,
    product_name,
    customer_segment,
    min_amount,
    max_amount,
    min_duration_months,
    max_duration_months,
    min_annual_rate,
    max_annual_rate,
    fee_rate
from {{ ref('stg_reference__products') }}
