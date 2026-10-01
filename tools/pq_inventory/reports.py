"""Report writers: JSON, Markdown, self-contained HTML, CycloneDX CBOM."""

from __future__ import annotations

import html
import json
import uuid
from collections import defaultdict
from pathlib import Path

from . import __version__
from .algorithms import CLASSICALLY_BROKEN, OK, QUANTUM_BROKEN, QUANTUM_WEAKENED, RISK_ORDER

RISK_TEXT = {
    CLASSICALLY_BROKEN: "Already weak today, without any quantum computer. Fix first.",
    QUANTUM_BROKEN: "Secure today, but a future large quantum computer breaks it (Shor's algorithm). "
                    "Data recorded now can be decrypted later.",
    QUANTUM_WEAKENED: "A quantum computer roughly halves its strength (Grover's algorithm). Upgrade during maintenance.",
    OK: "No known quantum break. No action needed.",
}
RISK_COLOUR = {CLASSICALLY_BROKEN: "#b3261e", QUANTUM_BROKEN: "#c75000", QUANTUM_WEAKENED: "#8a6d00", OK: "#2e7d32"}


def _by_file(findings: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for f in findings:
        groups[f["file"]].append(f)
    return dict(sorted(groups.items(), key=lambda kv: (-max(f["severity"] for f in kv[1]), kv[0])))


def headline(doc: dict) -> str:
    s = doc["summary"]
    broken_files = len({f["file"] for f in doc["findings"] if f["risk"] == QUANTUM_BROKEN})
    weak_files = len({f["file"] for f in doc["findings"] if f["risk"] == CLASSICALLY_BROKEN})
    return (f"{broken_files} of {s['files_scanned']} scanned files use cryptography that a future quantum computer "
            f"would break, and {weak_files} use cryptography that is already weak today.")


def write_json(doc: dict, roadmap: dict | None, path: Path) -> None:
    payload = {**doc, "roadmap": roadmap} if roadmap else doc
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


# ------------------------------------------------------------------- Markdown

def write_markdown(doc: dict, roadmap: dict | None, path: Path) -> None:
    s = doc["summary"]
    out = [f"# Cryptography inventory: `{doc['root']}`", "", f"_Generated {doc['generated_at']} by pq_inventory {doc['version']} "
           "(read-only scan; no key material included)._", "", "## Executive summary", "", headline(doc), "",
           "| Risk | Findings | What it means |", "|---|---:|---|"]
    out += [f"| {risk} | {s['by_risk'][risk]} | {RISK_TEXT[risk]} |" for risk in RISK_ORDER]
    out += ["", f"{s['files_scanned']} files scanned, {s['files_with_findings']} with findings, {s['findings']} findings "
            f"({s['heuristic_findings']} heuristic), {s['skipped']} files skipped."]
    if doc["notes"]:
        out += [""] + [f"> Note: {note}" for note in doc["notes"]]
    if roadmap:
        out += ["", "## Migration roadmap (Mosca: at risk if x + y > z)", "", f"_{roadmap['assumptions']['z_source']}_ "
                f"z = {roadmap['assumptions']['z_years']} years.", "",
                "| Priority | System | x | y | z | Slack (years) | Findings | Start by | Actions |", "|---|---|---:|---:|---:|---:|---:|---|---|"]
        for item in roadmap["items"]:
            actions = "; ".join(f"{a['algorithm']} ({a['count']}) → {a['replacement']}" for a in item["actions"]) or "none"
            out.append(f"| {item['tier']}. {item['tier_label']} | {item['system']} | {item['x']:g} | {item['y']:g} | "
                       f"{item['z']:g} | {item['slack_years']:+g} | {item['findings']} | {start_text(item)} | {actions} |")
    out += ["", "## Findings by file", ""]
    for file, findings in _by_file(doc["findings"]).items():
        out += [f"### `{file}`", "", "| Line | Risk | Algorithm | Detail | Recommended replacement |", "|---:|---|---|---|---|"]
        for f in findings:
            flag = " (heuristic)" if f["heuristic"] else ""
            out.append(f"| {f['line'] or '-'} | {f['risk']} | {f['algorithm']}{flag} | {f['detail'].replace('|', '/')} | {f['replacement']} |")
        out.append("")
    if doc["skipped"]:
        out += ["## Skipped files", ""] + [f"- `{s['file']}`: {s['reason']}" for s in doc["skipped"]] + [""]
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


# ----------------------------------------------------------------------- HTML

_CSS = """
:root{--bg:#fbfbfa;--fg:#1d1d1b;--muted:#5d5d58;--card:#fff;--line:#deddd8}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--fg:#ecebe6;--muted:#a8a7a0;--card:#202020;--line:#383836}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1080px;margin:0 auto;padding:24px 16px 64px}h1{font-size:1.6rem;margin:0 0 4px}h2{margin-top:2.2rem;font-size:1.25rem}
.muted{color:var(--muted)}.lead{font-size:1.15rem;margin:18px 0}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-left:6px solid var(--c);border-radius:8px;padding:12px 14px}
.card b{display:block;font-size:1.9rem;line-height:1.1}.card span{font-weight:600}
table{width:100%;border-collapse:collapse;background:var(--card);font-size:.92rem}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
.wrap{overflow-x:auto}.pill{display:inline-block;padding:1px 8px;border-radius:999px;color:#fff;font-size:.78rem;font-weight:600;white-space:nowrap}
details{background:var(--card);border:1px solid var(--line);border-radius:8px;margin:8px 0;padding:6px 10px}summary{cursor:pointer;font-weight:600}
code{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.88em}.heur{font-size:.75rem;color:var(--muted)}
"""


def start_text(item: dict) -> str:
    if item["start_migration_by"] is None:
        return "-"
    if item["overdue_years"] > 0:
        years = item["overdue_years"]
        return f"now (overdue by {years:g} year{'' if years == 1 else 's'})"
    return str(item["start_migration_by"])


def _pill(risk: str) -> str:
    return f'<span class="pill" style="background:{RISK_COLOUR[risk]}">{html.escape(risk)}</span>'


def write_html(doc: dict, roadmap: dict | None, path: Path) -> None:
    e = html.escape
    s = doc["summary"]
    parts = [f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
             f"<title>Cryptography inventory</title><style>{_CSS}</style></head><body><main>",
             f"<h1>Cryptography inventory</h1><div class=\"muted\">Scanned <code>{e(doc['root'])}</code> on {e(doc['generated_at'])} "
             f"with pq_inventory {e(doc['version'])}. Read-only scan; no key material is included in this report.</div>",
             "<h2>Executive summary</h2>", f"<p class=\"lead\">{e(headline(doc))}</p>", "<div class=\"cards\">"]
    for risk in RISK_ORDER:
        parts.append(f"<div class=\"card\" style=\"--c:{RISK_COLOUR[risk]}\"><b>{s['by_risk'][risk]}</b><span>{e(risk)}</span>"
                     f"<div class=\"muted\">{e(RISK_TEXT[risk])}</div></div>")
    parts.append("</div>")
    parts.append(f"<p class=\"muted\">{s['files_scanned']} files scanned, {s['files_with_findings']} with findings, {s['findings']} findings "
                 f"({s['heuristic_findings']} heuristic: pattern matches in configuration that need a human check), "
                 f"{s['skipped']} files skipped.</p>")
    for note in doc["notes"]:
        parts.append(f"<p class=\"muted\"><b>Note:</b> {e(note)}</p>")
    if roadmap:
        a = roadmap["assumptions"]
        parts += ["<h2>What to do first: migration roadmap</h2>",
                  "<p>A system is at risk when <b>x + y &gt; z</b>: x = years its data must stay secret, y = years to migrate it, "
                  "z = years until a quantum computer can break today's public-key cryptography (Mosca, 2018).</p>",
                  f"<p class=\"muted\">{e(a['z_source'])} Here z = {a['z_years']} years.</p>",
                  "<div class=\"wrap\"><table><tr><th>Priority</th><th>System</th><th>x</th><th>y</th><th>z</th><th>Slack</th>"
                  "<th>Start migrating by</th><th>Actions</th></tr>"]
        for item in roadmap["items"]:
            actions = "<br>".join(f"{_pill(act['risk'])} {e(act['algorithm'])} ({act['count']}) → {e(act['replacement'])}"
                                  for act in item["actions"]) or "none"
            x_note = "" if item["x_from"] == "config" else " <span class=heur>(assumed)</span>"
            y_note = "" if item["y_from"] == "config" else " <span class=heur>(assumed)</span>"
            parts.append(f"<tr><td><b>{item['tier']}</b>. {e(item['tier_label'])}</td><td>{e(item['system'])}</td>"
                         f"<td>{item['x']:g}{x_note}</td><td>{item['y']:g}{y_note}</td><td>{item['z']:g}</td>"
                         f"<td>{item['slack_years']:+g}</td><td>{e(start_text(item))}</td><td>{actions}</td></tr>")
        parts.append("</table></div>")
    parts.append("<h2>Findings by file</h2>")
    for file, findings in _by_file(doc["findings"]).items():
        worst = max(findings, key=lambda f: f["severity"])["risk"]
        parts.append(f"<details{' open' if worst != OK else ''}><summary>{_pill(worst)} <code>{e(file)}</code> "
                     f"({len(findings)} finding{'s' if len(findings) != 1 else ''})</summary><div class=\"wrap\"><table>"
                     "<tr><th>Line</th><th>Risk</th><th>Algorithm</th><th>Why</th><th>Recommended replacement</th></tr>")
        for f in findings:
            heur = " <span class=heur>heuristic</span>" if f["heuristic"] else ""
            parts.append(f"<tr><td>{f['line'] or '-'}</td><td>{_pill(f['risk'])}</td><td>{e(f['algorithm'])}{heur}"
                         f"<div class=muted>{e(f['detail'])}</div></td><td>{e(f['why'])}</td><td>{e(f['replacement'])}</td></tr>")
        parts.append("</table></div></details>")
    if doc["skipped"]:
        parts.append("<h2>Skipped files</h2><ul>" + "".join(f"<li><code>{e(x['file'])}</code>: {e(x['reason'])}</li>" for x in doc["skipped"]) + "</ul>")
    parts.append("<h2>Glossary</h2><ul><li><b>Shor's algorithm</b>: a quantum algorithm that breaks RSA, Diffie-Hellman and elliptic curves.</li>"
                 "<li><b>Grover's algorithm</b>: a quantum search that roughly halves the strength of symmetric keys (AES-128 becomes about 64-bit).</li>"
                 "<li><b>ML-KEM / ML-DSA / SLH-DSA</b>: NIST's post-quantum standards FIPS 203, 204 and 205 (August 2024).</li>"
                 "<li><b>Heuristic</b>: matched by a configuration pattern, not by parsing; confirm by hand.</li></ul>")
    parts.append("</main></body></html>")
    path.write_text("\n".join(parts), encoding="utf-8")


# ---------------------------------------------------------------- CycloneDX

PRIMITIVE = {"RSA": "pke", "RSA-KEX": "pke", "RSA-SIGNATURE": "signature", "DSA": "signature", "ECDSA": "signature",
             "EdDSA": "signature", "ML-DSA": "signature", "SLH-DSA": "signature", "DH": "key-agree", "ECDH": "key-agree",
             "EC": "key-agree", "X25519": "key-agree", "ML-KEM": "kem", "HYBRID-PQ": "kem", "AES": "block-cipher",
             "AES-128": "block-cipher", "AES-192": "block-cipher", "AES-256": "block-cipher", "DES": "block-cipher",
             "3DES": "block-cipher", "RC2": "block-cipher", "CAMELLIA-128": "block-cipher", "CAMELLIA-256": "block-cipher",
             "RC4": "stream-cipher", "CHACHA20": "ae", "MD5": "hash", "SHA-1": "hash", "SHA-224": "hash", "SHA-256": "hash",
             "SHA-384": "hash", "SHA-512": "hash", "SHA-3": "hash", "HMAC-SHA1": "mac", "HMAC-MD5": "mac"}
NIST_QUANTUM_LEVEL = {"AES-128": 1, "AES-192": 3, "AES-256": 5, "SHA-256": 2, "SHA-384": 4, "SHA-512": 5}


def cbom(doc: dict) -> dict:
    components: dict[str, dict] = {}
    for f in doc["findings"]:
        if f["algorithm"].startswith(("TLS", "SSL")):
            ref = f"crypto/protocol/{f['algorithm']}"
            body = {"assetType": "protocol", "protocolProperties": {"type": "tls" if f["algorithm"].startswith("TLS") else "ssl",
                                                                      "version": f["algorithm"].replace("TLS", "").replace("SSLv", "")}}
        elif f["category"] in ("private-key", "public-key", "ssh-key"):
            kind = "private-key" if f["category"] == "private-key" else "public-key"
            ref = f"crypto/key/{kind}/{f['algorithm']}-{f['key_size'] or 'unknown'}/{f['fingerprint']}"
            body = {"assetType": "related-crypto-material", "relatedCryptoMaterialProperties":
                    {"type": kind, "size": f["key_size"], "algorithmRef": f"crypto/algorithm/{f['algorithm']}"}}
        elif f["category"] == "certificate" and f["rule"].endswith("certificate"):
            ref = f"crypto/certificate/{f['fingerprint']}"
            body = {"assetType": "certificate", "certificateProperties": {"subjectName": f["detail"].split(";")[0].removeprefix("certificate "),
                                                                            "signatureAlgorithmRef": f"crypto/algorithm/{f['algorithm']}"}}
        else:
            name = f["algorithm"] + (f"-{f['key_size']}" if f["key_size"] else "")
            ref = f"crypto/algorithm/{name}"
            props = {"primitive": PRIMITIVE.get(f["algorithm"], "unknown")}
            if f["key_size"]:
                props["parameterSetIdentifier"] = str(f["key_size"])
            if f["risk"] == QUANTUM_BROKEN:
                props["nistQuantumSecurityLevel"] = 0
            elif f["algorithm"] in NIST_QUANTUM_LEVEL:
                props["nistQuantumSecurityLevel"] = NIST_QUANTUM_LEVEL[f["algorithm"]]
            body = {"assetType": "algorithm", "algorithmProperties": props}
        component = components.setdefault(ref, {
            "type": "cryptographic-asset", "bom-ref": ref, "name": ref.split("/")[2] if ref.count("/") >= 2 else ref,
            "cryptoProperties": body, "evidence": {"occurrences": []},
            "properties": [{"name": "pq_inventory:risk", "value": f["risk"]},
                           {"name": "pq_inventory:replacement", "value": f["replacement"]}],
        })
        occurrence = {"location": f["file"]}
        if f["line"]:
            occurrence["line"] = f["line"]
        component["evidence"]["occurrences"].append(occurrence)
    seed = "|".join(sorted(f["fingerprint"] for f in doc["findings"]))
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, 'pq_inventory:' + doc['root'] + ':' + seed)}",
        "version": 1,
        "metadata": {"timestamp": doc["generated_at"],
                     "tools": {"components": [{"type": "application", "name": "pq_inventory", "version": __version__}]},
                     "component": {"type": "application", "name": Path(doc["root"]).name or doc["root"], "bom-ref": "scanned-root"}},
        "components": sorted(components.values(), key=lambda c: c["bom-ref"]),
    }


def write_cbom(doc: dict, path: Path) -> None:
    path.write_text(json.dumps(cbom(doc), indent=2) + "\n", encoding="utf-8")
