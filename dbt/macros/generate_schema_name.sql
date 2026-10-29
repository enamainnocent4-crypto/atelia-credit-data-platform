{#
  Par défaut, dbt préfixe les schémas personnalisés par celui du profil
  (« staging_audit »). On veut des noms simples et lisibles : staging, audit, marts.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
