{{ config(materialized='table') }}

-- Échéances avec leur date de règlement : une ligne par échéance.
-- Sert au calcul des jours de retard (DPD, days past due).
--
-- Règle : une échéance est réglée à la date du premier paiement reçu pour elle.
-- Les paiements antidatés (en quarantaine pour les flux financiers) COMPTENT ici :
-- le paiement existe, seule sa date est incohérente. Les ignorer créerait de faux
-- impayés, puis de faux défauts et de fausses pertes sur 15 prêts.
with payments as (
    select
        installment_id,
        payment_date,
        row_number() over (partition by payment_id order by loaded_at) as copy_number
    from {{ ref('stg_core_banking__payments') }}
),

settlement as (
    select installment_id, min(payment_date) as settled_date
    from payments
    where copy_number = 1
    group by installment_id
)

select
    i.installment_id,
    i.loan_id,
    i.installment_number,
    i.due_date,
    i.principal_due,
    i.interest_due,
    s.settled_date
from {{ ref('stg_core_banking__installments') }} as i
left join settlement as s
    on s.installment_id = i.installment_id
