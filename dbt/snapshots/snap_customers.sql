{#
  Historisation des clients (SCD de type 2).
  À chaque exécution, dbt compare les colonnes suivies avec la version précédente :
  si l'une d'elles a changé, l'ancienne ligne est fermée (dbt_valid_to renseignée)
  et une nouvelle version est ajoutée. Rien n'est jamais écrasé.
#}
{% snapshot snap_customers %}

{{
    config(
        schema='snapshots',
        unique_key='customer_id',
        strategy='check',
        check_cols=['city', 'postal_code', 'monthly_income', 'customer_segment', 'email'],
    )
}}

select * from {{ ref('stg_crm__customers') }}

{% endsnapshot %}
