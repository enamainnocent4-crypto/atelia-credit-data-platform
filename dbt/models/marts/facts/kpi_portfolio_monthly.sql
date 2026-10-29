-- Tableau de bord mensuel du portefeuille, calculé dans la base.
-- Grain : un mois. Sert de référence pour vérifier les mesures DAX de Power BI :
-- les deux doivent donner exactement les mêmes chiffres.
with monthly as (
    select
        month_end,
        count(*) filter (where loan_status not in ('CLOSED', 'WRITTEN_OFF'))   as active_loans,
        sum(outstanding_principal)                                              as outstanding,
        sum(par30_outstanding)                                                  as par30_outstanding,
        sum(default_outstanding)                                                as default_outstanding,
        sum(provision_amount)                                                   as provisions,
        sum(write_off_amount)                                                   as write_offs,
        sum(cost_of_risk)                                                       as cost_of_risk,
        sum(disbursed_amount)                                                   as production,
        sum(interest_received)                                                  as interest_income,
        sum(fee_income)                                                         as fee_income,
        sum(refinancing_cost)                                                   as refinancing_cost,
        -- Recouvrement : prêts en retard le mois précédent...
        count(*) filter (where previous_dpd_bucket <> '1. À jour')                       as late_previous_month,
        -- ... revenus à jour ce mois-ci
        count(*) filter (where previous_dpd_bucket <> '1. À jour' and dpd_bucket = '1. À jour') as regularized,
        -- Bascule : de 1-30 jours vers 31-90 jours
        count(*) filter (where previous_dpd_bucket = '2. 1-30 jours')           as in_1_30_previous_month,
        count(*) filter (where previous_dpd_bucket = '2. 1-30 jours'
                           and dpd_bucket = '3. 31-90 jours')                   as rolled_to_31_90
    from {{ ref('fact_loan_balance_monthly') }}
    group by month_end
)

select
    month_end,
    active_loans,
    round(outstanding, 2)                                                       as outstanding,
    round(production, 2)                                                        as production,
    round(par30_outstanding / nullif(outstanding, 0), 4)                        as par30_rate,
    round(default_outstanding / nullif(outstanding, 0), 4)                      as default_rate,
    round(provisions, 2)                                                        as provisions,
    round(write_offs, 2)                                                        as write_offs,
    round(cost_of_risk, 2)                                                      as cost_of_risk,
    -- Coût du risque annualisé, rapporté à l'encours moyen du mois
    round(12 * cost_of_risk / nullif((outstanding + lag(outstanding) over (order by month_end)) / 2, 0), 4) as cost_of_risk_rate_annualized,
    round(interest_income, 2)                                                   as interest_income,
    round(fee_income, 2)                                                        as fee_income,
    round(refinancing_cost, 2)                                                  as refinancing_cost,
    round(interest_income + fee_income - refinancing_cost, 2)                   as net_banking_income,
    round(regularized::numeric / nullif(late_previous_month, 0), 4)             as regularization_rate,
    round(rolled_to_31_90::numeric / nullif(in_1_30_previous_month, 0), 4)     as roll_rate_1_30_to_31_90
from monthly
order by month_end
