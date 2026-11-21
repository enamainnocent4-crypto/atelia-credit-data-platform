-- Réconciliation : la production décaissée doit être IDENTIQUE dans les deux tables de faits.
-- - fact_credit_application : vue « demandes » (page Réseau d'agences) ;
-- - fact_loan_balance_monthly : vue « portefeuille » (page Direction générale).
-- Un écart signifierait qu'un prêt est compté d'un côté et pas de l'autre
-- (c'est ce test qui aurait détecté les 16 prêts de 218 750 € exclus par erreur).
with from_applications as (
    select coalesce(sum(disbursed_amount), 0) as amount
    from {{ ref('fact_credit_application') }}
    -- même période que l'encours mensuel : du 1er jour du premier mois à la date d'arrêté
    where disbursement_date between date_trunc('month', '{{ var("reporting_start_date") }}'::date)
                                and '{{ var("reporting_end_date") }}'::date
),
from_portfolio as (
    select coalesce(sum(disbursed_amount), 0) as amount
    from {{ ref('fact_loan_balance_monthly') }}
)

select from_applications.amount as production_applications,
       from_portfolio.amount    as production_portfolio
from from_applications, from_portfolio
where abs(from_applications.amount - from_portfolio.amount) > 0.01
