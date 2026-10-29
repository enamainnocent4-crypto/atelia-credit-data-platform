-- Prêts : une ligne par prêt décaissé.
select
    loan_id,
    application_id,
    customer_id,
    branch_code,
    product_code,
    principal_amount::numeric(12, 2)        as principal_amount,
    annual_interest_rate::numeric(6, 4)     as annual_interest_rate,
    duration_months::integer                as duration_months,
    monthly_payment::numeric(12, 2)         as monthly_payment,
    fee_amount::numeric(12, 2)              as fee_amount,
    disbursement_date::date                 as disbursement_date,
    first_due_date::date                    as first_due_date,
    updated_at::timestamp                   as updated_at,
    _loaded_at                              as loaded_at
from {{ source('core_banking', 'loans') }}
