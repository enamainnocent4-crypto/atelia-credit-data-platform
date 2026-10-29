-- Paiements fiables : une ligne par paiement.
-- 1. Doublons : la source envoie parfois deux fois le même paiement ; on garde le premier reçu.
-- 2. Quarantaine : un paiement antérieur au versement des fonds est impossible ; il est
--    écarté ici et listé dans audit.quarantined_records.
with ranked as (
    select
        p.*,
        row_number() over (partition by p.payment_id order by p.loaded_at) as copy_number
    from {{ ref('stg_core_banking__payments') }} as p
)

select
    r.payment_id,
    r.loan_id,
    r.installment_id,
    r.installment_number,
    r.payment_date,
    r.amount,
    r.payment_method
from ranked as r
join {{ ref('stg_core_banking__loans') }} as l
    on l.loan_id = r.loan_id
where r.copy_number = 1
  and r.payment_date >= l.disbursement_date
