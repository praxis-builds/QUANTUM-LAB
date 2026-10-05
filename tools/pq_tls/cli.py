"""python -m pq_tls check <host> [<host> ...] [--port 443] [--json out.json]

Exit codes: 0 = every host was checked (whatever the verdicts); 2 = usage error (bad host, too many
hosts, bad port). Hosts come only from the command line, one name or address each: no ranges, no
wildcards, no lists from files, at most 20 per run.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .probe import TIMEOUT, run

MAX_HOSTS = 20
HOSTNAME = re.compile(r"^(?=.{1,253}\.?$)(?:(?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)*(?!-)[A-Za-z0-9-]{1,63}(?<!-)\.?$")


def validate_host(text: str) -> str:
    """One DNS name or one IP address. Anything that could name several machines is refused."""
    host = text.strip()
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        pass
    if "/" in host or "*" in host or "," in host or ":" in host:
        raise argparse.ArgumentTypeError(f"{text!r}: give one host name or one IP address (no ranges, wildcards, ports or URLs)")
    # The last label must contain a letter (RFC 3696 2: top-level domains are not all-numeric), which
    # also rejects address look-alikes such as 1.2.3.4-9 or 999.1.1.1.
    if not HOSTNAME.match(host) or not re.search(r"[A-Za-z]", host.rstrip(".").rsplit(".", 1)[-1]):
        raise argparse.ArgumentTypeError(f"{text!r} is not a host name or a single IP address")
    return host.lower()


def _port(text: str) -> int:
    value = int(text)
    if not 1 <= value <= 65535:
        raise argparse.ArgumentTypeError("port must be 1-65535")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pq_tls", description="Does a website use post-quantum (hybrid) TLS key exchange?")
    parser.add_argument("--version", action="version", version=f"pq_tls {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help=f"check 1 to {MAX_HOSTS} hosts")
    check.add_argument("hosts", nargs="+", type=validate_host, metavar="host")
    check.add_argument("--port", type=_port, default=443)
    check.add_argument("--json", type=Path, help="also write the full results as JSON")
    return parser


def format_table(results: dict) -> str:
    lines = [f"pq_tls {results['version']} · {results['checked_at']} · ML-KEM: {results['ml_kem'] or 'none (PQ check skipped)'}", ""]
    for entry in results["hosts"]:
        v = entry["verdict"]
        lines += [f"{entry['host']}:{entry['port']}",
                  f"  key exchange : {v['key_exchange']} - {v['key_exchange_detail']}",
                  f"  TLS version  : {v['tls_version'] or 'unknown'}",
                  f"  certificate  : {v['certificate']}",
                  f"  recommended  : {v['recommendation']}", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None, *, timeout: float = TIMEOUT, now: str | None = None) -> int:
    args = _parser().parse_args(argv)
    hosts = list(dict.fromkeys(args.hosts))
    if len(hosts) > MAX_HOSTS:
        print(f"error: at most {MAX_HOSTS} hosts per run (got {len(hosts)})", file=sys.stderr)
        return 2
    checked_at = now or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    results = run(hosts, args.port, timeout=timeout, checked_at=checked_at)
    print(format_table(results))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        print(f"JSON written to {args.json}")
    return 0
