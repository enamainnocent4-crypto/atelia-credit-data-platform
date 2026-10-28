"""Paramètres du « monde » Atelia Crédit.

Tout ce qui décrit la banque fictive est réuni ici : on ajuste le scénario
sans toucher à la logique de simulation (generate.py).
"""

from datetime import date
from pathlib import Path

# --- Reproductibilité -------------------------------------------------------
# Même graine = mêmes données à chaque exécution. Indispensable pour reproduire
# un bug ou comparer deux versions d'un modèle dbt.
SEED = 42

# --- Période simulée --------------------------------------------------------
START_DATE = date(2024, 11, 1)   # début de l'historique (24 mois)
AS_OF_DATE = date(2026, 10, 31)  # date d'extraction : rien n'existe après

# --- Volumes ----------------------------------------------------------------
N_APPLICATIONS = 8_000           # demandes de crédit sur la période
REPEAT_CUSTOMER_RATE = 0.375     # part des demandes faites par un client existant
                                 # -> environ 5 000 clients au total
MONTHLY_GROWTH = 0.02            # croissance de l'activité : +2 % par mois

# Saisonnalité : poids relatif de chaque mois (août et décembre plus calmes)
MONTH_SEASONALITY = {
    1: 1.00, 2: 1.00, 3: 1.10, 4: 1.05, 5: 1.00, 6: 1.05,
    7: 0.90, 8: 0.60, 9: 1.15, 10: 1.10, 11: 1.00, 12: 0.75,
}

# --- Profils de comportement des clients (vérité cachée) --------------------
# Ces profils n'apparaissent PAS dans l'export CRM : la banque ne les connaît
# pas, elle les découvre à travers les retards de paiement.
CUSTOMER_PROFILES = {
    "good_payer": 0.65,          # paie à l'heure, rares petits décalages
    "late_regularizing": 0.25,   # retards fréquents, mais finit par régulariser
    "defaulting": 0.10,          # cesse de payer à partir d'une certaine échéance
}

# Probabilité d'accord du dossier selon le profil (le scoring filtre une partie
# des clients risqués). Moyenne pondérée ~ 65 %.
APPROVAL_RATE_BY_PROFILE = {
    "good_payer": 0.72,
    "late_regularizing": 0.56,
    "defaulting": 0.42,
}

DECISION_DELAY_DAYS = (2, 15)        # délai d'instruction (min, max)
DISBURSEMENT_DELAY_DAYS = (1, 10)    # délai entre accord et versement des fonds

# --- Segments de clientèle ----------------------------------------------------
SEGMENT_SHARES = {"particulier": 0.70, "professionnel": 0.30}

# Produits demandés selon le segment (somme = 1 pour chaque segment)
PRODUCT_MIX_BY_SEGMENT = {
    "particulier": {"MICRO_PERSO": 0.35, "PRET_PERSO": 0.40, "CREDIT_AUTO": 0.25},
    "professionnel": {"MICRO_PRO": 0.70, "PRET_PERSO": 0.15, "CREDIT_AUTO": 0.15},
}

MONTHLY_INCOME_RANGE = {             # revenu mensuel net déclaré (EUR)
    "particulier": (1_300, 4_500),
    "professionnel": (1_000, 6_000),
}

# --- Catalogue produits ---------------------------------------------------------
# Taux nominaux annuels fictifs mais plausibles. Les crédits aux particuliers
# restent sous les seuils de l'usure du 4e trimestre 2026 publiés par la
# Banque de France (8,56 % au-delà de 6 000 EUR, 15,76 % de 3 000 à 6 000 EUR).
PRODUCTS = [
    {
        "product_code": "MICRO_PRO",
        "product_name": "Microcrédit professionnel",
        "customer_segment": "professionnel",
        "min_amount": 1_000, "max_amount": 12_000,
        "min_duration_months": 12, "max_duration_months": 48,
        "min_rate": 0.070, "max_rate": 0.085,
        "fee_rate": 0.015,
    },
    {
        "product_code": "MICRO_PERSO",
        "product_name": "Microcrédit personnel",
        "customer_segment": "particulier",
        "min_amount": 300, "max_amount": 5_000,
        "min_duration_months": 6, "max_duration_months": 36,
        "min_rate": 0.030, "max_rate": 0.050,
        "fee_rate": 0.000,
    },
    {
        "product_code": "PRET_PERSO",
        "product_name": "Prêt personnel",
        "customer_segment": "tous",
        "min_amount": 3_000, "max_amount": 30_000,
        "min_duration_months": 12, "max_duration_months": 72,
        "min_rate": 0.049, "max_rate": 0.074,
        "fee_rate": 0.010,
    },
    {
        "product_code": "CREDIT_AUTO",
        "product_name": "Crédit auto",
        "customer_segment": "tous",
        "min_amount": 5_000, "max_amount": 40_000,
        "min_duration_months": 24, "max_duration_months": 84,
        "min_rate": 0.045, "max_rate": 0.069,
        "fee_rate": 0.010,
    },
]

# --- Réseau d'agences -----------------------------------------------------------
# Deux agences ouvrent pendant la période : utile pour l'analyse de la montée
# en charge d'une nouvelle agence.
BRANCHES = [
    {"branch_code": "BR01", "branch_name": "Paris Nation", "city": "Paris", "region": "Île-de-France", "opening_date": "2018-03-01", "weight": 1.6},
    {"branch_code": "BR02", "branch_name": "Saint-Denis", "city": "Saint-Denis", "region": "Île-de-France", "opening_date": "2019-09-01", "weight": 1.3},
    {"branch_code": "BR03", "branch_name": "Créteil", "city": "Créteil", "region": "Île-de-France", "opening_date": "2021-01-15", "weight": 1.0},
    {"branch_code": "BR04", "branch_name": "Lyon Part-Dieu", "city": "Lyon", "region": "Auvergne-Rhône-Alpes", "opening_date": "2018-06-01", "weight": 1.3},
    {"branch_code": "BR05", "branch_name": "Grenoble", "city": "Grenoble", "region": "Auvergne-Rhône-Alpes", "opening_date": "2025-09-01", "weight": 0.8},
    {"branch_code": "BR06", "branch_name": "Lille Centre", "city": "Lille", "region": "Hauts-de-France", "opening_date": "2019-02-01", "weight": 1.1},
    {"branch_code": "BR07", "branch_name": "Roubaix", "city": "Roubaix", "region": "Hauts-de-France", "opening_date": "2022-05-02", "weight": 0.8},
    {"branch_code": "BR08", "branch_name": "Marseille Canebière", "city": "Marseille", "region": "Provence-Alpes-Côte d'Azur", "opening_date": "2018-10-01", "weight": 1.3},
    {"branch_code": "BR09", "branch_name": "Nice", "city": "Nice", "region": "Provence-Alpes-Côte d'Azur", "opening_date": "2023-03-01", "weight": 0.8},
    {"branch_code": "BR10", "branch_name": "Toulouse Capitole", "city": "Toulouse", "region": "Occitanie", "opening_date": "2020-04-01", "weight": 1.1},
    {"branch_code": "BR11", "branch_name": "Montpellier", "city": "Montpellier", "region": "Occitanie", "opening_date": "2026-01-05", "weight": 0.8},
    {"branch_code": "BR12", "branch_name": "Bordeaux", "city": "Bordeaux", "region": "Nouvelle-Aquitaine", "opening_date": "2019-11-04", "weight": 1.1},
]

# --- Anomalies volontaires ------------------------------------------------------
# Injectées APRÈS la simulation, pour que les tests de qualité (dbt) aient de
# vrais problèmes à détecter. Chaque anomalie est tracée dans
# _ground_truth/injected_anomalies.csv.
ANOMALIES = {
    "duplicate_payment": 120,          # paiement présent deux fois
    "negative_requested_amount": 20,   # montant demandé négatif
    "unknown_branch": 15,              # code agence absent du référentiel
    "payment_before_disbursement": 15, # paiement daté avant le versement des fonds
}

# --- Sorties ----------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "generated"
