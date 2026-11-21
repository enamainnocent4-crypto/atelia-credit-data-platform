-- Réconciliation : chaque demande reçue se retrouve dans fact_credit_application.
-- Les demandes au montant invalide sont SIGNALÉES (is_requested_amount_valid = 0)
-- mais jamais exclues : aucune ne doit se perdre en route, aucune ne doit être comptée deux fois.
with received as (
    select count(*) as n from {{ ref('stg_core_banking__applications') }}
),
loaded as (
    select count(*) as n from {{ ref('fact_credit_application') }}
),
flagged_in_fact as (
    select count(*) as n from {{ ref('fact_credit_application') }} where is_requested_amount_valid = 0
),
flagged_in_audit as (
    select count(*) as n from {{ ref('quarantined_records') }} where table_name = 'applications'
)

select received.n as received, loaded.n as loaded,
       flagged_in_fact.n as flagged_in_fact, flagged_in_audit.n as flagged_in_audit
from received, loaded, flagged_in_fact, flagged_in_audit
where received.n <> loaded.n
   or flagged_in_fact.n <> flagged_in_audit.n
