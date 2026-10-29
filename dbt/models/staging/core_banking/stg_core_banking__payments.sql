-- Paiements : une ligne par ligne reçue de l'API. Les doublons de la source sont
-- volontairement conservés ici : le test d'unicité les détecte et les enregistre.
select
    payment_id,
    loan_id,
    loan_id || '-' || lpad(installment_number, 3, '0')  as installment_id,
    installment_number::integer                          as installment_number,
    payment_date::date                                   as payment_date,
    amount::numeric(12, 2)                               as amount,
    payment_method,
    updated_at::timestamp                                as updated_at,
    _loaded_at                                           as loaded_at
from {{ source('core_banking', 'payments') }}
