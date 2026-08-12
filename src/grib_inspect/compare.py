"""Diff two sets of scanned GRIB records by identity, then by encoding key."""

from __future__ import annotations

import json
from dataclasses import dataclass, field


def _identity_key(identity: dict) -> str:
    return json.dumps(identity, sort_keys=True)


@dataclass
class Diff:
    only_in_a: list[dict] = field(default_factory=list)
    only_in_b: list[dict] = field(default_factory=list)
    # each entry: {"identity": ..., "record_a": ..., "record_b": ..., "changed_keys": {key: (a, b)}}
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
        f"only in {label_a}: {len(diff.only_in_a)}  only in {label_b}: {len(diff.only_in_b)}"
    )

    if diff.duplicate_identities_a:
        lines.append(f"\nWARNING: {len(diff.duplicate_identities_a)} duplicate identities in {label_a} (last write kept)")
    if diff.duplicate_identities_b:
        lines.append(f"WARNING: {len(diff.duplicate_identities_b)} duplicate identities in {label_b} (last write kept)")

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
