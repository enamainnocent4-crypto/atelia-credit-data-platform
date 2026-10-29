"""Tests d'intégration : la base a été remplie par le pipeline complet, puis par dbt.

Lancement : pytest -m integration   (PostgreSQL démarré, ingestion et dbt build faits)
"""

import pandas as pd
import psycopg
import pytest

from ingestion.settings import load_settings

pytestmark = pytest.mark.integration

# Nom du test dbt qui doit détecter chaque type d'anomalie injectée
DETECTING_TEST = {
    "duplicate_payment": "payments_payment_id_is_unique",
    "negative_requested_amount": "applications_requested_amount_is_positive",
    "unknown_branch": "applications_branch_code_exists_in_referential",
    "payment_before_disbursement": "payments_not_before_disbursement",
}


@pytest.fixture(scope="module")
def conn():
    settings = load_settings()
    with psycopg.connect(settings.db_conninfo) as connection:
        yield connection


def scalar(conn, query):
    return conn.execute(query).fetchone()[0]


def test_every_injected_anomaly_is_detected_by_dbt(conn):
    """Mesure de l'efficacité des tests : autant d'anomalies trouvées que d'injectées."""
    settings = load_settings()
    truth = pd.read_csv(settings.data_dir / "_ground_truth" / "injected_anomalies.csv")
    expected = truth["anomaly_type"].value_counts().to_dict()
    for anomaly_type, test_name in DETECTING_TEST.items():
        found = scalar(conn, f'select count(*) from audit."{test_name}"')
        assert found == expected[anomaly_type], f"{anomaly_type} : {found} trouvées, {expected[anomaly_type]} injectées"


def test_no_payment_is_lost_or_double_counted(conn):
    received = scalar(conn, "select count(distinct payment_id) from staging.stg_core_banking__payments")
    loaded = scalar(conn, "select count(*) from marts.fact_payment")
    quarantined = scalar(conn, "select count(*) from audit.quarantined_records "
                               "where table_name = 'payments' and reason not like 'Doublon%'")
    assert received == loaded + quarantined


def test_portfolio_indicators_are_plausible(conn):
    """Garde-fous métier : un PAR30 négatif ou supérieur à 100 % trahirait un bug de calcul."""
    rows = conn.execute("select par30_rate, default_rate from marts.kpi_portfolio_monthly").fetchall()
    assert rows, "kpi_portfolio_monthly est vide"
    for par30, default in rows:
        assert 0 <= par30 <= 1
        assert 0 <= default <= par30
