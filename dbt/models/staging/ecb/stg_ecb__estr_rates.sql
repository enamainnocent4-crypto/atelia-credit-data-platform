-- €STR quotidien : une ligne par jour ouvré. Taux publié en pourcentage (2.44),
-- converti ici en décimal (0.0244) comme les taux des prêts, pour pouvoir les comparer.
select
    rate_date::date                         as rate_date,
    estr_rate::numeric(8, 4)                as estr_rate_pct,
    estr_rate::numeric(8, 4) / 100          as estr_rate
from {{ source('ecb', 'ecb_estr_rates') }}
