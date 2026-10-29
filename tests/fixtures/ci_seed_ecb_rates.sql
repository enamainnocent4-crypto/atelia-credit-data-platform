-- Taux €STR de test pour l'intégration continue.
-- La CI n'appelle pas l'API de la BCE : une source externe peut être lente ou
-- indisponible, et un test ne doit échouer que si NOTRE code est cassé.
-- On insère donc un taux fixe de 2,500 % pour chaque jour ouvré de la période.
create table if not exists raw.ecb_estr_rates (
    rate_date  text,
    estr_rate  text,
    _loaded_at timestamptz not null,
    _source    text        not null,
    _batch_id  uuid        not null
);

insert into raw.ecb_estr_rates
select
    d::date::text,
    '2.500',
    now(),
    'ci-fixture',
    gen_random_uuid()
from generate_series('2024-11-01'::date, '2026-10-30'::date, interval '1 day') as d
where extract(isodow from d) < 6;
