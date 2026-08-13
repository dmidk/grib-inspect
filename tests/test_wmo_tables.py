"""Self-check for the WMO table fallback. Run: python tests/test_wmo_tables.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grib_inspect.wmo_tables import lookup_parameter_name


def test_resolves_code_eccodes_reports_as_unknown():
    # discipline=0/parameterCategory=0/parameterNumber=31: eccodes' own
    # codes_get(msg, "name") returns "unknown" for this real-world code even
    # though its bundled raw Table 4.2 file defines it -- that's the whole
    # reason this fallback exists.
    name = lookup_parameter_name(0, 0, 31)
    assert name is not None
    assert "sublimation" in name.lower()


def test_resolves_other_disciplines():
    assert "solar" in lookup_parameter_name(3, 6, 3).lower()
    assert "radiation" in lookup_parameter_name(0, 4, 7).lower()


def test_reserved_code_returns_none():
    # 192-254 in this table is "Reserved for local use" -- no single entry.
    assert lookup_parameter_name(0, 0, 200) is None


def test_missing_inputs_return_none():
    assert lookup_parameter_name(None, 0, 31) is None
    assert lookup_parameter_name(0, None, 31) is None
    assert lookup_parameter_name(0, 0, None) is None


def test_unknown_discipline_returns_none_not_error():
    assert lookup_parameter_name(999, 999, 0) is None


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok {name}")
    print("all tests passed")
