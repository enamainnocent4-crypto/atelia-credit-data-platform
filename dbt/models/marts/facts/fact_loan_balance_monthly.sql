-- Encours mensuel — photo périodique (periodic snapshot).
-- Grain : un prêt à une fin de mois.
-- C'est la table qui porte les indicateurs de risque (PAR30, défaut, provisions,
-- coût du risque) et le PNB, pour chaque prêt, chaque mois.
--
-- Un prêt apparaît chaque fin de mois, de son décaissement jusqu'au mois où il est
-- soldé (remboursé) ou passé en perte (plus de 180 jours de retard), inclus.

with months as (
    select
        date_day                                 as month_end,
        month_start
    from {{ ref('dim_date') }}
    where is_month_end
      and date_day between '{{ var("reporting_start_date") }}' and '{{ var("reporting_end_date") }}'
),

-- €STR moyen du mois ; si un mois n'a aucune cotation, on reprend la dernière connue
estr_monthly as (
    select
        m.month_end,
        coalesce(
            (select avg(r.estr_rate_pct) from {{ ref('stg_ecb__estr_rates') }} as r
             where r.rate_date between m.month_start and m.month_end),
            (select r.estr_rate_pct from {{ ref('stg_ecb__estr_rates') }} as r
             where r.rate_date <= m.month_end order by r.rate_date desc limit 1)
        ) as estr_rate_pct
    from months as m
),

loans as (
    select * from {{ ref('stg_core_banking__loans') }}
),

-- Flux financiers du mois (paiements fiables uniquement)
monthly_flows as (
    select
        p.loan_id,
        (date_trunc('month', p.payment_date) + interval '1 month - 1 day')::date as month_end,
        sum(p.interest_amount)  as interest_received,
        sum(p.principal_amount) as principal_received
    from {{ ref('fact_payment') }} as p
    group by 1, 2
),

enriched as (
    select
        pos.loan_id,
        pos.month_end,
        pos.month_start,
        l.customer_id,
        l.branch_code,
        l.product_code,
        l.disbursement_date,
        l.principal_amount,
        l.principal_amount - pos.principal_repaid                       as outstanding_before_write_off,
        case when pos.oldest_unpaid_due_date is null then 0
             else pos.month_end - pos.oldest_unpaid_due_date end         as days_past_due,
        coalesce(f.interest_received, 0)                                as interest_received,
        coalesce(f.principal_received, 0)                               as principal_received,
        case when l.disbursement_date between pos.month_start and pos.month_end
             then l.principal_amount else 0 end                         as disbursed_amount,
        case when l.disbursement_date between pos.month_start and pos.month_end
             then l.fee_amount else 0 end                               as fee_income,
        e.estr_rate_pct
    from {{ ref('int_loan_months__positions') }} as pos
    join loans as l on l.loan_id = pos.loan_id
    left join monthly_flows as f on f.loan_id = pos.loan_id and f.month_end = pos.month_end
    join estr_monthly as e on e.month_end = pos.month_end
),

-- Fin de vie du prêt : premier mois soldé, ou premier mois au-delà du seuil de perte
lifecycle as (
    select
        *,
        min(month_end) filter (where days_past_due > {{ var('write_off_days') }})
            over (partition by loan_id)                                 as write_off_month,
        min(month_end) filter (where outstanding_before_write_off <= 0.01 and days_past_due = 0)
            over (partition by loan_id)                                 as closed_month
    from enriched
),

active as (
    select
        *,
        month_end = write_off_month                                     as is_write_off_month
    from lifecycle
    where month_end <= least(coalesce(write_off_month, '9999-12-31'), coalesce(closed_month, '9999-12-31'))
),

measured as (
    select
        *,
        case when is_write_off_month then 0 else greatest(outstanding_before_write_off, 0) end as outstanding_principal,
        case when is_write_off_month then outstanding_before_write_off else 0 end              as write_off_amount,
        case
            when days_past_due = 0  then '1. À jour'
            when days_past_due <= 30 then '2. 1-30 jours'
            when days_past_due <= 90 then '3. 31-90 jours'
            when days_past_due <= {{ var('write_off_days') }} then '4. 91-180 jours'
            else '5. Plus de 180 jours'
        end                                                             as dpd_bucket
    from active
),

provisioned as (
    select
        *,
        outstanding_principal * case
            when days_past_due = 0  then {{ var('provision_rate_current') }}
            when days_past_due <= 30 then {{ var('provision_rate_1_30') }}
            when days_past_due <= 90 then {{ var('provision_rate_31_90') }}
            else {{ var('provision_rate_over_90') }}
        end                                                             as provision_amount,
        lag(outstanding_principal) over w                               as previous_outstanding,
        lag(dpd_bucket) over w                                          as previous_dpd_bucket
    from measured
    window w as (partition by loan_id order by month_end)
)

select
    p.loan_id || '-' || to_char(p.month_end, 'YYYYMM')                  as loan_month_id,
    p.loan_id,
    p.month_end,
    c.customer_sk,
    p.customer_id,
    p.branch_code,
    p.product_code,

    -- Statut de risque
    p.days_past_due,
    p.dpd_bucket,
    p.previous_dpd_bucket,
    case
        when p.is_write_off_month then 'WRITTEN_OFF'
        when p.outstanding_principal <= 0.01 then 'CLOSED'
        when p.days_past_due > 90 then 'DEFAULT'
        when p.days_past_due > 0 then 'LATE'
        else 'CURRENT'
    end                                                                 as loan_status,
    case when p.days_past_due > 30 and not p.is_write_off_month then 1 else 0 end as is_par30,
    case when p.days_past_due > 90 and not p.is_write_off_month then 1 else 0 end as is_default,

    -- Encours (montants en euros)
    round(p.outstanding_principal, 2)                                   as outstanding_principal,
    case when p.days_past_due > 30 then round(p.outstanding_principal, 2) else 0 end as par30_outstanding,
    case when p.days_past_due > 90 then round(p.outstanding_principal, 2) else 0 end as default_outstanding,

    -- Risque : provisions et coût du risque
    round(p.provision_amount, 2)                                        as provision_amount,
    round(p.write_off_amount, 2)                                        as write_off_amount,
    round(p.provision_amount - coalesce(lag(p.provision_amount) over w, 0) + p.write_off_amount, 2) as cost_of_risk,

    -- Activité et PNB
    p.disbursed_amount,
    p.principal_received,
    p.interest_received,
    p.fee_income,
    p.estr_rate_pct,
    -- Coût de refinancement : encours moyen du mois x (€STR + marge) x jours / 360 (convention monétaire)
    round(
        (coalesce(p.previous_outstanding, p.principal_amount) + p.outstanding_principal) / 2
        * (p.estr_rate_pct / 100 + {{ var('refinancing_spread') }})
        * (p.month_end - greatest(p.month_start, p.disbursement_date) + 1) / 360.0
    , 2)                                                                as refinancing_cost
from provisioned as p
left join {{ ref('dim_customer') }} as c
    on c.customer_id = p.customer_id
   and p.month_end >= c.valid_from
   and p.month_end < c.valid_to
window w as (partition by p.loan_id order by p.month_end)
