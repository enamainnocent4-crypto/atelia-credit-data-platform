"""Générateur de données synthétiques d'Atelia Crédit.

Simule la vie de la banque dans l'ordre chronologique :
    client -> demande -> décision -> décaissement -> échéancier -> paiements

puis injecte des anomalies volontaires et écrit les fichiers sources :
    data/generated/reference/      référentiels (CSV)      : agences, produits
    data/generated/crm/            export CRM (CSV)        : clients
    data/generated/core_banking/   système bancaire central : demandes, prêts,
                                   échéances, paiements (servis par l'API, étape 3)
    data/generated/_ground_truth/  vérité cachée : profils clients, anomalies

Lancement, depuis la racine du projet :
    python -m data_generator.generate
"""

from __future__ import annotations

import unicodedata
from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd
from faker import Faker

from data_generator import config as cfg

# Indicatif postal du département de chaque ville d'agence
POSTCODE_PREFIX = {
    "Paris": "75", "Saint-Denis": "93", "Créteil": "94", "Lyon": "69",
    "Grenoble": "38", "Lille": "59", "Roubaix": "59", "Marseille": "13",
    "Nice": "06", "Toulouse": "31", "Montpellier": "34", "Bordeaux": "33",
}

PAYMENT_METHODS = ["SEPA_DIRECT_DEBIT", "BANK_TRANSFER", "CARD"]
PAYMENT_METHOD_WEIGHTS = [0.85, 0.10, 0.05]


# ---------------------------------------------------------------------------
# Petits outils
# ---------------------------------------------------------------------------

def add_months(d: date, months: int, day: int) -> date:
    """Ajoute `months` mois à `d` et place le résultat au jour `day` (<= 28)."""
    month_index = d.month - 1 + months
    return date(d.year + month_index // 12, month_index % 12 + 1, day)


def random_timestamp(rng: np.random.Generator, d: date) -> datetime:
    """Horodatage aléatoire pendant les heures ouvrées du jour `d`."""
    seconds = int(rng.integers(8 * 3600, 19 * 3600))
    return datetime.combine(d, time()) + timedelta(seconds=seconds)


def ascii_slug(text: str) -> str:
    """'Hélène Le Gall' -> 'helene.le.gall' (pour fabriquer un e-mail)."""
    no_accents = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return ".".join(no_accents.lower().replace("'", "").split())


def pick(rng: np.random.Generator, shares: dict[str, float]) -> str:
    """Tire une clé du dictionnaire selon les probabilités associées."""
    keys = list(shares)
    return str(rng.choice(keys, p=list(shares.values())))


def annuity_payment(principal: float, annual_rate: float, n_months: int) -> float:
    """Mensualité constante : C x t / (1 - (1 + t)^-n), t = taux mensuel."""
    t = annual_rate / 12
    return principal * t / (1 - (1 + t) ** -n_months)


# ---------------------------------------------------------------------------
# 1. Référentiels
# ---------------------------------------------------------------------------

def build_branches() -> pd.DataFrame:
    return pd.DataFrame(cfg.BRANCHES).drop(columns="weight")


def build_products() -> pd.DataFrame:
    return pd.DataFrame(cfg.PRODUCTS)


# ---------------------------------------------------------------------------
# 2. Dates des demandes : croissance + saisonnalité
# ---------------------------------------------------------------------------

def sample_application_dates(rng: np.random.Generator) -> list[date]:
    months, weights = [], []
    current, i = cfg.START_DATE.replace(day=1), 0
    while current <= cfg.AS_OF_DATE:
        months.append(current)
        weights.append(cfg.MONTH_SEASONALITY[current.month] * (1 + cfg.MONTHLY_GROWTH) ** i)
        current, i = add_months(current, 1, 1), i + 1

    weights = np.array(weights) / sum(weights)
    counts = rng.multinomial(cfg.N_APPLICATIONS, weights)

    dates = []
    for month_start, n in zip(months, counts, strict=True):
        month_end = min(add_months(month_start, 1, 1) - timedelta(days=1), cfg.AS_OF_DATE)
        span = (month_end - month_start).days + 1
        dates += [month_start + timedelta(days=int(x)) for x in rng.integers(0, span, n)]
    return sorted(dates)


# ---------------------------------------------------------------------------
# 3. Clients et demandes de crédit
# ---------------------------------------------------------------------------

def new_customer(rng, fake, customer_id, branch, submitted) -> dict:
    segment = pick(rng, cfg.SEGMENT_SHARES)
    first, last = fake.first_name(), fake.last_name()
    low, high = cfg.MONTHLY_INCOME_RANGE[segment]
    opening = date.fromisoformat(branch["opening_date"])
    created = max(submitted - timedelta(days=int(rng.integers(0, 21))), opening)
    return {
        "customer_id": customer_id,
        "first_name": first,
        "last_name": last,
        "birth_date": submitted - timedelta(days=int(rng.integers(20 * 365, 70 * 365))),
        "email": f"{ascii_slug(first + ' ' + last)}{int(rng.integers(1, 99))}@example.com",
        "city": branch["city"],
        "postal_code": f"{POSTCODE_PREFIX[branch['city']]}0{int(rng.integers(0, 100)):02d}",
        "segment": segment,
        "monthly_income": int(round(rng.uniform(low, high), -1)),
        "home_branch_code": branch["branch_code"],
        "created_at": random_timestamp(rng, created),
        # vérité cachée : retirée de l'export CRM avant écriture
        "_profile": pick(rng, cfg.CUSTOMER_PROFILES),
    }


def draw_loan_terms(rng, product: dict) -> tuple[float, int, float]:
    """Montant, durée et taux tirés dans les bornes du produit."""
    lo, hi = product["min_amount"], product["max_amount"]
    step = 50 if hi <= 5_000 else 100
    amount = round(rng.triangular(lo, lo + (hi - lo) * 0.25, hi) / step) * step
    durations = [m for m in range(6, 121, 6)
                 if product["min_duration_months"] <= m <= product["max_duration_months"]]
    duration = int(rng.choice(durations))
    rate = round(rng.uniform(product["min_rate"], product["max_rate"]) * 2000) / 2000  # pas de 0,05 %
    return float(max(lo, min(hi, amount))), duration, rate


def build_customers_and_applications(rng, fake):
    branches = cfg.BRANCHES
    products = {p["product_code"]: p for p in cfg.PRODUCTS}
    customers: list[dict] = []
    customers_by_branch: dict[str, list[dict]] = {b["branch_code"]: [] for b in branches}
    last_application: dict[str, date] = {}
    applications: list[dict] = []

    for i, submitted in enumerate(sample_application_dates(rng), start=1):
        # Agence : uniquement parmi celles déjà ouvertes, pondérées par leur taille
        open_branches = [b for b in branches if date.fromisoformat(b["opening_date"]) <= submitted]
        w = np.array([b["weight"] for b in open_branches])
        branch = open_branches[int(rng.choice(len(open_branches), p=w / w.sum()))]

        # Client existant de l'agence (au moins 60 jours depuis sa dernière demande) ou nouveau
        eligible = [c for c in customers_by_branch[branch["branch_code"]]
                    if (submitted - last_application[c["customer_id"]]).days >= 60]
        if eligible and rng.random() < cfg.REPEAT_CUSTOMER_RATE:
            customer = eligible[int(rng.integers(len(eligible)))]
        else:
            customer = new_customer(rng, fake, f"C{len(customers) + 1:06d}", branch, submitted)
            customers.append(customer)
            customers_by_branch[branch["branch_code"]].append(customer)
        last_application[customer["customer_id"]] = submitted

        product = products[pick(rng, cfg.PRODUCT_MIX_BY_SEGMENT[customer["segment"]])]
        amount, duration, rate = draw_loan_terms(rng, product)

        # Décision : après le délai d'instruction, si la date d'extraction le permet
        decision_date = submitted + timedelta(days=int(rng.integers(*cfg.DECISION_DELAY_DAYS, endpoint=True)))
        if decision_date > cfg.AS_OF_DATE:
            status, decision_date = "PENDING", None
        elif rng.random() < cfg.APPROVAL_RATE_BY_PROFILE[customer["_profile"]]:
            status = "APPROVED"
        else:
            status = "REJECTED"

        applications.append({
            "application_id": f"A{i:06d}",
            "customer_id": customer["customer_id"],
            "branch_code": branch["branch_code"],
            "product_code": product["product_code"],
            "submitted_date": submitted,
            "requested_amount": amount,
            "requested_duration_months": duration,
            "proposed_annual_rate": rate,
            "status": status,
            "decision_date": decision_date,
            "updated_at": random_timestamp(rng, decision_date or submitted),
        })

    return customers, applications


# ---------------------------------------------------------------------------
# 4. Prêts, échéanciers et paiements
# ---------------------------------------------------------------------------

def payment_delay(rng, profile: str) -> int:
    """Nombre de jours de retard pour une échéance, selon le profil du client."""
    if profile == "good_payer":
        return 0 if rng.random() < 0.92 else int(rng.integers(1, 11))
    # late_regularizing (et defaulting avant sa rupture de paiement)
    if rng.random() < 0.30:
        return int(rng.integers(15, 46)) if rng.random() < 0.6 else int(rng.integers(46, 96))
    return int(rng.integers(0, 6))


def build_loans_schedule_payments(rng, customers, applications):
    profile_of = {c["customer_id"]: c["_profile"] for c in customers}
    fee_rate = {p["product_code"]: p["fee_rate"] for p in cfg.PRODUCTS}
    loans, installments, payments = [], [], []

    for app in applications:
        if app["status"] != "APPROVED":
            continue
        disbursed = app["decision_date"] + timedelta(
            days=int(rng.integers(*cfg.DISBURSEMENT_DELAY_DAYS, endpoint=True)))
        if disbursed > cfg.AS_OF_DATE:
            continue  # accordé mais pas encore versé à la date d'extraction

        loan_id = f"L{len(loans) + 1:06d}"
        principal = app["requested_amount"]
        rate, n = app["proposed_annual_rate"], app["requested_duration_months"]
        monthly = round(annuity_payment(principal, rate, n), 2)
        due_day = min(disbursed.day, 28)

        loans.append({
            "loan_id": loan_id,
            "application_id": app["application_id"],
            "customer_id": app["customer_id"],
            "branch_code": app["branch_code"],
            "product_code": app["product_code"],
            "principal_amount": principal,
            "annual_interest_rate": rate,
            "duration_months": n,
            "monthly_payment": monthly,
            "fee_amount": round(principal * fee_rate[app["product_code"]], 2),
            "disbursement_date": disbursed,
            "first_due_date": add_months(disbursed, 1, due_day),
            "updated_at": random_timestamp(rng, disbursed),
        })

        profile = profile_of[app["customer_id"]]
        # Un client « defaulting » cesse de payer après quelques échéances
        stop_at = int(rng.integers(2, max(3, min(n, 12)) + 1)) if profile == "defaulting" else None
        balance = principal

        for k in range(1, n + 1):
            due = add_months(disbursed, k, due_day)
            interest = round(balance * rate / 12, 2)
            principal_part = round(balance, 2) if k == n else round(monthly - interest, 2)
            balance = round(balance - principal_part, 2)
            installments.append({
                "loan_id": loan_id,
                "installment_number": k,
                "due_date": due,
                "principal_due": principal_part,
                "interest_due": interest,
                "total_due": round(principal_part + interest, 2),
                "updated_at": random_timestamp(rng, disbursed),
            })

            if due > cfg.AS_OF_DATE or (stop_at is not None and k > stop_at):
                continue  # échéance future, ou client en rupture de paiement
            paid_on = due + timedelta(days=payment_delay(rng, profile))
            if paid_on > cfg.AS_OF_DATE:
                continue  # en retard et pas encore payée à la date d'extraction
            payments.append({
                "payment_id": f"P{len(payments) + 1:07d}",
                "loan_id": loan_id,
                "installment_number": k,
                "payment_date": paid_on,
                "amount": round(principal_part + interest, 2),
                "payment_method": str(rng.choice(PAYMENT_METHODS, p=PAYMENT_METHOD_WEIGHTS)),
                "updated_at": random_timestamp(rng, paid_on),
            })

    return pd.DataFrame(loans), pd.DataFrame(installments), pd.DataFrame(payments)


# ---------------------------------------------------------------------------
# 5. Anomalies volontaires
# ---------------------------------------------------------------------------

def inject_anomalies(rng, applications: pd.DataFrame, loans: pd.DataFrame, payments: pd.DataFrame):
    log = []
    n = cfg.ANOMALIES

    # Montants négatifs et agences inconnues : sur des demandes distinctes
    picked = rng.choice(applications.index,
                        n["negative_requested_amount"] + n["unknown_branch"], replace=False)
    negative, unknown = picked[: n["negative_requested_amount"]], picked[n["negative_requested_amount"]:]
    applications.loc[negative, "requested_amount"] *= -1
    applications.loc[unknown, "branch_code"] = "BR99"
    log += [("applications", applications.at[i, "application_id"], "negative_requested_amount") for i in negative]
    log += [("applications", applications.at[i, "application_id"], "unknown_branch") for i in unknown]

    # Paiement antidaté : choisi parmi les premières échéances
    disbursed = loans.set_index("loan_id")["disbursement_date"]
    firsts = payments.index[payments["installment_number"] == 1]
    backdated = rng.choice(firsts, n["payment_before_disbursement"], replace=False)
    for i in backdated:
        loan_start = disbursed[payments.at[i, "loan_id"]]
        payments.at[i, "payment_date"] = loan_start - timedelta(days=int(rng.integers(3, 21)))
        log.append(("payments", payments.at[i, "payment_id"], "payment_before_disbursement"))

    # Doublons : copie exacte de lignes de paiement (hors lignes déjà altérées)
    candidates = payments.index.difference(backdated)
    duplicated = rng.choice(candidates, n["duplicate_payment"], replace=False)
    log += [("payments", payments.at[i, "payment_id"], "duplicate_payment") for i in duplicated]
    payments = pd.concat([payments, payments.loc[duplicated]]).sort_values(["payment_id"], kind="stable")

    anomalies = pd.DataFrame(log, columns=["table_name", "record_id", "anomaly_type"])
    return applications, payments.reset_index(drop=True), anomalies


# ---------------------------------------------------------------------------
# 6. Écriture des fichiers
# ---------------------------------------------------------------------------

def write_csv(df: pd.DataFrame, folder: str, name: str) -> None:
    path = cfg.OUTPUT_DIR / folder / f"{name}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")
    print(f"  {folder}/{name}.csv".ljust(42), f"{len(df):>8,} lignes".replace(",", " "))


def main() -> None:
    rng = np.random.default_rng(cfg.SEED)
    Faker.seed(cfg.SEED)
    fake = Faker("fr_FR")

    print(f"Génération Atelia Crédit : {cfg.START_DATE} -> {cfg.AS_OF_DATE} (seed={cfg.SEED})")
    customers, applications = build_customers_and_applications(rng, fake)
    loans, installments, payments = build_loans_schedule_payments(rng, customers, applications)

    customers_df = pd.DataFrame(customers)
    applications_df = pd.DataFrame(applications)
    applications_df, payments, anomalies = inject_anomalies(rng, applications_df, loans, payments)

    # Une nouvelle génération repart de zéro : l'ancienne sauvegarde de mise à jour CRM n'a plus de sens
    (cfg.OUTPUT_DIR / "crm" / "customers_v1.csv").unlink(missing_ok=True)

    write_csv(build_branches(), "reference", "branches")
    write_csv(build_products(), "reference", "products")
    write_csv(customers_df.drop(columns="_profile"), "crm", "customers")
    write_csv(applications_df, "core_banking", "applications")
    write_csv(loans, "core_banking", "loans")
    write_csv(installments, "core_banking", "installments")
    write_csv(payments, "core_banking", "payments")
    write_csv(customers_df[["customer_id", "_profile"]].rename(columns={"_profile": "behavior_profile"}),
              "_ground_truth", "customer_profiles")
    write_csv(anomalies, "_ground_truth", "injected_anomalies")

    decided = applications_df[applications_df["status"] != "PENDING"]
    print(f"Taux d'acceptation : {(decided['status'] == 'APPROVED').mean():.1%}")
    print(f"Fichiers écrits dans {cfg.OUTPUT_DIR}")


if __name__ == "__main__":
    main()
