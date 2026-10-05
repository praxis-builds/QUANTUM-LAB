"""python -m pq_readiness report --client "Name" [--code <path>] [--sites a.com b.com | --sites-json file]
    [--systems systems.json] --out <dir> [--date YYYY-MM-DD]

Writes <out>/readiness-report.html (self-contained, print-ready) and <out>/readiness-report.json.
Exit codes: 0 = written; 2 = usage or input error. --sites contacts the websites (pq_tls rules:
at most 20 single hosts); --sites-json reuses a recorded pq_tls results file and needs no network.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date as Date
from datetime import datetime, timezone
from pathlib import Path

from pq_tls.cli import MAX_HOSTS, validate_host

from . import __version__
from .build import InputError, build, load_site_results
from .render import render


def _date(text: str) -> str:
    try:
        return Date.fromisoformat(text).isoformat()
    except ValueError as error:
        raise argparse.ArgumentTypeError("--date must be YYYY-MM-DD") from error


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pq_readiness", description="Quantum Readiness Report from code, configuration and websites.")
    parser.add_argument("--version", action="version", version=f"pq_readiness {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    report = sub.add_parser("report", help="write the HTML and JSON report")
    report.add_argument("--client", required=True, help="client or organisation name shown on the report")
    report.add_argument("--code", type=Path, help="directory or file to scan with pq_inventory")
    sites = report.add_mutually_exclusive_group()
    sites.add_argument("--sites", nargs="+", type=validate_host, metavar="host", help=f"check these websites now (at most {MAX_HOSTS})")
    sites.add_argument("--sites-json", type=Path, help="reuse recorded pq_tls results instead of contacting the sites")
    report.add_argument("--sites-note", help="one sentence shown with the website results (e.g. where they come from)")
    report.add_argument("--systems", type=Path, help="roadmap config for the Mosca timeline (see docs/pq-inventory.md)")
    report.add_argument("--out", type=Path, required=True)
    report.add_argument("--date", type=_date, help="report date (YYYY-MM-DD; default today, UTC)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.code is None and not args.sites and args.sites_json is None:
        print("error: give --code, --sites or --sites-json (or several)", file=sys.stderr)
        return 2
    day = args.date or datetime.now(timezone.utc).date().isoformat()
    try:
        site_results, label = None, None
        if args.sites_json is not None:
            site_results = load_site_results(args.sites_json)
            label = f"recorded pq_tls results from {site_results['checked_at'][:10]} ({args.sites_json.name}), not a live check"
        elif args.sites:
            hosts = list(dict.fromkeys(args.sites))
            if len(hosts) > MAX_HOSTS:
                raise InputError(f"at most {MAX_HOSTS} websites per report")
            from pq_tls.probe import run

            site_results = run(hosts, checked_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat())
            label = f"checked live on {site_results['checked_at'][:10]}"
        report = build(client=args.client, date=day, code=args.code, systems=args.systems,
                       site_results=site_results, site_results_label=label, sites_note=args.sites_note)
    except InputError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if args.out.exists() and not args.out.is_dir():
        print(f"error: --out {args.out} exists and is not a directory", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "readiness-report.html").write_text(render(report), encoding="utf-8")
    (args.out / "readiness-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Quantum Readiness Report for {report['client']} written to {args.out}")
    for line in report["executive_summary"]:
        print(f"  - {line}")
    return 0
