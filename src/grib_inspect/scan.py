"""Read a GRIB2 file with eccodes and record identity + encoding metadata per message."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import eccodes

from . import db

# Identity: what makes two messages across different files/products "the same variable".
DEFAULT_IDENTITY_KEYS = ["shortName", "typeOfLevel", "level", "stepRange"]

# Encoding/metadata keys worth reporting on. Not exhaustive by design (v1: metadata only,
# no data values) -- extend with --keys if a comparison needs more.
DEFAULT_METADATA_KEYS = [
    "name",
    "units",
    "paramId",
    "editionNumber",
    "centre",
    "subCentre",
    "generatingProcessIdentifier",
    "typeOfGeneratingProcess",
    "dataDate",
    "dataTime",
    "gridType",
    "Ni",
    "Nj",
    "packingType",
    "bitsPerValue",
    "numberOfValues",
    "missingValue",
    "typeOfFirstFixedSurface",
    "scaleFactorOfFirstFixedSurface",
    "scaledValueOfFirstFixedSurface",
]


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
) -> int:
    """Append every message in file_path to db_path under the given model label.

    Returns the number of messages scanned.
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
    finally:
        conn.close()
    return count
