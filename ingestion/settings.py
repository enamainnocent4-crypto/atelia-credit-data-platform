"""Configuration du pipeline, lue dans le fichier .env (jamais écrite dans le code)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Première date demandée à la BCE lors du tout premier chargement
ECB_HISTORY_START = date(2024, 11, 1)


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    api_base_url: str
    api_key: str
    data_dir: Path

    @property
    def db_conninfo(self) -> str:
        return (f"host={self.db_host} port={self.db_port} dbname={self.db_name} "
                f"user={self.db_user} password={self.db_password}")


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Variable {name} absente du fichier .env")
    return value


def load_settings() -> Settings:
    return Settings(
        db_host=os.getenv("POSTGRES_HOST", "localhost"),
        db_port=int(os.getenv("POSTGRES_PORT", "55432")),
        db_name=_required("POSTGRES_DB"),
        db_user=_required("POSTGRES_USER"),
        db_password=_required("POSTGRES_PASSWORD"),
        api_base_url=os.getenv("API_BASE_URL", f"http://localhost:{os.getenv('API_PORT', '8100')}"),
        api_key=_required("CORE_BANKING_API_KEY"),
        data_dir=PROJECT_ROOT / "data" / "generated",
    )
