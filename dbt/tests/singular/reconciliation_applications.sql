-- Réconciliation : chaque demande reçue est SOIT dans fact_credit_application, SOIT en quarantaine.
with received as (
    select count(*) as n from {{ ref('stg_core_banking__applications') }}
),
loaded as (
    select count(*) as n from {{ ref('fact_credit_application') }}
),
quarantined as (
    select count(*) as n from {{ ref('quarantined_records') }} where table_name = 'applications'
)

select received.n as received, loaded.n as loaded, quarantined.n as quarantined
from received, loaded, quarantined
where received.n <> loaded.n + quarantined.n
