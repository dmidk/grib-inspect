"""Assert-based self-check for the diff logic. Run: python tests/test_compare.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grib_inspect.compare import diff_records


def record(shortname, level, **keys):
    return {
        "identity": {"shortName": shortname, "typeOfLevel": "heightAboveGround", "level": level},
        "keys": keys,
    }


def test_identical():
    a = [record("2t", 2, packingType="grid_simple", bitsPerValue=16)]
    b = [record("2t", 2, packingType="grid_simple", bitsPerValue=16)]
    diff = diff_records(a, b)
    assert len(diff.identical) == 1
    assert not diff.differs
    assert not diff.only_in_a
    assert not diff.only_in_b


def test_only_in_one_side():
    a = [record("2t", 2), record("10u", 10)]
    b = [record("2t", 2)]
    diff = diff_records(a, b)
    assert len(diff.identical) == 1
    assert [r["identity"]["shortName"] for r in diff.only_in_a] == ["10u"]
    assert not diff.only_in_b


def test_differing_encoding():
    a = [record("2t", 2, packingType="grid_simple", bitsPerValue=16)]
    b = [record("2t", 2, packingType="grid_ccsds", bitsPerValue=16)]
    diff = diff_records(a, b)
    assert not diff.identical
    assert len(diff.differs) == 1
    assert diff.differs[0]["changed_keys"] == {"packingType": ("grid_simple", "grid_ccsds")}


def test_duplicate_identity_reported():
    a = [record("2t", 2, bitsPerValue=16), record("2t", 2, bitsPerValue=24)]
    b = [record("2t", 2, bitsPerValue=16)]
    diff = diff_records(a, b)
    assert len(diff.duplicate_identities_a) == 1
    # last write wins: bitsPerValue=24 vs 16 -> differs
    assert len(diff.differs) == 1


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok {name}")
    print("all tests passed")
