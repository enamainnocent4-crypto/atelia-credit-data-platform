"""Client de l'API publique de la Banque centrale européenne (ECB Data Portal).

Récupère le €STR (euro short-term rate), le taux interbancaire au jour le jour
de la zone euro. Il sert à estimer le coût de refinancement d'Atelia Crédit,
donc son PNB.

Série utilisée : EST.B.EU000A2X2A25.WT
    EST           jeu de données €STR
    B             fréquence quotidienne (jours ouvrés)
    EU000A2X2A25  identifiant du €STR
    WT            taux moyen pondéré par les volumes (le taux officiel publié)

Test, depuis la racine du projet :
    python -m ingestion.ecb_client
"""

from __future__ import annotations

import io
from datetime import date

import pandas as pd
import requests

ECB_API_URL = "https://data-api.ecb.europa.eu/service/data/EST/B.EU000A2X2A25.WT"
TIMEOUT_SECONDS = 30


def fetch_estr(start: date, end: date | None = None) -> pd.DataFrame:
    """Renvoie le €STR quotidien entre `start` et `end` : colonnes rate_date, estr_rate (en %)."""
    params = {"startPeriod": start.isoformat(), "format": "csvdata", "detail": "dataonly"}
    if end is not None:
        params["endPeriod"] = end.isoformat()

    response = requests.get(ECB_API_URL, params=params, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()  # erreur claire si la BCE répond 4xx ou 5xx

    df = pd.read_csv(io.StringIO(response.text))
    expected = {"TIME_PERIOD", "OBS_VALUE"}
    if not expected.issubset(df.columns):
        raise ValueError(f"Format inattendu de la BCE : colonnes reçues {list(df.columns)}")

    return (
        df[["TIME_PERIOD", "OBS_VALUE"]]
        .rename(columns={"TIME_PERIOD": "rate_date", "OBS_VALUE": "estr_rate"})
        .sort_values("rate_date")
        .reset_index(drop=True)
    )


if __name__ == "__main__":
    rates = fetch_estr(date(2024, 11, 1))
    print(f"{len(rates)} jours de cotation, du {rates['rate_date'].iloc[0]} au {rates['rate_date'].iloc[-1]}")
    print(rates.head(3).to_string(index=False))
    print("...")
    print(rates.tail(3).to_string(index=False))
