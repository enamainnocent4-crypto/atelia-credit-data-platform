-- Demandes de crédit fiables. Un montant demandé négatif ou nul est impossible :
-- la demande est mise en quarantaine (audit.quarantined_records).
-- Les codes agence inconnus sont CONSERVÉS : ils seront rattachés à « Agence inconnue ».
select *
from {{ ref('stg_core_banking__applications') }}
where requested_amount > 0
