-- Paiements reçus — table de faits transactionnelle.
-- Grain : une ligne par paiement fiable (dédoublonné, hors quarantaine).
select
    p.payment_id,
    p.payment_date,
    p.loan_id,
    p.installment_id,
    c.customer_sk,
    l.customer_id,
    coalesce(b.branch_code, 'UNKNOWN')          as branch_code,
    l.product_code,
    p.payment_method,

    -- Mesures : chaque paiement couvre une échéance (capital + intérêts)
    p.amount,
    i.principal_due                             as principal_amount,
    i.interest_due                              as interest_amount,

    -- Ponctualité
    i.due_date,
    p.payment_date - i.due_date                 as days_late,
    case when p.payment_date > i.due_date then 1 else 0 end as is_late_payment
from {{ ref('int_payments__deduplicated') }} as p
join {{ ref('stg_core_banking__installments') }} as i
    on i.installment_id = p.installment_id
join {{ ref('stg_core_banking__loans') }} as l
    on l.loan_id = p.loan_id
left join {{ ref('dim_branch') }} as b
    on b.branch_code = l.branch_code
left join {{ ref('dim_customer') }} as c
    on c.customer_id = l.customer_id
   and p.payment_date >= c.valid_from
   and p.payment_date < c.valid_to
