{#
  Test générique réutilisable : échoue pour chaque ligne où la colonne est <= 0.
  Usage dans un fichier .yml :  data_tests: [positive_value]
#}
{% test positive_value(model, column_name) %}
select *
from {{ model }}
where {{ column_name }} <= 0
{% endtest %}
