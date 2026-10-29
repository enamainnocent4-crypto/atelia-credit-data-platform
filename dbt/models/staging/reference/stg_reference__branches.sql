-- Agences : une ligne par agence.
select
    branch_code,
    branch_name,
    city,
    region,
    opening_date::date as opening_date
from {{ source('reference', 'branches') }}
