-- Demandes de crédit validées. Grain : une ligne par demande reçue (aucune n'est exclue).
--
-- Un montant demandé négatif ou nul est une ERREUR DE SAISIE : le montant est mis à
-- vide (NULL) et la demande est SIGNALÉE (is_requested_amount_valid = 0), mais elle est
-- CONSERVÉE. Certaines de ces demandes ont été acceptées et décaissées : les exclure
-- ferait disparaître de vrais prêts de la production. Le signalement est tracé dans
-- audit.quarantined_records.
-- Les codes agence inconnus sont aussi conservés : ils seront rattachés à « Agence inconnue ».
select
    application_id,
    customer_id,
    branch_code,
    product_code,
    submitted_date,
    case when requested_amount > 0 then requested_amount end   as requested_amount,
    case when requested_amount > 0 then 1 else 0 end            as is_requested_amount_valid,
    requested_duration_months,
    proposed_annual_rate,
    application_status,
    decision_date,
    decision_delay_days,
    updated_at,
    loaded_at
from {{ ref('stg_core_banking__applications') }}
