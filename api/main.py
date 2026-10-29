"""API « core banking » d'Atelia Crédit.

Simule le système bancaire central qui gère les demandes, les prêts, les
échéances et les paiements. Le pipeline d'ingestion (étape 4) l'interroge comme
il interrogerait le vrai système d'une banque.

- Authentification : clé d'API dans l'en-tête X-API-Key
- Pagination       : paramètres limit / offset
- Incrémental      : paramètre updated_since (ne renvoie que ce qui a changé)
- Documentation    : générée automatiquement sur /docs

Lancement local (depuis la racine du projet) :
    uvicorn api.main:app --port 8100
"""

from __future__ import annotations

import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Security, status
from fastapi.security import APIKeyHeader

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("CORE_BANKING_DATA_DIR", PROJECT_ROOT / "data" / "generated" / "core_banking"))

# Chaque ressource de l'API et sa clé (pour un tri stable entre deux pages)
RESOURCES: dict[str, list[str]] = {
    "applications": ["application_id"],
    "loans": ["loan_id"],
    "installments": ["loan_id", "installment_number"],
    "payments": ["payment_id"],
}

MAX_LIMIT = 5_000
TABLES: dict[str, pd.DataFrame] = {}


# ---------------------------------------------------------------------------
# Chargement des données au démarrage
# ---------------------------------------------------------------------------

def load_tables() -> None:
    """Charge les fichiers du générateur en mémoire, triés pour la pagination."""
    missing = [name for name in RESOURCES if not (DATA_DIR / f"{name}.csv").exists()]
    if missing:
        raise RuntimeError(
            f"Fichiers introuvables dans {DATA_DIR} : {missing}. "
            "Lancez d'abord : python -m data_generator.generate"
        )
    for name, keys in RESOURCES.items():
        df = pd.read_csv(DATA_DIR / f"{name}.csv")
        # Horodatage technique utilisé pour filtrer ; il n'est pas renvoyé tel quel
        df["_updated_at"] = pd.to_datetime(df["updated_at"])
        # Tri stable : d'abord par date de mise à jour, puis par identifiant.
        # Sans ordre garanti, une ligne pourrait apparaître sur deux pages, ou sur aucune.
        TABLES[name] = df.sort_values(["_updated_at", *keys], kind="stable").reset_index(drop=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not os.getenv("CORE_BANKING_API_KEY"):
        raise RuntimeError("Variable CORE_BANKING_API_KEY absente : définissez-la dans .env")
    load_tables()
    yield


app = FastAPI(
    title="Atelia Crédit — Core Banking API",
    description="Système bancaire central simulé : demandes, prêts, échéances et paiements.",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Sécurité : clé d'API
# ---------------------------------------------------------------------------

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: Annotated[str | None, Security(api_key_header)]) -> None:
    expected = os.getenv("CORE_BANKING_API_KEY", "")
    # compare_digest compare en temps constant : on ne peut pas deviner la clé
    # caractère par caractère en mesurant le temps de réponse.
    if not api_key or not secrets.compare_digest(api_key, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Clé d'API absente ou invalide")


# ---------------------------------------------------------------------------
# Points d'accès
# ---------------------------------------------------------------------------

@app.get("/health", tags=["supervision"])
def health() -> dict[str, Any]:
    """Vérifie que l'API répond et que les données sont chargées (sans authentification)."""
    return {"status": "ok", "rows": {name: len(df) for name, df in TABLES.items()}}


def paginate(name: str, updated_since: datetime | None, limit: int, offset: int) -> dict[str, Any]:
    df = TABLES[name]
    if updated_since is not None:
        # Strictement après : la ligne déjà chargée au dernier passage n'est pas renvoyée
        df = df[df["_updated_at"] > pd.Timestamp(updated_since).tz_localize(None)]

    total = len(df)
    page = df.iloc[offset: offset + limit].drop(columns="_updated_at")
    records = page.astype(object).where(page.notna(), None).to_dict(orient="records")
    next_offset = offset + limit if offset + limit < total else None

    return {
        "resource": name,
        "total": total,
        "limit": limit,
        "offset": offset,
        "next_offset": next_offset,
        "count": len(records),
        "data": records,
    }


def make_endpoint(name: str):
    def endpoint(
        updated_since: Annotated[datetime | None, Query(
            description="Ne renvoie que les lignes modifiées après cette date (ISO 8601)")] = None,
        limit: Annotated[int, Query(ge=1, le=MAX_LIMIT, description="Nombre de lignes par page")] = 1_000,
        offset: Annotated[int, Query(ge=0, description="Position de départ dans le résultat")] = 0,
    ) -> dict[str, Any]:
        return paginate(name, updated_since, limit, offset)

    endpoint.__name__ = f"list_{name}"
    endpoint.__doc__ = f"Liste paginée des {name}, triée par date de mise à jour."
    return endpoint


for resource in RESOURCES:
    app.get(f"/{resource}", tags=["core banking"], dependencies=[Depends(require_api_key)])(
        make_endpoint(resource)
    )
