-- Réconciliation de l'encours à la date d'arrêté, pour chaque prêt encore en portefeuille :
-- encours = capital prêté - capital des échéances réglées.
-- Vérifie que la photo mensuelle ne dérive pas de l'échéancier source.
with last_month as (
    select loan_id, outstanding_principal
    from {{ ref('fact_loan_balance_monthly') }}
    where month_end = '{{ var("reporting_end_date") }}'
      and loan_status not in ('WRITTEN_OFF')
),

expected as (
    select
        l.loan_id,
        l.principal_amount - coalesce(sum(i.principal_due) filter (
            where i.settled_date <= '{{ var("reporting_end_date") }}'), 0) as expected_outstanding
    from {{ ref('stg_core_banking__loans') }} as l
    join {{ ref('int_installments__settlement') }} as i using (loan_id)
    group by l.loan_id, l.principal_amount
)

select m.loan_id, m.outstanding_principal, e.expected_outstanding
from last_month as m
join expected as e using (loan_id)
where abs(m.outstanding_principal - e.expected_outstanding) > 0.01
