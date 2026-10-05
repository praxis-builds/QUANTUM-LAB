"""The report's data: one JSON-ready dict built from a pq_inventory scan, a Mosca roadmap and pq_tls results.

Nothing from the scanned files is copied except metadata the scanner already reports (file, line,
algorithm, risk, a description). Evidence fields are dropped entirely: the scanner stores them only
as "[redacted]" (DECISIONS D18), and the report does not even carry the marker.
"""

from __future__ import annotations

import json
from pathlib import Path

import pq_inventory
import pq_tls
from pq_inventory import roadmap as mosca
from pq_inventory.algorithms import CLASSICALLY_BROKEN, OK, QUANTUM_BROKEN, QUANTUM_WEAKENED, RISK_ORDER
from pq_inventory.reports import RISK_TEXT, start_text
from pq_inventory.scanner import scan, to_document

from . import __version__

FINDING_FIELDS = ("file", "line", "category", "algorithm", "risk", "why", "replacement", "heuristic", "detail")
KEY_EXCHANGES = ("PQ-HYBRID", "CLASSICAL", "UNKNOWN")


class InputError(ValueError):
    """Bad input (exit code 2)."""


def load_site_results(path: Path) -> dict:
    """A pq_tls results file (python -m pq_tls check ... --json), validated before use."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise InputError(f"{path} is not a readable pq_tls results file ({error})") from error
    if not isinstance(data, dict) or data.get("tool") != "pq_tls":
        raise InputError(f"{path} is not a pq_tls results file")
    hosts = data.get("hosts")
    if not isinstance(hosts, list) or not all(
            isinstance(h, dict) and isinstance(h.get("host"), str) and isinstance(h.get("verdict"), dict)
            and h["verdict"].get("key_exchange") in KEY_EXCHANGES for h in hosts):
        raise InputError(f"{path}: 'hosts' must be pq_tls host results")
    return data


def _website_rows(results: dict) -> list[dict]:
    rows = []
    for entry in results["hosts"]:
        verdict, connection = entry["verdict"], entry.get("connection") or {}
        rows.append({"host": entry["host"], "port": entry.get("port", 443), "key_exchange": verdict["key_exchange"],
                     "key_exchange_detail": verdict.get("key_exchange_detail", ""),
                     "tls_version": verdict.get("tls_version") or "unknown",
                     "certificate_key": connection.get("certificate_key") or "not read",
                     "recommendation": verdict.get("recommendation", "")})
    return rows


def _finding(f: dict) -> dict:
    return {key: f[key] for key in FINDING_FIELDS}


def _actions(code: dict | None, websites: list[dict]) -> dict[str, list[dict]]:
    """Prioritised actions: now (weak today, or late under Mosca), next (quantum exposure with time
    left, websites without hybrid key exchange), later (certificates, Grover-only items)."""
    now, next_, later = [], [], []
    if code:
        for item in code["roadmap"]["items"]:
            fixes = "; ".join(f"{a['algorithm']} ({a['count']}) → {a['replacement']}" for a in item["actions"])
            if item["tier"] == 1:
                weak = "; ".join(f"{a['algorithm']} ({a['count']}) → {a['replacement']}" for a in item["actions"]
                                 if a["risk"] == CLASSICALLY_BROKEN)
                now.append({"what": f"{item['system']}: replace cryptography that is weak today", "detail": weak,
                            "why": "Broken or deprecated without any quantum computer."})
            if item["counts"][QUANTUM_BROKEN] and item["mosca_at_risk"]:
                now.append({"what": f"{item['system']}: start the post-quantum migration now ({start_text(item)})",
                            "detail": fixes, "why": f"x + y = {item['x'] + item['y']:g} years > z = {item['z']:g}: data protected "
                                                    "today must stay secret beyond the assumed horizon."})
            elif item["counts"][QUANTUM_BROKEN]:
                next_.append({"what": f"{item['system']}: plan the post-quantum migration, start by {start_text(item)}",
                              "detail": fixes, "why": f"Quantum-vulnerable, with {item['slack_years']:+g} years of slack under the assumed z."})
            elif item["tier"] == 4:
                later.append({"what": f"{item['system']}: upgrade 128-bit symmetric keys in routine maintenance",
                              "detail": fixes, "why": "Grover's algorithm roughly halves symmetric key strength; no break."})
    for site in websites:
        if site["tls_version"] not in ("TLSv1.3", "TLS 1.3", "unknown"):
            now.append({"what": f"{site['host']}: enable TLS 1.3", "detail": f"{site['tls_version']} negotiated",
                        "why": "Hybrid post-quantum key exchange needs TLS 1.3."})
        elif site["key_exchange"] == "CLASSICAL":
            next_.append({"what": f"{site['host']}: enable hybrid key exchange X25519MLKEM768",
                          "detail": "On the TLS endpoint or CDN (RFC 10024).",
                          "why": "Traffic recorded today could be decrypted later (harvest now, decrypt later)."})
        elif site["key_exchange"] == "UNKNOWN":
            next_.append({"what": f"{site['host']}: re-check the key exchange", "detail": site["key_exchange_detail"],
                          "why": "The check did not give an answer."})
    if websites or code:
        later.append({"what": "Certificates and signature keys: move to ML-DSA (FIPS 204) or composite certificates when possible",
                      "detail": "Public CAs and browsers do not support post-quantum web certificates yet; track it.",
                      "why": "Signatures only need to resist forgery while in use, so they can follow the key exchange."})
    return {"now": now, "next": next_, "later": later}


def _summary(code: dict | None, websites: list[dict], actions: dict, sites_source: str | None, sites_note: str | None) -> list[str]:
    lines = []
    if websites:
        hybrid = sum(s["key_exchange"] == "PQ-HYBRID" for s in websites)
        classical = sum(s["key_exchange"] == "CLASSICAL" for s in websites)
        unknown = len(websites) - hybrid - classical
        lines.append(f"Websites: {hybrid} of {len(websites)} already protect their traffic with hybrid post-quantum key exchange; "
                     f"{classical} still {'uses' if classical == 1 else 'use'} classical key exchange only"
                     + (f", and {unknown} could not be checked" if unknown else "") + f" ({sites_source})."
                     + (f" {sites_note}" if sites_note else ""))
    if code:
        s = code["summary"]
        by = s["by_risk"]
        lines.append(f"Code and configuration: {s['findings']} uses of cryptography in {s['files_with_findings']} of "
                     f"{s['files_scanned']} files. {by[CLASSICALLY_BROKEN]} are weak today, {by[QUANTUM_BROKEN]} would be broken by "
                     f"a large quantum computer, {by[QUANTUM_WEAKENED]} are only weakened, {by[OK]} are fine.")
        late = [i for i in code["roadmap"]["items"] if i["mosca_at_risk"] and i["counts"][QUANTUM_BROKEN]]
        z = code["roadmap"]["assumptions"]["z_years"]
        if late:
            names = ", ".join(i["system"] for i in late)
            lines.append(f"Under the planning assumption z = {z:g} years (an assumption, not a forecast), {len(late)} of "
                         f"{len(code['roadmap']['items'])} systems are already late: {names}.")
        else:
            lines.append(f"Under the planning assumption z = {z:g} years (an assumption, not a forecast), no system is late yet.")
    if actions["now"]:
        lines.append(f"Do now: {actions['now'][0]['what']}" + (f", and {len(actions['now']) - 1} more" if len(actions["now"]) > 1 else "") + ".")
    lines.append("Certificates everywhere still use RSA or elliptic curves, like every web certificate today; that "
                 "migration waits for post-quantum certificates to become available.")
    return lines


def build(*, client: str, date: str, code: Path | None = None, systems: Path | None = None,
          site_results: dict | None = None, site_results_label: str | None = None, sites_note: str | None = None) -> dict:
    """The full report as data. `date` (YYYY-MM-DD) is the only clock: the same inputs give the same report."""
    if not client.strip():
        raise InputError("--client must not be empty")
    code_section = None
    if code is not None:
        if not Path(code).exists():
            raise InputError(f"{code} does not exist")
        try:
            config = mosca.load_config(systems)
        except (OSError, ValueError) as error:
            raise InputError(f"systems config: {error}") from error
        document = to_document(scan(Path(code)), generated_at=f"{date}T00:00:00+00:00")
        if document["summary"]["files_scanned"] == 0:
            raise InputError(f"nothing could be read under {code}")
        plan = mosca.build(document["findings"], config)
        findings = [_finding(f) for f in document["findings"]]
        code_section = {"root": document["root"], "summary": document["summary"], "notes": document["notes"],
                        "skipped": len(document["skipped"]), "roadmap": plan,
                        "findings_by_risk": {risk: [f for f in findings if f["risk"] == risk] for risk in RISK_ORDER},
                        "risk_text": RISK_TEXT}
    websites = _website_rows(site_results) if site_results else []
    sites_source = None
    if site_results:
        sites_source = site_results_label or f"checked {site_results['checked_at']}"
    actions = _actions(code_section, websites)
    return {
        "tool": "pq_readiness", "version": __version__, "client": client.strip(), "date": date,
        "versions": {"pq_readiness": __version__, "pq_inventory": pq_inventory.__version__, "pq_tls": pq_tls.__version__,
                     **({"pq_tls (website results)": site_results.get("version", "?")} if site_results else {})},
        "executive_summary": _summary(code_section, websites, actions, sites_source, sites_note),
        "websites": {"rows": websites, "source": sites_source, "note": sites_note,
                     "checked_at": site_results.get("checked_at") if site_results else None,
                     "ml_kem": site_results.get("ml_kem") if site_results else None},
        "code": code_section, "actions": actions,
    }
