"""Tests du client BCE, avec des réponses simulées (aucun appel réseau)."""

from datetime import date
from unittest import mock

import pytest

from ingestion import ecb_client


def fake_response(status_code=200, text=""):
    response = mock.Mock(status_code=status_code, text=text)
    response.raise_for_status = mock.Mock()
    return response


def fetch_with(response):
    with mock.patch("ingestion.ecb_client.requests.get", return_value=response):
        return ecb_client.fetch_estr(date(2026, 10, 28))


def test_normal_response_is_parsed():
    rates = fetch_with(fake_response(text="KEY,TIME_PERIOD,OBS_VALUE\nX,2026-10-28,2.439\nX,2026-10-27,2.440\n"))
    assert list(rates.columns) == ["rate_date", "estr_rate"]
    assert rates["rate_date"].tolist() == ["2026-10-27", "2026-10-28"]  # trié par date


@pytest.mark.parametrize("response", [
    fake_response(text=""),                   # 200 avec corps vide (incident du 29/10/2026)
    fake_response(text="\n"),
    fake_response(status_code=404, text="No results found"),
])
def test_no_new_rate_is_not_an_error(response):
    """Rien de nouveau à publier : résultat vide, sans exception."""
    assert fetch_with(response).empty


def test_unexpected_format_raises_a_clear_error():
    with pytest.raises(ValueError, match="Format inattendu"):
        fetch_with(fake_response(text="DATE,VALUE\n2026-10-28,2.439\n"))
