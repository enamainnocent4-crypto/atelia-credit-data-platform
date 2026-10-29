"""Pipeline d'ingestion d'Atelia Crédit : sources -> couche raw de PostgreSQL.

Principes :
- raw est FIDÈLE : les données sont stockées telles que reçues (texte),
  anomalies comprises. Le nettoyage se fait dans dbt.
- Le pipeline est IDEMPOTENT : chaque source est chargée dans une transaction.
  Si quelque chose échoue, rien n'est écrit et le marque-page ne bouge pas ;
  une relance reprend exactement au même point, sans doublon.
- Le pipeline est INCRÉMENTAL pour les grosses sources : il ne demande que ce
  qui a changé depuis le dernier passage (marque-page dans raw._ingestion_state).
- Tout est TRACÉ dans raw._ingestion_log et dans logs/ingestion.log.

Lancement, depuis la racine du projet :
    python -m ingestion.run                    # chargement normal (incrémental)
    python -m ingestion.run --full-refresh     # tout recharger depuis zéro
    python -m ingestion.run --only api         # une seule famille de sources
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import psycopg

from ingestion import db
from ingestion.core_banking_client import CoreBankingClient
from ingestion.ecb_client import fetch_estr
from ingestion.settings import ECB_HISTORY_START, PROJECT_ROOT, Settings, load_settings

log = logging.getLogger("ingestion")


@dataclass
class Result:
    rows: int
    watermark_after: str | None


# ---------------------------------------------------------------------------
# Les trois façons de charger une source
# ---------------------------------------------------------------------------

def load_csv_full(conn, settings: Settings, table: str, relative_path: str, ctx: dict) -> Result:
    """Rechargement complet d'un fichier : on vide la table puis on recharge tout."""
    path = settings.data_dir / relative_path
    if not path.exists():
        raise FileNotFoundError(f"{path} introuvable : lancez d'abord python -m data_generator.generate")
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        columns = next(reader)
        db.ensure_raw_table(conn, table, columns)
        db.truncate(conn, table)
        # Un CSV ne connaît pas la valeur « vide » : une cellule vide devient NULL
        rows = ([v if v != "" else None for v in row] for row in reader)
        count = db.copy_rows(conn, table, columns, rows, ctx["source"], ctx["batch_id"], ctx["loaded_at"])
    return Result(count, None)


def load_api_incremental(conn, client: CoreBankingClient, table: str, ctx: dict) -> Result:
    """Ne demande à l'API que les lignes modifiées depuis le marque-page."""
    watermark = ctx["watermark_before"]
    since = watermark.replace(" ", "T") if watermark else None
    columns: list[str] | None = None
    count, max_updated = 0, watermark

    for page in client.iter_pages(table, since):
        if not page:
            continue
        if columns is None:  # la première page donne la liste des colonnes
            columns = list(page[0].keys())
            db.ensure_raw_table(conn, table, columns)
        rows = [[record.get(c) for c in columns] for record in page]
        count += db.copy_rows(conn, table, columns, rows, ctx["source"], ctx["batch_id"], ctx["loaded_at"])
        # Le nouveau marque-page vient de la SOURCE (updated_at), pas de l'horloge du PC
        page_max = max(r["updated_at"] for r in page)
        max_updated = page_max if max_updated is None else max(max_updated, page_max)

    return Result(count, max_updated)


def load_ecb_incremental(conn, ctx: dict) -> Result:
    """Demande à la BCE les cotations postérieures à la dernière date chargée."""
    watermark = ctx["watermark_before"]
    start = date.fromisoformat(watermark) + timedelta(days=1) if watermark else ECB_HISTORY_START
    if start > date.today():
        return Result(0, watermark)
    rates = fetch_estr(start)
    if rates.empty:
        return Result(0, watermark)
    columns = list(rates.columns)
    db.ensure_raw_table(conn, "ecb_estr_rates", columns)
    count = db.copy_rows(conn, "ecb_estr_rates", columns, rates.itertuples(index=False),
                         ctx["source"], ctx["batch_id"], ctx["loaded_at"])
    return Result(count, str(rates["rate_date"].max()))


# ---------------------------------------------------------------------------
# Exécution d'une source dans sa propre transaction
# ---------------------------------------------------------------------------

def run_source(conn, batch_id: str, source: str, mode: str, loader: Callable[[dict], Result],
               full_refresh: bool) -> tuple[str, int]:
    started = datetime.now(UTC)
    ctx = {"source": source, "batch_id": batch_id, "loaded_at": started, "watermark_before": None}
    try:
        with conn.transaction():
            if mode == "incremental":
                if full_refresh:
                    # Vidage DANS la transaction : si le rechargement échoue, l'ancien contenu revient
                    db.truncate_if_exists(conn, TABLE_OF[source])
                else:
                    ctx["watermark_before"] = db.get_watermark(conn, source)
            result = loader(ctx)
            # Marque-page et données sont validés ENSEMBLE : impossible d'avoir l'un sans l'autre
            db.set_watermark(conn, source, result.watermark_after, started)
            db.write_log(conn, batch_id=batch_id, source_name=source, load_mode=mode,
                         started_at=started, finished_at=datetime.now(UTC),
                         rows_loaded=result.rows, watermark_before=ctx["watermark_before"],
                         watermark_after=result.watermark_after, status="SUCCESS", error_message=None)
        log.info("%-22s %-12s %8d lignes   marque-page : %s", source, mode, result.rows, result.watermark_after or "-")
        return "SUCCESS", result.rows
    except Exception as exc:  # noqa: BLE001 - on trace toute erreur puis on passe à la source suivante
        log.error("%-22s ÉCHEC : %s", source, exc)
        with conn.transaction():
            db.write_log(conn, batch_id=batch_id, source_name=source, load_mode=mode,
                         started_at=started, finished_at=datetime.now(UTC), rows_loaded=0,
                         watermark_before=ctx["watermark_before"], watermark_after=None,
                         status="FAILED", error_message=str(exc)[:1000])
        return "FAILED", 0


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

CSV_SOURCES = [
    ("csv.branches", "branches", "reference/branches.csv"),
    ("csv.products", "products", "reference/products.csv"),
    ("csv.customers", "customers", "crm/customers.csv"),
]
API_RESOURCES = ["applications", "loans", "installments", "payments"]
# Table raw alimentée par chaque source incrémentale
TABLE_OF = {f"api.{r}": r for r in API_RESOURCES} | {"api.ecb_estr": "ecb_estr_rates"}


def setup_logging() -> None:
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")
    handlers = [logging.StreamHandler(sys.stdout), logging.FileHandler(log_dir / "ingestion.log", encoding="utf-8")]
    for handler in handlers:
        handler.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=handlers)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingestion des sources Atelia Crédit vers raw")
    parser.add_argument("--full-refresh", action="store_true", help="ignorer les marque-pages et tout recharger")
    parser.add_argument("--only", choices=["csv", "api", "ecb"], help="ne charger qu'une famille de sources")
    args = parser.parse_args()

    setup_logging()
    settings = load_settings()
    batch_id = str(uuid.uuid4())
    log.info("Lot %s%s", batch_id, " (full refresh)" if args.full_refresh else "")

    statuses: list[str] = []
    total_rows = 0
    with psycopg.connect(settings.db_conninfo, autocommit=True) as conn:
        db.ensure_metadata_tables(conn)

        def run(source, mode, loader):
            nonlocal total_rows
            status, rows = run_source(conn, batch_id, source, mode, loader, args.full_refresh)
            statuses.append(status)
            total_rows += rows

        if args.only in (None, "csv"):
            for source, table, path in CSV_SOURCES:
                run(source, "full", lambda ctx, t=table, p=path: load_csv_full(conn, settings, t, p, ctx))

        if args.only in (None, "api"):
            client = CoreBankingClient(settings.api_base_url, settings.api_key)
            client.check_health()
            for resource in API_RESOURCES:
                run(f"api.{resource}", "incremental",
                    lambda ctx, r=resource: load_api_incremental(conn, client, r, ctx))

        if args.only in (None, "ecb"):
            run("api.ecb_estr", "incremental", lambda ctx: load_ecb_incremental(conn, ctx))

    failed = statuses.count("FAILED")
    log.info("Terminé : %d source(s), %d ligne(s) chargée(s), %d échec(s)", len(statuses), total_rows, failed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
