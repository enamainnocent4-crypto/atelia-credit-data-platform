"""Client de l'API core banking : parcourt toutes les pages d'une ressource."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import requests

PAGE_SIZE = 5_000          # maximum autorisé par l'API
TIMEOUT_SECONDS = 60


class CoreBankingClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        # Une session réutilise la même connexion HTTP pour toutes les pages
        self.session = requests.Session()
        self.session.headers["X-API-Key"] = api_key

    def check_health(self) -> None:
        """Échoue tout de suite, avec un message clair, si l'API ne répond pas."""
        try:
            self.session.get(f"{self.base_url}/health", timeout=10).raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(
                f"API core banking injoignable sur {self.base_url} : Docker Desktop est-il lancé ? "
                f"(docker compose ps)"
            ) from exc

    def iter_pages(self, resource: str, updated_since: str | None) -> Iterator[list[dict[str, Any]]]:
        """Renvoie les pages une par une, jusqu'à ce que next_offset soit vide."""
        offset: int | None = 0
        while offset is not None:
            params: dict[str, Any] = {"limit": PAGE_SIZE, "offset": offset}
            if updated_since:
                params["updated_since"] = updated_since
            response = self.session.get(f"{self.base_url}/{resource}", params=params, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
            body = response.json()
            yield body["data"]
            offset = body["next_offset"]
