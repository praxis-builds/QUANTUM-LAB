"""Command line: python -m pq_inventory scan <path> --out <dir> | diff <old.json> <new.json> --out <dir>.

Exit codes: 0 = done, 1 = --fail-on threshold reached (for CI), 2 = usage or input error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, diff, reports, roadmap
from .algorithms import RISK_ORDER, SEVERITY
from .detect_source import load_rules
from .scanner import scan, to_document
from .walker import DEFAULT_MAX_BYTES, DEFAULT_MAX_FILES

# --fail-on X fails on X *or worse*, in the order CLASSICALLY-BROKEN > QUANTUM-BROKEN > QUANTUM-WEAKENED > OK
# (algorithms.SEVERITY). The gate-relevant classes are QUANTUM-BROKEN (the usual CI gate) and
# CLASSICALLY-BROKEN; quantum-weakened is available for strict pipelines.
FAIL_LEVELS = {"none": None, "quantum-weakened": "QUANTUM-WEAKENED", "quantum-broken": "QUANTUM-BROKEN",
               "classically-broken": "CLASSICALLY-BROKEN"}
FORMATS = ("json", "html", "md", "cbom")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pq_inventory", description="Read-only cryptography inventory for post-quantum migration.")
    parser.add_argument("--version", action="version", version=f"pq_inventory {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("scan", help="scan a file or directory")
    s.add_argument("path", type=Path)
    s.add_argument("--out", type=Path, required=True, help="output directory (the only place anything is written)")
    s.add_argument("--rules", type=Path, action="append", default=[], help="extra rule file (JSON); repeatable")
    s.add_argument("--systems", type=Path, help="roadmap config: systems with x/y and the z assumption (JSON)")
    s.add_argument("--formats", default=",".join(FORMATS), help=f"comma-separated subset of {', '.join(FORMATS)}")
    s.add_argument("--fail-on", choices=FAIL_LEVELS, default="none",
                   help="exit 1 if any finding is at this level or worse; order: classically-broken > quantum-broken > quantum-weakened")
    s.add_argument("--max-file-size", type=int, default=DEFAULT_MAX_BYTES)
    s.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    s.add_argument("--timestamp", help="fixed ISO timestamp for reproducible reports")
    d = sub.add_parser("diff", help="compare two scan JSON files")
    d.add_argument("old", type=Path)
    d.add_argument("new", type=Path)
    d.add_argument("--out", type=Path, required=True)
    d.add_argument("--fail-on", choices=FAIL_LEVELS, default="none", help="exit 1 if a NEW finding is at this level or worse")
    return parser


def _threshold_hit(findings: list[dict], level: str) -> bool:
    risk = FAIL_LEVELS[level]
    return risk is not None and any(f["severity"] >= SEVERITY[risk] for f in findings)


def _scan(args) -> int:
    if not args.path.exists():
        print(f"error: {args.path} does not exist", file=sys.stderr)
        return 2
    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    unknown = set(formats) - set(FORMATS)
    if unknown:
        print(f"error: unknown format(s) {sorted(unknown)}", file=sys.stderr)
        return 2
    try:
        rules = load_rules(args.rules)
        config = roadmap.load_config(args.systems)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    result = scan(args.path, rules=rules, max_bytes=args.max_file_size, max_files=args.max_files, exclude=[args.out])
    doc = to_document(result, generated_at=args.timestamp)
    plan = roadmap.build(doc["findings"], config)
    writers = {"json": lambda: reports.write_json(doc, plan, args.out / "scan.json"),
               "html": lambda: reports.write_html(doc, plan, args.out / "report.html"),
               "md": lambda: reports.write_markdown(doc, plan, args.out / "report.md"),
               "cbom": lambda: reports.write_cbom(doc, args.out / "cbom.cdx.json")}
    for fmt in formats:
        writers[fmt]()
    s = doc["summary"]
    print(reports.headline(doc))
    print("  " + ", ".join(f"{risk}: {s['by_risk'][risk]}" for risk in RISK_ORDER) + f"  (files scanned: {s['files_scanned']})")
    print(f"  reports written to {args.out}")
    if _threshold_hit(doc["findings"], args.fail_on):
        print(f"FAIL: findings at or above {FAIL_LEVELS[args.fail_on]}", file=sys.stderr)
        return 1
    return 0


def _diff(args) -> int:
    try:
        old, new = diff.load(args.old), diff.load(args.new)
    except (OSError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    result = diff.compare(old, new)
    (args.out / "diff.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    diff.write_markdown(result, args.out / "diff.md")
    print(f"fixed {len(result['fixed'])}, new {len(result['new_findings'])}, unchanged {len(result['unchanged'])}; "
          f"written to {args.out}")
    if _threshold_hit(result["new_findings"], args.fail_on):
        print(f"FAIL: new findings at or above {FAIL_LEVELS[args.fail_on]}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return _scan(args) if args.command == "scan" else _diff(args)
