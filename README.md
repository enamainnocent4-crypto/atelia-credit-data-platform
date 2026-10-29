# Atelia Crédit — Enterprise Data Platform & BI

Mini-plateforme décisionnelle de bout en bout pour un établissement fictif de microcrédit et de crédit à la consommation en France : des systèmes sources jusqu'aux indicateurs de pilotage dans Power BI.

## Objectif

Démontrer la conception d'un système d'information décisionnel complet : ingestion de sources hétérogènes, modélisation en étoile, transformations testées, restitution métier et industrialisation.

## Cas métier

Atelia Crédit pilote son activité avec quatre décideurs :

| Décideur | Question | Indicateurs |
| --- | --- | --- |
| Direction générale | Gagne-t-on de l'argent, et grâce à quoi ? | PNB, production |
| Direction des risques | Nos clients remboursent-ils ? | PAR30, taux de défaut, coût du risque |
| Direction du réseau | Nos agences produisent-elles bien et vite ? | Taux d'acceptation, délai d'instruction |
| Service recouvrement | Qui appeler en priorité, et nos actions marchent-elles ? | Taux de régularisation, taux de bascule |

Toutes les données sont synthétiques : aucune donnée personnelle réelle n'est utilisée (RGPD).

## Architecture

```
Sources (CSV, API interne FastAPI, API BCE)
        │
        ▼
Ingestion Python ──► PostgreSQL : raw ──► staging ──► marts (modèle en étoile)
                                     dbt (modèles, tests, snapshots)
        │
        ▼
Power BI (tableau de bord de pilotage)
```

| Dossier | Rôle |
| --- | --- |
| `data_generator/` | Génération des données synthétiques |
| `api/` | API interne simulant le système bancaire central |
| `ingestion/` | Chargement des sources dans la couche `raw` |
| `dbt/` | Transformations `staging` et `marts`, tests de qualité |
| `tests/` | Tests automatisés (pytest) |
| `powerbi/` | Rapport Power BI |
| `docs/` | Documentation d'architecture |
| `sql/init/` | Initialisation de la base (schémas) |

## Démarrage rapide

Prérequis : Docker Desktop lancé, Python 3.12.

```bash
cp .env.example .env                  # puis changer les secrets dans .env
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1          # Windows PowerShell
pip install -r requirements.txt
python -m data_generator.generate     # 1. génère les données sources
docker compose up -d --build          # 2. démarre PostgreSQL et l'API
docker compose ps                     # les deux services doivent être "healthy"
python -m ingestion.run               # 3. charge les sources dans la couche raw
python run_dbt.py build               # 4. construit staging, intermediate, marts et lance les tests
```

| Service | Adresse | Accès |
| --- | --- | --- |
| PostgreSQL | `localhost:55432`, base `atelia_dw` | utilisateur `atelia`, mot de passe du `.env` |
| API core banking | `http://localhost:8100/docs` | en-tête `X-API-Key` (clé du `.env`) |

Les ports 55432 et 8100 évitent les conflits avec un PostgreSQL ou une autre API déjà présents sur le poste. Ils se changent dans `.env` (`POSTGRES_PORT`, `API_PORT`).

## Données synthétiques

Le générateur simule 24 mois d'activité (novembre 2024 à octobre 2026) dans l'ordre chronologique : client → demande → décision → décaissement → échéancier → paiements. Une graine fixe rend les données reproductibles à l'identique.

| Dossier de sortie (`data/generated/`) | Fichiers | Rôle |
| --- | --- | --- |
| `reference/` | `branches.csv`, `products.csv` | Référentiels (12 agences, 4 produits) |
| `crm/` | `customers.csv` | Export CRM (~5 200 clients fictifs) |
| `core_banking/` | `applications.csv`, `loans.csv`, `installments.csv`, `payments.csv` | Système bancaire central, servi par l'API |
| `_ground_truth/` | `customer_profiles.csv`, `injected_anomalies.csv` | Vérité cachée, pour valider les tests de qualité |

Profils de clients : 65 % de bons payeurs, 25 % de retards qui se régularisent, 10 % de ruptures de paiement. Environ 170 anomalies sont injectées volontairement (doublons, montants négatifs, agence inconnue, paiement antérieur au décaissement) : les tests dbt doivent toutes les détecter.

## Sources

| Source | Type | Contenu |
| --- | --- | --- |
| `data/generated/reference/` | Fichiers CSV | Référentiels agences et produits |
| `data/generated/crm/` | Fichier CSV | Export CRM des clients |
| API core banking (`api/`) | API REST interne (FastAPI) | Demandes, prêts, échéances, paiements |
| [ECB Data Portal](https://data.ecb.europa.eu/) (`ingestion/ecb_client.py`) | API REST publique | Taux €STR quotidien, pour le coût de refinancement |

L'API core banking propose :

- `GET /applications`, `/loans`, `/installments`, `/payments` : listes paginées (`limit`, `offset`), triées par date de mise à jour ;
- le paramètre `updated_since` pour le chargement incrémental ;
- `GET /health` pour la supervision (sans authentification) ;
- une documentation interactive générée automatiquement sur `/docs`.

## Ingestion

```bash
python -m ingestion.run                  # chargement normal (incrémental)
python -m ingestion.run --full-refresh   # tout recharger depuis zéro
python -m ingestion.run --only api       # une seule famille : csv, api ou ecb
```

| Source | Table `raw` | Mode |
| --- | --- | --- |
| `reference/branches.csv`, `reference/products.csv`, `crm/customers.csv` | `branches`, `products`, `customers` | Rechargement complet |
| API core banking | `applications`, `loans`, `installments`, `payments` | Incrémental (`updated_since`) |
| API BCE | `ecb_estr_rates` | Incrémental (depuis la dernière date chargée) |

Principes :

- **Fidélité** : `raw` stocke les données telles que reçues (colonnes texte), anomalies comprises, avec trois colonnes techniques (`_loaded_at`, `_source`, `_batch_id`). Le typage et le nettoyage se font dans dbt.
- **Idempotence** : chaque source est chargée dans une transaction, avec son marque-page. Une relance ne crée aucun doublon ; un échec n'écrit rien.
- **Traçabilité** : chaque exécution est journalisée dans `raw._ingestion_log` et `logs/ingestion.log` ; les marque-pages sont dans `raw._ingestion_state`.

## Transformations (dbt)

```bash
python run_dbt.py debug              # vérifier la connexion
python run_dbt.py build              # construire les modèles et lancer les tests
python run_dbt.py source freshness   # vérifier la fraîcheur des sources
```

`run_dbt.py` charge les identifiants du `.env` puis lance dbt : aucun secret n'est écrit dans `dbt/profiles.yml`.

**Staging** (`dbt/models/staging/`, schéma `staging`, en vues) : un modèle par table `raw`, nommé `stg_<source>__<table>`. On y type les colonnes, on les renomme, sans supprimer aucune ligne : le grain reste celui de la source.

**Tests de qualité** : 39 tests (unicité, non-nullité, intégrité référentielle, valeurs acceptées, montants positifs, cohérence des dates). Les quatre tests qui visent les anomalies connues de la source sont en mode avertissement et enregistrent les lignes fautives dans le schéma `audit` :

| Test | Anomalie détectée | Lignes |
| --- | --- | --- |
| `payments_payment_id_is_unique` | Paiement en double | 120 |
| `applications_requested_amount_is_positive` | Montant demandé négatif | 20 |
| `applications_branch_code_exists_in_referential` | Agence inconnue | 15 |
| `payments_not_before_disbursement` | Paiement antérieur au décaissement | 15 |

Total : **170 anomalies détectées pour 170 injectées** par le générateur (`_ground_truth/injected_anomalies.csv`).

## Modèle en étoile (marts)

| Table | Type | Grain |
| --- | --- | --- |
| `dim_date` | Dimension | Un jour (2024 à 2027) |
| `dim_branch` | Dimension | Une agence, plus le membre « Agence inconnue » |
| `dim_product` | Dimension | Un produit de crédit |
| `dim_customer` | Dimension historisée (SCD 2) | Une version de client |
| `fact_credit_application` | Faits, photo cumulative | Une demande de crédit (dépôt → décision → versement) |
| `fact_payment` | Faits, transactionnelle | Un paiement reçu |
| `fact_loan_balance_monthly` | Faits, photo périodique | Un prêt à une fin de mois |
| `kpi_portfolio_monthly` | Agrégat de contrôle | Un mois (référence pour valider les mesures Power BI) |

**Indicateurs de risque et de rentabilité** (`fact_loan_balance_monthly`) : encours, jours de retard et tranche de retard, PAR30, défaut (plus de 90 jours), provisions, passages en perte (plus de 180 jours), coût du risque, intérêts, frais de dossier, coût de refinancement et PNB.

Hypothèses simplifiées, paramétrées dans `dbt/dbt_project.yml` (`vars`) :

| Hypothèse | Valeur |
| --- | --- |
| Coût de refinancement | €STR moyen du mois + 1 point, sur l'encours moyen, base exact/360 |
| Provisions par tranche de retard (logique inspirée d'IFRS 9) | 1 % à jour, 5 % de 1 à 30 jours, 25 % de 31 à 90 jours, 100 % au-delà |
| Passage en perte | Plus de 180 jours de retard |
| Coût du risque | Variation des provisions + passages en perte |

**Traitement des anomalies** (couche `intermediate`) : les paiements en double sont dédoublonnés ; les montants négatifs et les paiements antérieurs au décaissement sont mis en quarantaine dans `audit.quarantined_records`, avec leur raison ; les agences inconnues sont rattachées au membre « Agence inconnue », pour qu'aucun fait ne soit perdu. Deux tests de réconciliation vérifient que chaque ligne reçue se retrouve soit dans les faits, soit en quarantaine.

**Historisation des clients** : un snapshot dbt (`snapshots/snap_customers.sql`) conserve chaque version d'un client quand sa ville, son revenu, son segment ou son e-mail change. Pour la démontrer :

```bash
python -m data_generator.crm_update      # 3 % des clients déménagent, 5 % changent de revenu
python -m ingestion.run --only csv       # recharge l'export CRM
python run_dbt.py build                  # le snapshot ajoute les nouvelles versions
```

## Stack

Python 3.12 (pandas, NumPy, Faker, psycopg) · PostgreSQL 16 · dbt 1.11 · FastAPI · Power BI · Docker Compose · pytest · GitHub Actions

## Avancement

- [x] Étape 0 — Cadrage métier
- [x] Étape 1 — Environnement
- [x] Étape 2 — Données synthétiques
- [x] Étape 3 — Sources
- [x] Étape 4 — Ingestion
- [x] Étape 5 — dbt staging
- [x] Étape 6 — Modèle en étoile
- [ ] Étape 7 — Qualité et intégration continue
- [ ] Étape 8 — Power BI
- [ ] Étape 9 — Documentation
