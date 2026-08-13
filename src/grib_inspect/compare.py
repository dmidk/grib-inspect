"""Diff two sets of scanned GRIB records by identity, then by encoding key."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field


def _identity_key(identity: dict) -> str:
    return json.dumps(identity, sort_keys=True)


@dataclass
class Diff:
    only_in_a: list[dict] = field(default_factory=list)
    only_in_b: list[dict] = field(default_factory=list)
    # each entry: {"identity", "record_a", "record_b", "changed_keys": {key: (a, b)}}
    differs: list[dict] = field(default_factory=list)
    identical: list[dict] = field(default_factory=list)
    duplicate_identities_a: list[str] = field(default_factory=list)
    duplicate_identities_b: list[str] = field(default_factory=list)


def _index_by_identity(records: list[dict]) -> tuple[dict[str, dict], list[str]]:
    index: dict[str, dict] = {}
    duplicates: list[str] = []
    for record in records:
        key = _identity_key(record["identity"])
        if key in index:
            duplicates.append(key)
        index[key] = record  # last one wins, duplicates are reported separately
    return index, duplicates


def diff_records(records_a: list[dict], records_b: list[dict]) -> Diff:
    index_a, dup_a = _index_by_identity(records_a)
    index_b, dup_b = _index_by_identity(records_b)

    result = Diff(duplicate_identities_a=dup_a, duplicate_identities_b=dup_b)
    for key, record_a in index_a.items():
        if key not in index_b:
            result.only_in_a.append(record_a)
            continue
        record_b = index_b[key]
        changed = {
            k: (record_a["keys"].get(k), record_b["keys"].get(k))
            for k in sorted(set(record_a["keys"]) | set(record_b["keys"]))
            if record_a["keys"].get(k) != record_b["keys"].get(k)
        }
        if changed:
            result.differs.append(
                {
                    "identity": record_a["identity"],
                    "record_a": record_a,
                    "record_b": record_b,
                    "changed_keys": changed,
                }
            )
        else:
            result.identical.append(record_a)

    for key, record_b in index_b.items():
        if key not in index_a:
            result.only_in_b.append(record_b)

    return result


def _fmt_identity(identity: dict) -> str:
    return ", ".join(f"{k}={v}" for k, v in identity.items())


def render_report(diff: Diff, label_a: str, label_b: str) -> str:
    lines = []
    lines.append(f"Comparing {label_a!r} vs {label_b!r}")
    lines.append(
        f"  identical: {len(diff.identical)}  differs: {len(diff.differs)}  "
        f"only in {label_a}: {len(diff.only_in_a)}  "
        f"only in {label_b}: {len(diff.only_in_b)}"
    )

    if diff.duplicate_identities_a:
        lines.append(
            f"\nWARNING: {len(diff.duplicate_identities_a)} duplicate identities "
            f"in {label_a} (last write kept)"
        )
    if diff.duplicate_identities_b:
        lines.append(
            f"WARNING: {len(diff.duplicate_identities_b)} duplicate identities "
            f"in {label_b} (last write kept)"
        )

    if diff.only_in_a:
        lines.append(f"\nOnly in {label_a} ({len(diff.only_in_a)}):")
        for record in diff.only_in_a:
            lines.append(f"  - {_fmt_identity(record['identity'])}")

    if diff.only_in_b:
        lines.append(f"\nOnly in {label_b} ({len(diff.only_in_b)}):")
        for record in diff.only_in_b:
            lines.append(f"  - {_fmt_identity(record['identity'])}")

    if diff.differs:
        lines.append(f"\nDiffers ({len(diff.differs)}):")
        for entry in diff.differs:
            lines.append(f"  - {_fmt_identity(entry['identity'])}")
            for k, (va, vb) in entry["changed_keys"].items():
                lines.append(f"      {k}: {va!r} -> {vb!r}")

    return "\n".join(lines)


def _esc(value) -> str:
    return html.escape(str(value)) if value is not None else "<em>null</em>"


def _identity_cell(identity: dict) -> str:
    return "<br>".join(
        f"<b>{html.escape(k)}</b>={_esc(v)}" for k, v in identity.items()
    )


def _changed_keys_cell(changed_keys: dict) -> str:
    return "".join(
        f"<div><b>{html.escape(k)}</b>: "
        f"<span class='val-a'>{_esc(va)}</span> &rarr; "
        f"<span class='val-b'>{_esc(vb)}</span></div>"
        for k, (va, vb) in changed_keys.items()
    )


def _identity_only_table(records: list[dict]) -> str:
    if not records:
        return "<p class='empty'>none</p>"
    rows = "".join(
        f"<tr><td>{_identity_cell(r['identity'])}</td></tr>" for r in records
    )
    return f"<table><tr><th>Identity</th></tr>{rows}</table>"


def _differs_table(entries: list[dict]) -> str:
    if not entries:
        return "<p class='empty'>none</p>"
    rows = "".join(
        f"<tr><td>{_identity_cell(e['identity'])}</td>"
        f"<td>{_changed_keys_cell(e['changed_keys'])}</td></tr>"
        for e in entries
    )
    return f"<table><tr><th>Identity</th><th>Changed keys</th></tr>{rows}</table>"


_HTML_STYLE = """
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
       margin: 2rem; color: #1a1a1a; }
h1 { font-size: 1.25rem; }
h2 { font-size: 1.05rem; margin-top: 2rem; }
table { border-collapse: collapse; width: 100%; font-size: 0.85rem; }
th, td { border: 1px solid #ddd; padding: 6px 10px; text-align: left; }
td { vertical-align: top; }
th { background: #f4f4f4; }
h2.only-a + table td { background: #fdecea; }
h2.only-b + table td { background: #eaf3fd; }
h2.differs + table td { background: #fff7e0; }
.val-a { color: #b3261e; text-decoration: line-through; }
.val-b { color: #1e6b3a; font-weight: 600; }
.summary span { display: inline-block; margin-right: 1.5rem; }
.warning { color: #9a5b00; }
.empty { color: #777; font-style: italic; }
"""


def render_html(diff: Diff, label_a: str, label_b: str) -> str:
    warnings = ""
    if diff.duplicate_identities_a:
        warnings += (
            f"<p class='warning'>WARNING: {len(diff.duplicate_identities_a)} "
            f"duplicate identities in {_esc(label_a)} (last write kept)</p>"
        )
    if diff.duplicate_identities_b:
        warnings += (
            f"<p class='warning'>WARNING: {len(diff.duplicate_identities_b)} "
            f"duplicate identities in {_esc(label_b)} (last write kept)</p>"
        )

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>grib-inspect compare: {_esc(label_a)} vs {_esc(label_b)}</title>
<style>{_HTML_STYLE}</style>
</head>
<body>
<h1>Comparing {_esc(label_a)} vs {_esc(label_b)}</h1>
<p class="summary">
<span>identical: {len(diff.identical)}</span>
<span>differs: {len(diff.differs)}</span>
<span>only in {_esc(label_a)}: {len(diff.only_in_a)}</span>
<span>only in {_esc(label_b)}: {len(diff.only_in_b)}</span>
</p>
{warnings}
<h2 class="differs">Differs ({len(diff.differs)})</h2>
{_differs_table(diff.differs)}
<h2 class="only-a">Only in {_esc(label_a)} ({len(diff.only_in_a)})</h2>
{_identity_only_table(diff.only_in_a)}
<h2 class="only-b">Only in {_esc(label_b)} ({len(diff.only_in_b)})</h2>
{_identity_only_table(diff.only_in_b)}
</body>
</html>
"""
