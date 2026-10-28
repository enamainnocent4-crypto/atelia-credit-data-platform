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
cp .env.example .env        # puis changer le mot de passe dans .env
docker compose up -d        # démarre PostgreSQL
docker compose ps           # le service doit être "healthy"
```

La base est exposée sur le port **55432** (et non 5432) pour ne pas entrer en conflit avec un PostgreSQL déjà installé sur le poste. Le port se change dans `.env` (`POSTGRES_PORT`).

Connexion depuis un client SQL (DBeaver…) : hôte `localhost`, port `55432`, base `atelia_dw`, utilisateur `atelia`, mot de passe du `.env`.

## Données synthétiques

```bash
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1          # Windows PowerShell
pip install -r requirements.txt
python -m data_generator.generate
```

Le générateur simule 24 mois d'activité (novembre 2024 à octobre 2026) dans l'ordre chronologique : client → demande → décision → décaissement → échéancier → paiements. Une graine fixe rend les données reproductibles à l'identique.

| Dossier de sortie (`data/generated/`) | Fichiers | Rôle |
| --- | --- | --- |
| `reference/` | `branches.csv`, `products.csv` | Référentiels (12 agences, 4 produits) |
| `crm/` | `customers.csv` | Export CRM (~5 200 clients fictifs) |
| `core_banking/` | `applications.csv`, `loans.csv`, `installments.csv`, `payments.csv` | Système bancaire central, servi par l'API |
| `_ground_truth/` | `customer_profiles.csv`, `injected_anomalies.csv` | Vérité cachée, pour valider les tests de qualité |

Profils de clients : 65 % de bons payeurs, 25 % de retards qui se régularisent, 10 % de ruptures de paiement. Environ 170 anomalies sont injectées volontairement (doublons, montants négatifs, agence inconnue, paiement antérieur au décaissement) : les tests dbt doivent toutes les détecter.

## Stack

Python 3.12 (pandas, NumPy, Faker) · PostgreSQL 16 · dbt · FastAPI · Power BI · Docker Compose · pytest · GitHub Actions

## Avancement

- [x] Étape 0 — Cadrage métier
- [x] Étape 1 — Environnement
- [ ] Étape 2 — Données synthétiques
- [ ] Étape 3 — Sources
- [ ] Étape 4 — Ingestion
- [ ] Étape 5 — dbt staging
- [ ] Étape 6 — Modèle en étoile
- [ ] Étape 7 — Qualité et intégration continue
- [ ] Étape 8 — Power BI
- [ ] Étape 9 — Documentation
