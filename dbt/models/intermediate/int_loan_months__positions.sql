{{ config(materialized='table') }}

-- Position de chaque prêt à chaque fin de mois : capital remboursé et plus ancienne
-- échéance impayée. Grain : un prêt à une fin de mois.
-- Matérialisé en table : c'est le calcul le plus lourd du projet (prêts x mois x échéances),
-- et PostgreSQL l'optimise bien mieux sur une table que sur une chaîne de vues.
with months as (
    select date_day as month_end, month_start
    from {{ ref('dim_date') }}
    where is_month_end
      and date_day between '{{ var("reporting_start_date") }}' and '{{ var("reporting_end_date") }}'
),

loan_months as (
    select l.loan_id, m.month_end, m.month_start
    from {{ ref('stg_core_banking__loans') }} as l
    join months as m
        on m.month_end >= l.disbursement_date
)

select
    lm.loan_id,
    lm.month_end,
    lm.month_start,
    coalesce(sum(i.principal_due) filter (where i.settled_date <= lm.month_end), 0) as principal_repaid,
    min(i.due_date) filter (
        where i.due_date <= lm.month_end
          and (i.settled_date is null or i.settled_date > lm.month_end)
    ) as oldest_unpaid_due_date
from loan_months as lm
join {{ ref('int_installments__settlement') }} as i
    on i.loan_id = lm.loan_id
group by lm.loan_id, lm.month_end, lm.month_start
