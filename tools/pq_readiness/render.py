"""The report as one self-contained, print-ready HTML page (no scripts, no external assets).

Every value from the data is escaped. The print stylesheet sets A4 margins, keeps tables and
sections from splitting badly and drops colour backgrounds, so "Print → Save as PDF" gives a clean PDF.
"""

from __future__ import annotations

import html

from pq_inventory.algorithms import RISK_ORDER
from pq_inventory.reports import start_text

RISK_COLOUR = {"CLASSICALLY-BROKEN": "#b3261e", "QUANTUM-BROKEN": "#b35400", "QUANTUM-WEAKENED": "#7a6000", "OK": "#2e7d32"}
KX_COLOUR = {"PQ-HYBRID": "#2e7d32", "CLASSICAL": "#b35400", "UNKNOWN": "#5d5d58"}

CSS = """
:root{--ink:#1b1f23;--muted:#59626b;--line:#d9dde1;--soft:#f3f5f7;--accent:#0f5f8a}
*{box-sizing:border-box}
html{background:#fff}
body{margin:0;color:var(--ink);font:15px/1.55 Georgia,"Times New Roman",serif;background:#fff}
main{max-width:860px;margin:0 auto;padding:32px 20px 64px}
h1,h2,h3,.label,table,.pill,.meta{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
h1{font-size:1.9rem;line-height:1.2;margin:.2em 0 .1em}
h2{font-size:1.25rem;margin:2.2em 0 .6em;padding-bottom:.25em;border-bottom:2px solid var(--ink)}
h3{font-size:1.02rem;margin:1.4em 0 .4em}
.meta{color:var(--muted);font-size:.9rem}
.cover{border-bottom:1px solid var(--line);padding-bottom:18px}
.summary li{margin:.35em 0}
table{width:100%;border-collapse:collapse;font-size:.86rem;margin:.6em 0 1em}
th,td{border:1px solid var(--line);padding:5px 7px;text-align:left;vertical-align:top;overflow-wrap:anywhere}
th{background:var(--soft)}
.num{text-align:right;white-space:nowrap}
.pill{display:inline-block;padding:0 7px;border-radius:9px;color:#fff;font-size:.74rem;font-weight:600;white-space:nowrap}
.note{background:var(--soft);border-left:4px solid var(--accent);padding:10px 14px;margin:1em 0;font-size:.92rem}
.actions h3{margin-top:1.1em}
.actions li{margin:.45em 0}
.small{font-size:.85rem;color:var(--muted)}
svg text{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
@page{size:A4;margin:16mm 14mm}
@media print{
  main{max-width:none;padding:0}
  body{font-size:10.5pt}
  h2{break-after:avoid}
  h3{break-after:avoid}
  tr,li,.note,svg{break-inside:avoid}
  section{break-inside:auto}
  #findings,#method{break-before:page}
  .pill{color:#000!important;background:none!important;border:1px solid #000}
  th{background:none}
  a{color:inherit;text-decoration:none}
}
"""


def _e(value) -> str:
    return html.escape(str(value), quote=True)


def _pill(text: str, colour: str) -> str:
    return f'<span class="pill" style="background:{colour}">{_e(text)}</span>'


def _timeline(items: list[dict], reference_year: int, z: float) -> str:
    """Bars of x + y years per system against the line at z (Mosca)."""
    if not items:
        return ""
    horizon = max([z] + [i["x"] + i["y"] for i in items]) + 1
    left, width, row = 230, 600, 26
    height = 40 + row * len(items)
    scale = (width - left - 20) / horizon
    parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" aria-label="Mosca timeline: x + y per system against z = {z:g} years">']
    for year in range(0, int(horizon) + 1, max(1, int(horizon // 8) or 1)):
        x = left + year * scale
        parts.append(f'<line x1="{x:.1f}" y1="20" x2="{x:.1f}" y2="{height - 14}" stroke="#d9dde1"/>'
                     f'<text x="{x:.1f}" y="{height - 2}" font-size="10" text-anchor="middle" fill="#59626b">{reference_year + year}</text>')
    for index, item in enumerate(items):
        y = 24 + index * row
        total = item["x"] + item["y"]
        late = total > z
        parts.append(f'<text x="{left - 8}" y="{y + 13}" font-size="11" text-anchor="end" fill="#1b1f23">{_e(item["system"][:34])}</text>')
        parts.append(f'<rect x="{left}" y="{y + 2}" width="{item["x"] * scale:.1f}" height="9" fill="{"#b35400" if late else "#0f5f8a"}"/>')
        parts.append(f'<rect x="{left + item["x"] * scale:.1f}" y="{y + 2}" width="{item["y"] * scale:.1f}" height="9" fill="{"#e0a37a" if late else "#8fb9d1"}"/>')
        parts.append(f'<text x="{left + total * scale + 5:.1f}" y="{y + 11}" font-size="10" fill="#59626b">{total:g} y{" · late" if late else ""}</text>')
    zx = left + z * scale
    parts.append(f'<line x1="{zx:.1f}" y1="14" x2="{zx:.1f}" y2="{height - 14}" stroke="#b3261e" stroke-width="2" stroke-dasharray="4 3"/>'
                 f'<text x="{zx + 4:.1f}" y="12" font-size="10" fill="#b3261e">z = {z:g} years ({reference_year + z:g}, assumed)</text>')
    parts.append("</svg>")
    return "".join(parts)


def render(report: dict) -> str:
    code, websites, actions = report["code"], report["websites"], report["actions"]
    out = [f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
           f"<title>Quantum Readiness Report · {_e(report['client'])}</title><style>{CSS}</style></head><body><main>"]
    out.append(f'<section class="cover" id="cover"><div class="meta">Quantum Readiness Report</div><h1>{_e(report["client"])}</h1>'
               f'<div class="meta">Date: {_e(report["date"])} · Tools: '
               + ", ".join(f"{_e(name)} {_e(version)}" for name, version in report["versions"].items()) + "</div></section>")

    out.append('<section id="summary"><h2>1. Executive summary</h2><ul class="summary">'
               + "".join(f"<li>{_e(line)}</li>" for line in report["executive_summary"]) + "</ul>"
               '<div class="note">How to read this report: cryptography that is <b>weak today</b> needs fixing whatever happens with '
               'quantum computing. Cryptography that a <b>future quantum computer</b> breaks (RSA, elliptic curves, Diffie-Hellman) '
               'matters now for data that must stay secret for years, because traffic can be recorded today and decrypted later.</div></section>')

    out.append('<section id="websites"><h2>2. Websites: key exchange</h2>')
    if websites["rows"]:
        out.append(f'<p class="small">Source: {_e(websites["source"])}. ML-KEM implementation used for the check: '
                   f'{_e(websites["ml_kem"] or "none (post-quantum check skipped)")}.</p>')
        if websites.get("note"):
            out.append(f'<div class="note">{_e(websites["note"])}</div>')
        out.append("<table><tr><th>Website</th><th>Key exchange</th><th>TLS</th><th>Certificate key</th><th>Recommendation</th></tr>")
        for site in websites["rows"]:
            out.append(f"<tr><td>{_e(site['host'])}</td><td>{_pill(site['key_exchange'], KX_COLOUR[site['key_exchange']])}"
                       f"<div class=small>{_e(site['key_exchange_detail'])}</div></td><td>{_e(site['tls_version'])}</td>"
                       f"<td>{_e(site['certificate_key'])}</td><td>{_e(site['recommendation'])}</td></tr>")
        out.append("</table><p class=small>PQ-HYBRID: the server chose X25519MLKEM768 (ML-KEM-768 + X25519, RFC 10024). "
                   "CLASSICAL: it chose a classical group although the hybrid group was offered first. Every certificate key "
                   "listed is quantum-vulnerable, as on every website today: post-quantum web certificates are not available yet.</p>")
    else:
        out.append("<p>No websites were checked for this report.</p>")
    out.append("</section>")

    out.append('<section id="findings"><h2>3. Code and configuration findings</h2>')
    if code:
        s = code["summary"]
        out.append(f'<p>Scanned <code>{_e(code["root"])}</code>: {s["files_scanned"]} files, {s["files_with_findings"]} with findings, '
                   f'{s["findings"]} findings ({s["heuristic_findings"]} heuristic, to confirm by hand), {code["skipped"]} files skipped.</p>')
        out.append("<table><tr><th>Risk</th><th class=num>Findings</th><th>What it means</th></tr>")
        for risk in RISK_ORDER:
            out.append(f"<tr><td>{_pill(risk, RISK_COLOUR[risk])}</td><td class=num>{s['by_risk'][risk]}</td><td>{_e(code['risk_text'][risk])}</td></tr>")
        out.append("</table>")
        for risk in RISK_ORDER:
            findings = code["findings_by_risk"][risk]
            if not findings or risk == "OK":
                continue
            out.append(f"<h3>{_e(risk)} ({len(findings)})</h3><table><tr><th>Where</th><th>Algorithm</th><th>Detail</th><th>Replace with</th></tr>")
            for f in findings:
                flag = " <span class=small>(heuristic)</span>" if f["heuristic"] else ""
                out.append(f"<tr><td>{_e(f['file'])}{':' + str(f['line']) if f['line'] else ''}</td><td>{_e(f['algorithm'])}{flag}</td>"
                           f"<td>{_e(f['detail'])}</td><td>{_e(f['replacement'])}</td></tr>")
            out.append("</table>")
        ok = len(code["findings_by_risk"]["OK"])
        if ok:
            out.append(f"<p class=small>{ok} findings are already fine (OK) and are not listed.</p>")
        for note in code["notes"]:
            out.append(f'<p class="small">Note: {_e(note)}</p>')
    else:
        out.append("<p>No code or configuration was scanned for this report.</p>")
    out.append("</section>")

    out.append('<section id="timeline"><h2>4. Migration timeline (Mosca)</h2>')
    if code:
        plan, a = code["roadmap"], code["roadmap"]["assumptions"]
        out.append("<p>Mosca's inequality: a system is at risk when <b>x + y &gt; z</b>, where x is how long its data must stay "
                   "secret, y how long its migration takes, and z the years until a quantum computer can break today's "
                   "public-key cryptography (M. Mosca, IEEE Security &amp; Privacy 16(5), 2018).</p>")
        out.append(_timeline(plan["items"], int(a["reference_year"]), float(a["z_years"])))
        out.append("<table><tr><th>System</th><th class=num>x</th><th class=num>y</th><th class=num>z</th><th class=num>Slack</th><th>Start by</th><th>Priority</th></tr>")
        for item in plan["items"]:
            x_mark = "" if item["x_from"] == "config" else " (assumed)"
            y_mark = "" if item["y_from"] == "config" else " (assumed)"
            out.append(f"<tr><td>{_e(item['system'])}</td><td class=num>{item['x']:g}{x_mark}</td><td class=num>{item['y']:g}{y_mark}</td>"
                       f"<td class=num>{item['z']:g}</td><td class=num>{item['slack_years']:+g}</td><td>{_e(start_text(item))}</td>"
                       f"<td>{item['tier']}. {_e(item['tier_label'])}</td></tr>")
        out.append("</table>")
        out.append('<div class="note"><b>Assumptions (replace them with your own).</b><br>'
                   f'{_e(a["z_source"])}<br>{_e(a["x_source"])}<br>{_e(a["y_source"])}<br>Reference year: {a["reference_year"]}.</div>')
        if plan["unassigned_findings"]:
            out.append(f'<p class="small">{plan["unassigned_findings"]} risky findings belong to no configured system.</p>')
    else:
        out.append("<p>No systems were assessed (no code was scanned).</p>")
    out.append("</section>")

    out.append('<section id="actions" class="actions"><h2>5. Prioritised actions</h2>')
    for key, title in (("now", "Now"), ("next", "Next (12–24 months)"), ("later", "Later (as the ecosystem allows)")):
        out.append(f"<h3>{title}</h3>")
        if actions[key]:
            out.append("<ol>" + "".join(f"<li><b>{_e(a['what'])}</b>. {_e(a['detail'])} <span class=small>Why: {_e(a['why'])}</span></li>"
                                        for a in actions[key]) + "</ol>")
        else:
            out.append("<p class=small>Nothing in this category.</p>")
    out.append("</section>")

    out.append('<section id="method"><h2>6. Methodology and honest limits</h2><ul>'
               "<li><b>Code and configuration</b> were scanned by pq_inventory, read-only and offline: regular-expression rules for "
               "source code, parsers for keys, certificates and TLS/SSH configuration. Only metadata is reported: no key material and "
               "no source text appear in this report. Rules see one line at a time, so multi-line calls and hand-written cryptography "
               "can be missed; heuristic findings need a human check. The scanner's accuracy is measured only on a corpus written "
               "together with its rules.</li>"
               "<li><b>Websites</b> were checked by pq_tls: one TLS 1.3 ClientHello offering the hybrid group X25519MLKEM768 and one "
               "normal TLS connection per site, the same traffic a browser makes. Results are a snapshot from one place and time; "
               "CDNs can answer differently by region.</li>"
               "<li><b>Mosca timeline:</b> x, y and z are assumptions, labelled as such. z is a planning horizon taken from a "
               "regulatory draft, not a forecast of when a quantum computer will exist. Nobody knows that date.</li>"
               "<li><b>Classification:</b> CLASSICALLY-BROKEN &gt; QUANTUM-BROKEN &gt; QUANTUM-WEAKENED &gt; OK, with NIST "
               "replacements (FIPS 203 ML-KEM, FIPS 204 ML-DSA, FIPS 205 SLH-DSA, AES-256, SHA-2). Some choices are debatable "
               "(for example every SHA-1 use counts as weak today).</li>"
               "<li>No quantum advantage is claimed anywhere: this report is about planning a cryptographic migration.</li></ul>"
               f'<p class="small" id="versions">Generated {_e(report["date"])} by '
               + ", ".join(f"{_e(name)} {_e(version)}" for name, version in report["versions"].items())
               + ". Same inputs and date give the same report.</p></section>")
    out.append("</main></body></html>")
    return "\n".join(out) + "\n"
