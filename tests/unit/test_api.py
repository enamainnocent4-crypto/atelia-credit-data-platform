"""Tests de l'API core banking (sans Docker : l'application est appelée directement)."""

import importlib

import pytest
from fastapi.testclient import TestClient

API_KEY = "test-key"


@pytest.fixture(scope="module")
def client(small_dataset):
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("CORE_BANKING_API_KEY", API_KEY)
        mp.setenv("CORE_BANKING_DATA_DIR", str(small_dataset / "core_banking"))
        import api.main
        app_module = importlib.reload(api.main)  # relit le dossier de données configuré ci-dessus
        with TestClient(app_module.app) as test_client:
            yield test_client


AUTH = {"X-API-Key": API_KEY}


def test_health_needs_no_key(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong-key"}])
def test_data_requires_a_valid_key(client, headers):
    assert client.get("/loans", headers=headers).status_code == 401


def test_limit_above_maximum_is_rejected(client):
    assert client.get("/loans", headers=AUTH, params={"limit": 999_999}).status_code == 422


def test_pagination_returns_every_row_exactly_once(client):
    """En suivant next_offset, on récupère toutes les lignes, sans doublon ni oubli."""
    ids, offset = [], 0
    while offset is not None:
        body = client.get("/applications", headers=AUTH, params={"limit": 97, "offset": offset}).json()
        ids += [row["application_id"] for row in body["data"]]
        offset = body["next_offset"]
    assert len(ids) == body["total"]
    assert len(set(ids)) == len(ids)


def test_updated_since_only_returns_newer_rows(client):
    cutoff = "2026-06-01T00:00:00"
    body = client.get("/loans", headers=AUTH, params={"updated_since": cutoff, "limit": 5000}).json()
    assert body["total"] > 0
    assert all(row["updated_at"] > "2026-06-01 00:00:00" for row in body["data"])
