-- Demandes de crédit — photo cumulative (accumulating snapshot).
-- Grain : une ligne par demande. La ligne suit le parcours de la demande
-- (dépôt -> décision -> versement des fonds) avec une colonne de date par étape.
select
    a.application_id,
    c.customer_sk,
    a.customer_id,
    coalesce(b.branch_code, 'UNKNOWN')                  as branch_code,
    a.product_code,
    l.loan_id,

    -- Dates des étapes
    a.submitted_date,
    a.decision_date,
    l.disbursement_date,

    -- Statut et indicateurs 0/1 (faciles à additionner dans Power BI)
    a.application_status,
    case when a.application_status <> 'PENDING' then 1 else 0 end   as is_decided,
    case when a.application_status = 'APPROVED' then 1 else 0 end   as is_approved,
    case when l.loan_id is not null then 1 else 0 end               as is_disbursed,

    -- Mesures
    a.requested_amount,
    a.requested_duration_months,
    l.principal_amount                                   as disbursed_amount,
    l.fee_amount,
    a.decision_delay_days,
    l.disbursement_date - a.decision_date                as days_decision_to_disbursement
from {{ ref('int_applications__validated') }} as a
left join {{ ref('stg_core_banking__loans') }} as l
    on l.application_id = a.application_id
left join {{ ref('dim_branch') }} as b
    on b.branch_code = a.branch_code
-- La version du client valide au moment de la demande
left join {{ ref('dim_customer') }} as c
    on c.customer_id = a.customer_id
   and a.submitted_date >= c.valid_from
   and a.submitted_date < c.valid_to
