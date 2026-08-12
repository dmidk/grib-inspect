"""grib-inspect: scan GRIB2 files into an appendable SQLite report, and compare reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import compare as compare_mod
from . import db
from .scan import scan_file


def _parse_tags(pairs: list[str]) -> dict[str, str]:
    tags = {}
    for pair in pairs:
        if "=" not in pair:
            raise argparse.ArgumentTypeError(f"--tag must be key=value, got {pair!r}")
        key, value = pair.split("=", 1)
        tags[key] = value
    return tags


def cmd_scan(args: argparse.Namespace) -> int:
    identity_keys = args.identity_keys.split(",") if args.identity_keys else None
    metadata_keys = args.keys.split(",") if args.keys else None
    tags = _parse_tags(args.tag)

    count = scan_file(
        Path(args.file),
        Path(args.db),
        model=args.model,
        tags=tags,
        identity_keys=identity_keys,
        metadata_keys=metadata_keys,
    )
    print(f"Scanned {count} messages from {args.file} into {args.db} (model={args.model})")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    conn_a = db.connect(Path(args.db_a))
    conn_b = db.connect(Path(args.db_b))
    try:
        records_a = db.fetch_records(conn_a, model=args.model_a)
        records_b = db.fetch_records(conn_b, model=args.model_b)
    finally:
        conn_a.close()
        conn_b.close()

    label_a = args.model_a or args.db_a
    label_b = args.model_b or args.db_b

    if not records_a:
        print(f"No records found for {label_a} (check --model-a / db path)", file=sys.stderr)
        return 1
    if not records_b:
        print(f"No records found for {label_b} (check --model-b / db path)", file=sys.stderr)
        return 1

    diff = compare_mod.diff_records(records_a, records_b)
    print(compare_mod.render_report(diff, label_a, label_b))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="grib-inspect")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="scan a GRIB2 file and append it to a report db")
    scan_parser.add_argument("file", help="path to the GRIB2 file")
    scan_parser.add_argument("--db", required=True, help="path to the SQLite report to append to")
    scan_parser.add_argument("--model", required=True, help="source label, e.g. cy43h, cy46h, or a post-processing tool name")
    scan_parser.add_argument("--tag", action="append", default=[], help="extra key=value tag, may be repeated")
    scan_parser.add_argument("--identity-keys", help="comma-separated GRIB keys identifying a message across files (default: shortName,typeOfLevel,level,stepRange)")
    scan_parser.add_argument("--keys", help="comma-separated GRIB keys to record as metadata (default: a curated encoding key set)")
    scan_parser.set_defaults(func=cmd_scan)

    compare_parser = subparsers.add_parser("compare", help="compare two reports (or two models within/across reports)")
    compare_parser.add_argument("db_a", help="path to the first report db")
    compare_parser.add_argument("db_b", help="path to the second report db")
    compare_parser.add_argument("--model-a", help="restrict db_a to this model label")
    compare_parser.add_argument("--model-b", help="restrict db_b to this model label")
    compare_parser.set_defaults(func=cmd_compare)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
