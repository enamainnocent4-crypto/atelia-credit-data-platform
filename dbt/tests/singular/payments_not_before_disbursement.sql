{{ config(severity='warn') }}

-- Test singulier : un paiement ne peut pas être antérieur au versement des fonds.
-- Anomalie connue de la source : paiements antidatés.
-- Chaque ligne renvoyée est une anomalie.
select
    p.payment_id,
    p.loan_id,
    p.payment_date,
    l.disbursement_date
from {{ ref('stg_core_banking__payments') }} as p
join {{ ref('stg_core_banking__loans') }} as l
    on l.loan_id = p.loan_id
where p.payment_date < l.disbursement_date
