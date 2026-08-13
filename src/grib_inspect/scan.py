"""Read a GRIB2 file with eccodes, record identity + encoding metadata per message."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

import eccodes

from . import compare, db, wmo_tables
from .config import DEFAULT_IDENTITY_KEYS, DEFAULT_METADATA_KEYS


class ScanResult(NamedTuple):
    count: int
    duplicates: list[list[dict]]  # groups of 2+ messages sharing an identity


def _get(msg, key: str):
    try:
        return eccodes.codes_get(msg, key)
    except eccodes.KeyValueNotFoundError:
        return None


def iter_messages(path: Path):
    with open(path, "rb") as f:
        while True:
            msg = eccodes.codes_grib_new_from_file(f)
            if msg is None:
                return
            try:
                yield msg
            finally:
                eccodes.codes_release(msg)


def scan_file(
    file_path: Path,
    db_path: Path,
    *,
    model: str,
    tags: dict[str, str],
    identity_keys: list[str] | None = None,
    metadata_keys: list[str] | None = None,
) -> ScanResult:
    """Append every message in file_path to db_path under the given model label.

    Returns the number of messages scanned and any identity groups (2+
    messages sharing an identity) found across the whole model afterwards.
    """
    identity_keys = identity_keys or DEFAULT_IDENTITY_KEYS
    metadata_keys = metadata_keys or DEFAULT_METADATA_KEYS
    ingested_at = datetime.now(timezone.utc).isoformat()

    conn = db.connect(db_path)
    count = 0
    try:
        for index, msg in enumerate(iter_messages(file_path)):
            identity = {k: _get(msg, k) for k in identity_keys}
            keys = {k: _get(msg, k) for k in metadata_keys}
            if "name" in keys and keys["name"] in (None, "unknown"):
                fallback = wmo_tables.lookup_parameter_name(
                    _get(msg, "discipline"),
                    _get(msg, "parameterCategory"),
                    _get(msg, "parameterNumber"),
                )
                if fallback:
                    keys["name"] = fallback
            db.insert_message(
                conn,
                model=model,
                source_file=str(file_path),
                message_index=index,
                identity_keys=identity_keys,
                identity=identity,
                keys=keys,
                tags=tags,
                ingested_at=ingested_at,
            )
            count += 1
        conn.commit()
        duplicates = compare.find_duplicates(db.fetch_records(conn, model=model))
    finally:
        conn.close()
    return ScanResult(count=count, duplicates=duplicates)
