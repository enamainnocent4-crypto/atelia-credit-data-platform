-- Demandes de crédit : une ligne par ligne reçue de l'API (grain identique à raw).
-- Aucune ligne n'est supprimée : les anomalies sont détectées par les tests.
select
    application_id,
    customer_id,
    branch_code,
    product_code,
    submitted_date::date                        as submitted_date,
    requested_amount::numeric(12, 2)            as requested_amount,
    requested_duration_months::integer          as requested_duration_months,
    proposed_annual_rate::numeric(6, 4)         as proposed_annual_rate,
    status                                      as application_status,
    decision_date::date                         as decision_date,
    decision_date::date - submitted_date::date  as decision_delay_days,
    updated_at::timestamp                       as updated_at,
    _loaded_at                                  as loaded_at
from {{ source('core_banking', 'applications') }}
