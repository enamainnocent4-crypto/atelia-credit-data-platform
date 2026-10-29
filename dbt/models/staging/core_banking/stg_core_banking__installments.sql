-- Échéances : une ligne par mensualité due. La clé naturelle est (loan_id, installment_number) ;
-- on la combine en une seule colonne, plus simple à tester et à joindre.
select
    loan_id || '-' || lpad(installment_number, 3, '0')  as installment_id,
    loan_id,
    installment_number::integer                          as installment_number,
    due_date::date                                       as due_date,
    principal_due::numeric(12, 2)                        as principal_due,
    interest_due::numeric(12, 2)                         as interest_due,
    total_due::numeric(12, 2)                            as total_due,
    updated_at::timestamp                                as updated_at,
    _loaded_at                                           as loaded_at
from {{ source('core_banking', 'installments') }}
