"""Assert-based self-check for the diff logic. Run: python tests/test_compare.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grib_inspect.compare import (
    diff_records,
    find_duplicates,
    group_by_identity,
    render_html,
    render_report,
    summarize_changed_keys,
)


def record(shortname, level, **keys):
    return {
        "identity": {
            "shortName": shortname,
            "typeOfLevel": "heightAboveGround",
            "level": level,
        },
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
    assert diff.differs[0]["changed_keys"] == {
        "packingType": ("grid_simple", "grid_ccsds")
    }


def test_duplicate_identity_reported():
    a = [record("2t", 2, bitsPerValue=16), record("2t", 2, bitsPerValue=24)]
    b = [record("2t", 2, bitsPerValue=16)]
    diff = diff_records(a, b)
    assert len(diff.duplicate_identities_a) == 1
    # last write wins: bitsPerValue=24 vs 16 -> differs
    assert len(diff.differs) == 1


def test_render_html_contains_expected_sections():
    a = [record("2t", 2, packingType="grid_simple"), record("10u", 10)]
    b = [record("2t", 2, packingType="grid_ccsds")]
    diff = diff_records(a, b)
    out = render_html(diff, "cy43h", "cy46h")
    assert "<html>" in out and "</html>" in out
    assert "cy43h" in out and "cy46h" in out
    assert "grid_simple" in out and "grid_ccsds" in out
    assert "10u" in out  # only-in-a entry present
    assert "class='disclaimer'" in out
    assert "Generated at" in out


def test_render_html_escapes_special_characters():
    a = [record("weird<name>", 0, units="m&s")]
    b = []
    diff = diff_records(a, b)
    out = render_html(diff, "a", "b")
    assert "<name>" not in out
    assert "&lt;name&gt;" in out


def test_render_report_includes_human_name():
    a = [record("2t", 2, name="Temperature")]
    b = []
    diff = diff_records(a, b)
    out = render_report(diff, "a", "b")
    assert "(Temperature)" in out


def test_render_html_includes_human_name():
    a = [record("2t", 2, name="Temperature")]
    b = []
    diff = diff_records(a, b)
    out = render_html(diff, "a", "b")
    assert "Temperature" in out
    assert "class='name'" in out


def test_render_omits_name_when_absent():
    a = [record("2t", 2)]  # no "name" key captured
    b = []
    diff = diff_records(a, b)
    report = render_report(diff, "a", "b")
    html_out = render_html(diff, "a", "b")
    assert "(None)" not in report
    assert "class='name'" not in html_out


def test_group_by_identity_groups_all_matches():
    a = [
        record("2t", 2, bitsPerValue=16),
        record("2t", 2, bitsPerValue=24),
        record("10u", 10),
    ]
    groups = group_by_identity(a)
    sizes = sorted(len(g) for g in groups.values())
    assert sizes == [1, 2]


def test_find_duplicates_returns_only_groups_with_2_plus():
    a = [
        record("2t", 2, bitsPerValue=16),
        record("2t", 2, bitsPerValue=24),
        record("10u", 10),
    ]
    dupes = find_duplicates(a)
    assert len(dupes) == 1
    assert len(dupes[0]) == 2
    assert {r["keys"]["bitsPerValue"] for r in dupes[0]} == {16, 24}


def test_find_duplicates_empty_when_all_unique():
    a = [record("2t", 2), record("10u", 10)]
    assert find_duplicates(a) == []


def test_summarize_changed_keys_consistent_change():
    a = [
        record("2t", 2, centre="ekmi", packingType="grid_simple"),
        record("10u", 10, centre="ekmi", packingType="grid_ccsds"),
    ]
    b = [
        record("2t", 2, centre="lfpw", packingType="grid_ccsds"),
        record("10u", 10, centre="lfpw", packingType="grid_simple"),
    ]
    diff = diff_records(a, b)
    summary = {s["key"]: s for s in summarize_changed_keys(diff)}

    assert summary["centre"]["count"] == 2
    assert summary["centre"]["total"] == 2
    assert summary["centre"]["consistent"] is True
    assert summary["centre"]["example"] == ("ekmi", "lfpw")

    # packingType flips both directions across the two entries -> not consistent
    assert summary["packingType"]["consistent"] is False
    assert summary["packingType"]["example"] is None


def test_summarize_changed_keys_sorted_by_count_desc():
    a = [
        record("2t", 2, centre="ekmi", packingType="grid_simple"),
        record("10u", 10, centre="ekmi"),
    ]
    b = [
        record("2t", 2, centre="lfpw", packingType="grid_ccsds"),
        record("10u", 10, centre="lfpw"),
    ]
    diff = diff_records(a, b)
    summary = summarize_changed_keys(diff)
    assert [s["key"] for s in summary] == ["centre", "packingType"]


def test_summarize_changed_keys_empty_when_no_differs():
    a = [record("2t", 2, centre="ekmi")]
    b = [record("2t", 2, centre="ekmi")]
    diff = diff_records(a, b)
    assert summarize_changed_keys(diff) == []


def test_render_html_includes_common_changes_summary():
    a = [record("2t", 2, centre="ekmi"), record("10u", 10, centre="ekmi")]
    b = [record("2t", 2, centre="lfpw"), record("10u", 10, centre="lfpw")]
    diff = diff_records(a, b)
    out = render_html(diff, "a", "b")
    assert "Common changes" in out
    assert "class='note'" in out
    assert "2/2" in out
    assert "ekmi" in out and "lfpw" in out


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok {name}")
    print("all tests passed")
