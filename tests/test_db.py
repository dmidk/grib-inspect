"""Assert-based self-check for the db layer. Run: python tests/test_db.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grib_inspect import db


def test_insert_and_fetch_round_trip():
    conn = db.connect(":memory:")
    db.insert_message(
        conn,
        model="cy43h",
        source_file="a.grib2",
        message_index=0,
        identity_keys=["shortName", "level"],
        identity={"shortName": "2t", "level": 2},
        keys={"packingType": "grid_simple", "bitsPerValue": 16},
        tags={"part": "sf"},
        ingested_at="2026-08-12T00:00:00",
    )
    records = db.fetch_records(conn)
    assert len(records) == 1
    record = records[0]
    assert record["identity"] == {"shortName": "2t", "level": 2}
    assert record["keys"] == {"packingType": "grid_simple", "bitsPerValue": 16}
    assert record["tags"] == {"part": "sf"}


def test_columns_are_real_and_filterable():
    conn = db.connect(":memory:")
    db.insert_message(
        conn,
        model="cy43h",
        source_file="a.grib2",
        message_index=0,
        identity_keys=["shortName"],
        identity={"shortName": "2t"},
        keys={"packingType": "grid_simple"},
        tags={},
        ingested_at="2026-08-12T00:00:00",
    )
    rows = conn.execute(
        'SELECT model FROM messages WHERE "shortName" = ? AND "packingType" = ?',
        ("2t", "grid_simple"),
    ).fetchall()
    assert len(rows) == 1


def test_second_scan_adds_new_columns_without_disturbing_first():
    conn = db.connect(":memory:")
    db.insert_message(
        conn,
        model="cy43h",
        source_file="a.grib2",
        message_index=0,
        identity_keys=["shortName"],
        identity={"shortName": "2t"},
        keys={"packingType": "grid_simple"},
        tags={},
        ingested_at="2026-08-12T00:00:00",
    )
    db.insert_message(
        conn,
        model="cy43h",
        source_file="b.grib2",
        message_index=0,
        identity_keys=["shortName"],
        identity={"shortName": "10u"},
        keys={"gridType": "lambert"},  # a key the first row never had
        tags={},
        ingested_at="2026-08-12T00:00:01",
    )
    records = db.fetch_records(conn)
    first, second = records
    assert first["keys"] == {"packingType": "grid_simple", "gridType": None}
    assert second["keys"] == {"packingType": None, "gridType": "lambert"}


def test_rejects_unsafe_column_name():
    conn = db.connect(":memory:")
    try:
        db.insert_message(
            conn,
            model="x",
            source_file="a.grib2",
            message_index=0,
            identity_keys=["bad; DROP TABLE messages"],
            identity={"bad; DROP TABLE messages": "boom"},
            keys={},
            tags={},
            ingested_at="2026-08-12T00:00:00",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for unsafe column name")


def test_rejects_reserved_column_name():
    conn = db.connect(":memory:")
    try:
        db.insert_message(
            conn,
            model="x",
            source_file="a.grib2",
            message_index=0,
            identity_keys=["model"],
            identity={"model": "clash"},
            keys={},
            tags={},
            ingested_at="2026-08-12T00:00:00",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for reserved column name")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok {name}")
    print("all tests passed")
