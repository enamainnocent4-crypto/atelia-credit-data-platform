-- Catalogue produits : une ligne par produit. Les taux sont en décimal (0.0650 = 6,50 %).
select
    product_code,
    product_name,
    customer_segment,
    min_amount::numeric(12, 2)          as min_amount,
    max_amount::numeric(12, 2)          as max_amount,
    min_duration_months::integer        as min_duration_months,
    max_duration_months::integer        as max_duration_months,
    min_rate::numeric(6, 4)             as min_annual_rate,
    max_rate::numeric(6, 4)             as max_annual_rate,
    fee_rate::numeric(6, 4)             as fee_rate
from {{ source('reference', 'products') }}
