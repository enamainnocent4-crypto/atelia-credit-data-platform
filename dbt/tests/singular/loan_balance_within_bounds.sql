-- L'encours d'un prêt est toujours compris entre 0 et le montant prêté.
-- Un encours négatif ou supérieur au capital trahirait une erreur de calcul.
select loan_month_id, outstanding_principal
from {{ ref('fact_loan_balance_monthly') }} as f
join {{ ref('stg_core_banking__loans') }} as l using (loan_id)
where f.outstanding_principal < 0
   or f.outstanding_principal > l.principal_amount
