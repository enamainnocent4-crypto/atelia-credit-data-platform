{{ config(schema='audit', materialized='table') }}

-- Table d'audit : chaque ligne écartée des calculs OU signalée, avec sa raison.
-- Rien ne disparaît ni n'est corrigé sans laisser de trace.
-- - payments : lignes ÉCARTÉES de fact_payment (doublons, paiements avant versement) ;
-- - applications : demandes SIGNALÉES mais conservées dans fact_credit_application
--   (montant demandé mis à vide, voir int_applications__validated).
with duplicate_copies as (
    select
        payment_id,
        row_number() over (partition by payment_id order by loaded_at) as copy_number
    from {{ ref('stg_core_banking__payments') }}
)

select 'payments' as table_name, payment_id as record_id,
       'Doublon : copie supprimée, le premier exemplaire est conservé' as reason
from duplicate_copies
where copy_number > 1

union all

select 'payments', p.payment_id,
       'Paiement daté avant le versement des fonds'
from {{ ref('stg_core_banking__payments') }} as p
join {{ ref('stg_core_banking__loans') }} as l on l.loan_id = p.loan_id
where p.payment_date < l.disbursement_date

union all

select 'applications', application_id,
       'Montant demandé négatif ou nul : montant mis à vide, demande conservée et signalée'
from {{ ref('stg_core_banking__applications') }}
where requested_amount <= 0
