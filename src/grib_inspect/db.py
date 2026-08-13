"""SQLite storage for scanned GRIB message records. Append-only by design.

Each captured GRIB key (identity or metadata) gets its own real column,
added on demand via ALTER TABLE, so a report stays directly filterable in a
plain SQLite browser instead of hiding values inside JSON blobs. Different
scans may capture different keys (--identity-keys / --keys are config-driven
per run), so the column set grows as new keys are seen.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

BASE_COLUMNS = [
    "id",
    "model",
    "source_file",
    "message_index",
    "identity_keys",
    "tags",
    "ingested_at",
]

# GRIB key names become column names spliced directly into ALTER TABLE / INSERT
# SQL (sqlite3 can't parameterize identifiers), so validate them at this
# trust boundary -- they originate from --identity-keys / --keys CLI input.
_VALID_COLUMN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    model TEXT NOT NULL,
    source_file TEXT NOT NULL,
    message_index INTEGER NOT NULL,
    identity_keys TEXT NOT NULL,
    tags TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_model ON messages(model);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    """Open (creating if needed) a report db and ensure the base schema exists."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def _existing_columns(conn: sqlite3.Connection) -> set[str]:
    """Names of every column currently on the messages table."""
    return {row[1] for row in conn.execute("PRAGMA table_info(messages)")}


def _ensure_columns(conn: sqlite3.Connection, names: list[str]) -> None:
    """ALTER TABLE ADD COLUMN for any name not already present.

    Validates each name against `_VALID_COLUMN` and rejects collisions with
    `BASE_COLUMNS` before touching the schema (see module docstring)."""
    existing = _existing_columns(conn)
    for name in names:
        if not _VALID_COLUMN.match(name):
            raise ValueError(f"unsafe GRIB key name for column: {name!r}")
        if name in BASE_COLUMNS:
            raise ValueError(
                f"GRIB key name conflicts with a reserved column: {name!r}"
            )
        if name in existing:
            continue
        conn.execute(f'ALTER TABLE messages ADD COLUMN "{name}"')
        existing.add(name)


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
    """Insert one message row, adding any missing identity/metadata columns
    first so every captured key ends up as a real, queryable column."""
    value_columns = {**identity, **keys}
    _ensure_columns(conn, list(value_columns))

    columns = [
        "model",
        "source_file",
        "message_index",
        "identity_keys",
        "tags",
        "ingested_at",
        *value_columns,
    ]
    placeholders = ", ".join("?" for _ in columns)
    quoted = ", ".join(f'"{c}"' for c in columns)
    values = [
        model,
        source_file,
        message_index,
        json.dumps(identity_keys),
        json.dumps(tags, sort_keys=True),
        ingested_at,
        *value_columns.values(),
    ]
    conn.execute(f"INSERT INTO messages ({quoted}) VALUES ({placeholders})", values)


def fetch_records(conn: sqlite3.Connection, model: str | None = None) -> list[dict]:
    """Fetch messages (optionally filtered to one model) as records shaped
    {"model", "source_file", "message_index", "identity", "keys", "tags"},
    splitting each row's columns back into identity vs. metadata using the
    row's own stored `identity_keys`."""
    query = "SELECT * FROM messages"
    params: tuple = ()
    if model is not None:
        query += " WHERE model = ?"
        params = (model,)
    rows = conn.execute(query, params).fetchall()

    records = []
    for row in rows:
        row = dict(row)
        identity_keys = json.loads(row["identity_keys"])
        identity = {k: row.get(k) for k in identity_keys}
        keys = {
            k: v
            for k, v in row.items()
            if k not in BASE_COLUMNS and k not in identity_keys
        }
        records.append(
            {
                "model": row["model"],
                "source_file": row["source_file"],
                "message_index": row["message_index"],
                "identity": identity,
                "keys": keys,
                "tags": json.loads(row["tags"]),
            }
        )
    return records


def distinct_models(conn: sqlite3.Connection) -> list[str]:
    """Every distinct model label present in the report, sorted."""
    return [
        r[0] for r in conn.execute("SELECT DISTINCT model FROM messages ORDER BY model")
    ]
