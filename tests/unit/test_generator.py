"""Tests du générateur de données synthétiques."""

import numpy as np
import pandas as pd
import pytest
from faker import Faker

from data_generator import config as cfg
from data_generator import generate


def read(dataset, name):
    return pd.read_csv(dataset / name)


def test_same_seed_gives_identical_data(monkeypatch):
    """Reproductibilité : la même graine produit exactement les mêmes demandes."""
    monkeypatch.setattr(cfg, "N_APPLICATIONS", 200)

    def run():
        Faker.seed(cfg.SEED)
        return generate.build_customers_and_applications(np.random.default_rng(cfg.SEED), Faker("fr_FR"))

    assert run() == run()


def test_annuity_payment_matches_known_value():
    """Mensualité de référence : 10 000 EUR à 6 % sur 12 mois = 860,66 EUR."""
    assert generate.annuity_payment(10_000, 0.06, 12) == pytest.approx(860.66, abs=0.01)


def test_each_schedule_repays_exactly_the_principal(small_dataset):
    """La somme du capital des échéances d'un prêt est égale au capital prêté."""
    loans = read(small_dataset, "core_banking/loans.csv").set_index("loan_id")
    installments = read(small_dataset, "core_banking/installments.csv")
    repaid = installments.groupby("loan_id")["principal_due"].sum()
    gap = (repaid - loans["principal_amount"]).abs()
    assert gap.max() < 0.02


def test_nothing_happens_after_the_extraction_date(small_dataset):
    """Aucun paiement ni décaissement n'est postérieur à la date d'extraction."""
    as_of = cfg.AS_OF_DATE.isoformat()
    payments = read(small_dataset, "core_banking/payments.csv")
    loans = read(small_dataset, "core_banking/loans.csv")
    assert payments["payment_date"].max() <= as_of
    assert loans["disbursement_date"].max() <= as_of


def test_injected_anomalies_match_the_configuration(small_dataset):
    """Le générateur injecte exactement le nombre d'anomalies prévu, pour chaque type."""
    anomalies = read(small_dataset, "_ground_truth/injected_anomalies.csv")
    assert anomalies["anomaly_type"].value_counts().to_dict() == cfg.ANOMALIES


def test_injected_anomalies_are_really_in_the_data(small_dataset):
    """Chaque anomalie tracée se retrouve bien dans les fichiers sources."""
    anomalies = read(small_dataset, "_ground_truth/injected_anomalies.csv")
    applications = read(small_dataset, "core_banking/applications.csv")
    payments = read(small_dataset, "core_banking/payments.csv")

    negative_ids = anomalies.loc[anomalies["anomaly_type"] == "negative_requested_amount", "record_id"]
    assert (applications.set_index("application_id").loc[negative_ids, "requested_amount"] < 0).all()

    duplicated_ids = anomalies.loc[anomalies["anomaly_type"] == "duplicate_payment", "record_id"]
    counts = payments["payment_id"].value_counts()
    assert (counts.loc[duplicated_ids] == 2).all()


def test_customer_profiles_are_hidden_from_the_crm_export(small_dataset):
    """La vérité cachée (profil de comportement) ne doit pas fuiter dans l'export CRM."""
    customers = read(small_dataset, "crm/customers.csv")
    assert not any("profile" in column for column in customers.columns)
