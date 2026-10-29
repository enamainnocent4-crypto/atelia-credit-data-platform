-- Les périodes de validité d'un même client ne doivent jamais se chevaucher :
-- sinon, un fait pourrait se rattacher à deux versions à la fois.
select a.customer_id, a.customer_sk, b.customer_sk as overlapping_sk
from {{ ref('dim_customer') }} as a
join {{ ref('dim_customer') }} as b
    on a.customer_id = b.customer_id
   and a.customer_sk <> b.customer_sk
   and a.valid_from < b.valid_to
   and b.valid_from < a.valid_to
