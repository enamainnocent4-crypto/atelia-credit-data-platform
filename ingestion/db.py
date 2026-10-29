"""Accès à PostgreSQL : tables raw, marque-pages et journal d'ingestion."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Any

import psycopg
from psycopg import sql

log = logging.getLogger(__name__)

RAW_SCHEMA = "raw"
METADATA_COLUMNS = ["_loaded_at", "_source", "_batch_id"]

METADATA_DDL = """
CREATE TABLE IF NOT EXISTS raw._ingestion_state (
    source_name      text PRIMARY KEY,           -- ex. 'api.payments'
    watermark        text,                       -- dernier updated_at (ou date) chargé
    last_success_at  timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS raw._ingestion_log (
    batch_id         uuid        NOT NULL,
    source_name      text        NOT NULL,
    load_mode        text        NOT NULL,       -- 'full' ou 'incremental'
    started_at       timestamptz NOT NULL,
    finished_at      timestamptz NOT NULL,
    rows_loaded      integer     NOT NULL,
    watermark_before text,
    watermark_after  text,
    status           text        NOT NULL,       -- 'SUCCESS' ou 'FAILED'
    error_message    text,
    PRIMARY KEY (batch_id, source_name)
);
"""


def ensure_metadata_tables(conn: psycopg.Connection) -> None:
    conn.execute(METADATA_DDL)


def ensure_raw_table(conn: psycopg.Connection, table: str, columns: Sequence[str]) -> None:
    """Crée la table raw si besoin : toutes les colonnes en texte, plus les colonnes techniques.

    Si la source ajoute une colonne (« dérive de schéma »), elle est ajoutée
    à la table au lieu de faire échouer le chargement.
    """
    ident = sql.Identifier(RAW_SCHEMA, table)
    column_defs = [sql.SQL("{} text").format(sql.Identifier(c)) for c in columns]
    column_defs += [
        sql.SQL("_loaded_at timestamptz NOT NULL"),
        sql.SQL("_source text NOT NULL"),
        sql.SQL("_batch_id uuid NOT NULL"),
    ]
    conn.execute(sql.SQL("CREATE TABLE IF NOT EXISTS {} ({})").format(ident, sql.SQL(", ").join(column_defs)))

    existing = {row[0] for row in conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema = %s AND table_name = %s",
        (RAW_SCHEMA, table),
    )}
    for column in columns:
        if column not in existing:
            log.warning("Dérive de schéma : nouvelle colonne %s.%s ajoutée", table, column)
            conn.execute(sql.SQL("ALTER TABLE {} ADD COLUMN {} text").format(ident, sql.Identifier(column)))


def truncate(conn: psycopg.Connection, table: str) -> None:
    conn.execute(sql.SQL("TRUNCATE TABLE {}").format(sql.Identifier(RAW_SCHEMA, table)))


def truncate_if_exists(conn: psycopg.Connection, table: str) -> None:
    exists = conn.execute("SELECT to_regclass(%s)", (f"{RAW_SCHEMA}.{table}",)).fetchone()[0]
    if exists:
        truncate(conn, table)


def copy_rows(
    conn: psycopg.Connection,
    table: str,
    columns: Sequence[str],
    rows: Iterable[Sequence[Any]],
    source: str,
    batch_id: str,
    loaded_at: datetime,
) -> int:
    """Charge les lignes avec COPY, bien plus rapide que des INSERT ligne à ligne."""
    target = sql.SQL("COPY {} ({}) FROM STDIN").format(
        sql.Identifier(RAW_SCHEMA, table),
        sql.SQL(", ").join(sql.Identifier(c) for c in [*columns, *METADATA_COLUMNS]),
    )
    count = 0
    with conn.cursor() as cur, cur.copy(target) as copy:
        for row in rows:
            values = [None if v is None else str(v) for v in row]
            copy.write_row([*values, loaded_at, source, batch_id])
            count += 1
    return count


def get_watermark(conn: psycopg.Connection, source_name: str) -> str | None:
    row = conn.execute(
        "SELECT watermark FROM raw._ingestion_state WHERE source_name = %s", (source_name,)
    ).fetchone()
    return row[0] if row else None


def set_watermark(conn: psycopg.Connection, source_name: str, watermark: str | None, at: datetime) -> None:
    conn.execute(
        """
        INSERT INTO raw._ingestion_state (source_name, watermark, last_success_at)
        VALUES (%s, %s, %s)
        ON CONFLICT (source_name)
        DO UPDATE SET watermark = EXCLUDED.watermark, last_success_at = EXCLUDED.last_success_at
        """,
        (source_name, watermark, at),
    )


def write_log(conn: psycopg.Connection, **entry: Any) -> None:
    conn.execute(
        """
        INSERT INTO raw._ingestion_log (batch_id, source_name, load_mode, started_at, finished_at,
            rows_loaded, watermark_before, watermark_after, status, error_message)
        VALUES (%(batch_id)s, %(source_name)s, %(load_mode)s, %(started_at)s, %(finished_at)s,
            %(rows_loaded)s, %(watermark_before)s, %(watermark_after)s, %(status)s, %(error_message)s)
        """,
        entry,
    )
