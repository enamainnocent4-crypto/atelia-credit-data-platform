-- Clients historisés (SCD de type 2) : une ligne par VERSION de client.
-- customer_sk identifie une version ; customer_id identifie le client.
-- La première version est déclarée valide depuis toujours (1900-01-01) : l'historique
-- des faits antérieurs à la première capture se rattache ainsi à une version.
with versions as (
    select
        *,
        row_number() over (partition by customer_id order by dbt_valid_from) as version_number
    from {{ ref('snap_customers') }}
)

select
    dbt_scd_id                                          as customer_sk,
    customer_id,
    version_number,
    first_name,
    last_name,
    birth_date,
    email,
    city,
    postal_code,
    customer_segment,
    monthly_income,
    case
        when monthly_income < 1500 then '1. moins de 1 500 €'
        when monthly_income < 2500 then '2. 1 500 à 2 499 €'
        when monthly_income < 3500 then '3. 2 500 à 3 499 €'
        else '4. 3 500 € et plus'
    end                                                 as income_band,
    home_branch_code,
    created_at,
    case when version_number = 1 then '1900-01-01'::timestamp else dbt_valid_from end as valid_from,
    coalesce(dbt_valid_to, '9999-12-31'::timestamp)     as valid_to,
    dbt_valid_to is null                                as is_current
from versions
