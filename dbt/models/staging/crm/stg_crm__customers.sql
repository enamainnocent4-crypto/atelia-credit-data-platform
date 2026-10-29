-- Clients : une ligne par client.
select
    customer_id,
    first_name,
    last_name,
    birth_date::date                    as birth_date,
    lower(email)                        as email,
    city,
    postal_code,
    segment                             as customer_segment,
    monthly_income::integer             as monthly_income,
    home_branch_code,
    created_at::timestamp               as created_at
from {{ source('crm', 'customers') }}
