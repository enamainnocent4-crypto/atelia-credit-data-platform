-- Chaque client doit avoir exactement UNE version courante.
-- Deux versions courantes = l'historisation est cassée.
select customer_id, count(*) as current_versions
from {{ ref('dim_customer') }}
where is_current
group by customer_id
having count(*) <> 1
