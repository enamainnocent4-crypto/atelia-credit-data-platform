-- Calendrier : une ligne par jour, de 2024 à 2027.
-- Power BI s'appuie sur cette table pour toutes les analyses dans le temps.
with days as (
    select generate_series('2024-01-01'::date, '2027-12-31'::date, interval '1 day')::date as date_day
)

select
    date_day,
    to_char(date_day, 'YYYYMMDD')::integer                      as date_key,
    extract(year from date_day)::integer                         as year,
    extract(quarter from date_day)::integer                      as quarter,
    'T' || extract(quarter from date_day) || ' ' || extract(year from date_day) as quarter_label,
    extract(month from date_day)::integer                        as month,
    (array['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet',
           'août', 'septembre', 'octobre', 'novembre', 'décembre'])[extract(month from date_day)] as month_name,
    to_char(date_day, 'YYYY-MM')                                 as year_month,
    date_trunc('month', date_day)::date                          as month_start,
    (date_trunc('month', date_day) + interval '1 month - 1 day')::date as month_end,
    date_day = (date_trunc('month', date_day) + interval '1 month - 1 day')::date as is_month_end,
    extract(isodow from date_day)::integer                       as day_of_week,
    (array['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche'])[extract(isodow from date_day)] as day_name,
    extract(isodow from date_day) in (6, 7)                      as is_weekend
from days
