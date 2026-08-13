"""Fallback parameter names from eccodes' own bundled WMO GRIB2 Table 4.2 files.

eccodes' own `name`/`shortName` concept resolution doesn't cover every numeric
code that its bundled raw code tables (grib2/tables/<version>/4.2.<D>.<C>.table)
actually define -- e.g. discipline=0/parameterCategory=0/parameterNumber=31
("Latent heat net flux due to sublimation") comes back "unknown" from
codes_get(msg, "name") even though the table text is right there on disk. This
reads those same bundled files directly as a fallback, so no second data
source (fetched or vendored) is needed.
"""

from __future__ import annotations

from pathlib import Path

import eccodes

_table_cache: dict[tuple[int, int], dict[int, str]] = {}
_latest_version: int | None = None


def _tables_root() -> Path:
    return Path(eccodes.codes_definition_path()) / "grib2" / "tables"


def _latest_table_version() -> int:
    global _latest_version
    if _latest_version is None:
        versions = [int(p.name) for p in _tables_root().iterdir() if p.name.isdigit()]
        _latest_version = max(versions)
    return _latest_version


def _load_table(discipline: int, category: int) -> dict[int, str]:
    key = (discipline, category)
    if key in _table_cache:
        return _table_cache[key]

    table_file = _tables_root() / str(_latest_table_version()) / f"4.2.{discipline}.{category}.table"
    entries: dict[int, str] = {}
    if table_file.exists():
        for line in table_file.read_text().splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split(None, 2)
            if len(parts) == 3 and parts[0].isdigit():
                entries[int(parts[0])] = parts[2]

    _table_cache[key] = entries
    return entries


def lookup_parameter_name(discipline, category, number) -> str | None:
    """Look up a GRIB2 parameter's name straight from Table 4.2, bypassing
    eccodes' concept resolution. Returns None if any input is missing/None
    or the table has no entry for that code (e.g. reserved/local-use)."""
    if discipline is None or category is None or number is None:
        return None
    return _load_table(int(discipline), int(category)).get(int(number))
