-- Agences, plus une ligne « Agence inconnue » (UNKNOWN).
-- Principe Kimball : une demande dont l'agence est absente du référentiel n'est pas perdue,
-- elle est rattachée à ce membre inconnu et reste visible dans les totaux.
select
    branch_code,
    branch_name,
    city,
    region,
    opening_date,
    false as is_unknown_member
from {{ ref('stg_reference__branches') }}

union all

select 'UNKNOWN', 'Agence inconnue', 'Inconnue', 'Inconnue', null, true
