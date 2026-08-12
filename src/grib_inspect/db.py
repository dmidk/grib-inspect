"""SQLite storage for scanned GRIB message records. Append-only by design."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    model TEXT NOT NULL,
    source_file TEXT NOT NULL,
    message_index INTEGER NOT NULL,
    identity_keys TEXT NOT NULL,
    identity TEXT NOT NULL,
    keys TEXT NOT NULL,
    tags TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_model_identity ON messages(model, identity);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def insert_message(
    conn: sqlite3.Connection,
    *,
    model: str,
    source_file: str,
    message_index: int,
    identity_keys: list[str],
    identity: dict,
    keys: dict,
    tags: dict,
    ingested_at: str,
) -> None:
    conn.execute(
        "INSERT INTO messages (model, source_file, message_index, identity_keys,"
        " identity, keys, tags, ingested_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            model,
            source_file,
            message_index,
            json.dumps(identity_keys),
            json.dumps(identity, sort_keys=True),
            json.dumps(keys, sort_keys=True),
            json.dumps(tags, sort_keys=True),
            ingested_at,
        ),
    )


def fetch_records(conn: sqlite3.Connection, model: str | None = None) -> list[dict]:
    query = "SELECT model, source_file, message_index, identity, keys, tags FROM messages"
    params: tuple = ()
    if model is not None:
        query += " WHERE model = ?"
        params = (model,)
    rows = conn.execute(query, params).fetchall()
    return [
        {
            "model": r[0],
            "source_file": r[1],
            "message_index": r[2],
            "identity": json.loads(r[3]),
            "keys": json.loads(r[4]),
            "tags": json.loads(r[5]),
        }
        for r in rows
    ]


def distinct_models(conn: sqlite3.Connection) -> list[str]:
    return [r[0] for r in conn.execute("SELECT DISTINCT model FROM messages ORDER BY model")]
