-- Réconciliation : chaque paiement reçu doit se retrouver SOIT dans fact_payment,
-- SOIT dans la quarantaine. Aucun ne doit se perdre en route, aucun ne doit être compté deux fois.
with received as (
    select count(distinct payment_id) as n from {{ ref('stg_core_banking__payments') }}
),
loaded as (
    select count(*) as n from {{ ref('fact_payment') }}
),
quarantined as (
    select count(*) as n
    from {{ ref('quarantined_records') }}
    where table_name = 'payments'
      and reason not like 'Doublon%'
)

select received.n as received, loaded.n as loaded, quarantined.n as quarantined
from received, loaded, quarantined
where received.n <> loaded.n + quarantined.n
