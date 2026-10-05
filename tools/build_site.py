"""Build the static GitHub Pages showcase into a folder (default: _site/).

Renders the lesson pages, the case study and the tool guides from this repository's Markdown,
copies the committed scanner and readiness reports, writes a landing page, and publishes the
Circuit Playground and the Mosca calculator at playground/ (they run in the browser:
circuit_sim.js, with the presets exported from Python here). The rest of the dashboard needs Python.

    python tools/build_site.py --out _site

Needs `markdown` (in the `dev` extra) and NumPy (for the preset export); the Pages workflow installs both.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
REPO = os.environ.get("GITHUB_REPOSITORY", "praxis-builds/QUANTUM-LAB")
BLOB = f"https://github.com/{REPO}/blob/main/"
TREE = f"https://github.com/{REPO}"
CODESPACES = f"https://codespaces.new/{REPO}?quickstart=1"

LESSON_RE = re.compile(r"^\d\d_[a-z0-9_]+\.md$")
REPORTS = {
    "reports/before.html": ROOT / "examples/warehouse-demo/reports/before/report.html",
    "reports/after.html": ROOT / "examples/warehouse-demo/reports/after/report.html",
    "reports/readiness.html": ROOT / "examples/readiness-demo/readiness-report.html",
}
DASHBOARD = ROOT / "src/praxis_quantum_lab/dashboard_assets"
SITE_ASSETS = ROOT / "tools/site_assets"
# The live Playground page: these scripts, in this order, all served from playground/ (no external scripts).
PLAYGROUND_FILES = {"circuit_sim.js": DASHBOARD / "circuit_sim.js", "playground_backend.js": SITE_ASSETS / "playground_backend.js",
                    "playground.js": DASHBOARD / "playground.js", "security.js": DASHBOARD / "security.js",
                    "dashboard.css": DASHBOARD / "style.css"}
PLAYGROUND_SCRIPTS = ["circuit_sim.js", "presets.js", "playground_backend.js", "playground.js", "security.js"]
# Server wording in the dashboard markup, and what the browser version says instead.
PLAYGROUND_WORDING = {
    "Exact states come from the project's NumPy code; shots come from local Aer.":
        "Everything runs in your browser: exact states from a JavaScript port of the project's simulator "
        "(it matches the Python code to 1e-12), shots from a seeded random generator (browser sampling, not Aer).",
    "LOCAL AER SHOTS": "BROWSER SAMPLING, NOT AER",
}


def pages() -> dict[Path, str]:
    """Source Markdown file -> output path inside the site."""
    mapping = {
        ROOT / "lessons/README.md": "lessons/index.html",
        ROOT / "docs/case-study.md": "case-study.html",
        ROOT / "docs/pq-inventory.md": "pq-inventory.html",
        ROOT / "docs/pq-tls.md": "pq-tls.html",
        ROOT / "docs/pq-readiness.md": "pq-readiness.html",
    }
    for path in sorted((ROOT / "lessons").glob("*.md")):
        if LESSON_RE.match(path.name):
            mapping[path] = f"lessons/{path.stem}.html"
    return mapping


CSS = """
:root{--bg:#f6f7f9;--panel:#fff;--ink:#16202a;--muted:#55626f;--line:#dde3e8;--accent:#0f7466;--accent-soft:#e3f2ef;--code:#eef1f4;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--bg:#0f1418;--panel:#161d23;--ink:#e6edf2;--muted:#9aa8b4;--line:#2a343d;--accent:#4cc3b0;--accent-soft:#16302c;--code:#1d262d;color-scheme:dark}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--accent)}
.wrap{max-width:920px;margin:0 auto;padding:0 16px}
header.top{border-bottom:1px solid var(--line);background:var(--panel)}
header.top .wrap{display:flex;gap:16px;align-items:center;justify-content:space-between;padding-top:14px;padding-bottom:14px;flex-wrap:wrap}
.brand{font-weight:700;text-decoration:none;color:var(--ink)}
.brand span{color:var(--accent)}
nav a{margin-left:16px;text-decoration:none;font-size:15px}
main{padding:32px 0 64px}
article{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:24px 28px;overflow-wrap:anywhere}
h1{line-height:1.2;font-size:2rem;margin:0 0 .5em}
h2{margin-top:1.8em}
code{background:var(--code);padding:.1em .35em;border-radius:4px;font-size:.92em}
pre{background:var(--code);padding:14px;border-radius:8px;overflow-x:auto}
pre code{background:none;padding:0}
table{border-collapse:collapse;display:block;overflow-x:auto;max-width:100%;font-size:.94em}
th,td{border:1px solid var(--line);padding:6px 10px;text-align:left;vertical-align:top}
th{background:var(--code)}
.hero{padding:40px 0 8px}
.hero p.lead{font-size:1.2rem;color:var(--muted);max-width:720px}
.buttons{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0}
.btn{display:inline-block;padding:10px 18px;border-radius:8px;border:1px solid var(--accent);text-decoration:none;font-weight:600}
.btn.primary{background:var(--accent);color:var(--bg)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;margin:24px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px 20px}
.card h3{margin:0 0 6px;font-size:1.05rem}
.card p{margin:0;color:var(--muted);font-size:.95em}
.note{background:var(--accent-soft);border-radius:10px;padding:14px 18px;margin:24px 0}
footer{color:var(--muted);font-size:.9em;padding:24px 0 48px;border-top:1px solid var(--line)}
.pager{display:flex;justify-content:space-between;gap:12px;margin-top:20px;flex-wrap:wrap}
"""


def layout(title: str, body: str, depth: int) -> str:
    up = "../" * depth
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} · Praxis Quantum Lab</title><link rel="stylesheet" href="{up}style.css"></head>
<body><header class="top"><div class="wrap"><a class="brand" href="{up}index.html">Praxis <span>Quantum Lab</span></a>
<nav><a href="{up}lessons/index.html">Lessons</a><a href="{up}case-study.html">Case study</a><a href="{up}pq-inventory.html">Scanner</a><a href="{TREE}">GitHub</a></nav></div></header>
<main><div class="wrap">{body}</div></main>
<footer><div class="wrap">Simulator-only learning lab. No quantum advantage is claimed; toy keys and ciphers are for teaching only. Source: <a href="{TREE}">{html.escape(REPO)}</a>.</div></footer>
</body></html>
"""


def rewrite_links(rendered: str, source: Path, site_path: str, mapping: dict[Path, str]) -> str:
    """Point links at rendered pages when they exist, otherwise at the file on GitHub."""
    depth = site_path.count("/")
    up = "../" * depth

    def fix(match: re.Match) -> str:
        attr, target = match.group(1), html.unescape(match.group(2))
        if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("#") or not target:
            return match.group(0)
        path_part, _, anchor = target.partition("#")
        resolved = (source.parent / path_part).resolve()
        try:
            relative = resolved.relative_to(ROOT)
        except ValueError:
            return match.group(0)
        if resolved in mapping:
            new = up + mapping[resolved]
        else:
            new = BLOB + relative.as_posix()
        if anchor:
            new += "#" + anchor
        return f'{attr}="{html.escape(new, quote=True)}"'

    return re.sub(r'(href|src)="([^"]*)"', fix, rendered)


def render(source: Path, site_path: str, mapping: dict[Path, str], extra: str = "") -> str:
    text = source.read_text(encoding="utf-8")
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists", "toc"])
    body = rewrite_links(body, source, site_path, mapping)
    title_match = re.search(r"^#\s+(.+)$", text, re.M)
    title = title_match.group(1).strip() if title_match else source.stem
    return layout(title, f"<article>{body}{extra}</article>", site_path.count("/"))


def lesson_pager(index: int, lessons: list[Path], mapping: dict[Path, str]) -> str:
    links = []
    if index > 0:
        prev = lessons[index - 1]
        links.append(f'<a href="{mapping[prev].split("/")[-1]}">← {html.escape(prev.stem[:2])}</a>')
    else:
        links.append("<span></span>")
    links.append(f'<a href="{html.escape(BLOB + "lessons/" + lessons[index].stem + ".py")}">Script on GitHub</a>')
    if index + 1 < len(lessons):
        nxt = lessons[index + 1]
        links.append(f'<a href="{mapping[nxt].split("/")[-1]}">{html.escape(nxt.stem[:2])} →</a>')
    return '<div class="pager">' + "".join(links) + "</div>"


def playground_presets() -> list:
    """The dashboard's presets, exported from Python (checked by the same validator as user circuits)."""
    if str(ROOT / "src") not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))
    from praxis_quantum_lab.circuit_playground import presets_payload

    return presets_payload()["presets"]


def _cut(text: str, start: str, end: str) -> str:
    """From `start` up to (not including) `end`; fails loudly if the dashboard markup changed."""
    i = text.index(start)
    return text[i:text.index(end, i)].rstrip()


def playground_page() -> str:
    index = (DASHBOARD / "index.html").read_text(encoding="utf-8")
    playground = _cut(index, '<section id="playground-area"', '<section id="bell-area"')
    for server_text, browser_text in PLAYGROUND_WORDING.items():
        if server_text not in playground:
            raise ValueError(f"dashboard markup changed: {server_text!r} not found")
        playground = playground.replace(server_text, browser_text)
    mosca_start = index.index('<section class="panel" aria-labelledby="mosca-heading">')
    mosca = index[mosca_start:index.index("</section>", mosca_start) + len("</section>")]
    scripts = "\n".join(f'  <script src="{name}" defer></script>' for name in PLAYGROUND_SCRIPTS)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Circuit Playground · Praxis Quantum Lab</title>
  <link rel="stylesheet" href="dashboard.css">
{scripts}
</head>
<body>
  <a class="skip-link" href="#workspace">Skip to the playground</a>
  <header class="masthead">
    <div class="brand"><span class="brand-symbol" aria-hidden="true">Ψ</span><div><p class="eyebrow"><a href="../index.html">PRAXIS QUANTUM LAB</a></p><h1>Circuit Playground</h1></div></div>
    <div class="masthead-actions"><div class="local-badge"><span aria-hidden="true"></span>RUNS IN YOUR BROWSER</div></div>
  </header>
  <main id="workspace">
    <div class="intro"><p>Build a circuit, step through it, sample it.</p><span>1–3 qubits · classical simulation in your browser · nothing is sent anywhere</span></div>
    {playground}

    <section id="mosca-area" aria-labelledby="mosca-area-heading">
      <div class="section-heading"><div><p class="eyebrow">DEADLINES</p><h2 id="mosca-area-heading">When must you migrate?</h2></div><p>Mosca's inequality, pure arithmetic: if x + y &gt; z, data protected today with RSA or elliptic curves can be recorded now and decrypted later.</p></div>
      <div class="sec-grid">
        {mosca}
      </div>
    </section>
    <p class="field-note">This is a classical simulation of at most 3 qubits; no quantum advantage is claimed. The full lab (Bell Lab, Security Lab with Aer) needs Python: <a href="../index.html">see the home page</a>.</p>
  </main>
</body>
</html>
"""


def landing() -> str:
    cards = [
        ("33 lessons", "From one qubit to Shor, Grover, error correction, BB84 and post-quantum crypto. Predict first, then run.", "lessons/index.html"),
        ("Toy RSA break", "Lesson 16: Shor's period finding on local Aer factors 21 and decrypts a message from the public key alone.", "lessons/16_toy_rsa_break.html"),
        ("Crypto-inventory scanner", "A read-only tool that finds quantum-vulnerable cryptography and ranks the migration work.", "pq-inventory.html"),
        ("Case study", "A consulting-style before/after engagement on a fictional warehouse company.", "case-study.html"),
        ("Scanner report (before)", "The report a manager would read: risk counts, a Mosca roadmap, every finding.", "reports/before.html"),
        ("Scanner report (after)", "The same systems after the first migration wave.", "reports/after.html"),
        ("Quantum Readiness Report", "A print-ready client report: websites, code findings, Mosca timeline, actions now / next / later.", "reports/readiness.html"),
        ("Is this website quantum-safe?", "pq_tls checks whether a site already uses hybrid post-quantum key exchange (X25519MLKEM768).", "pq-tls.html"),
    ]
    grid = "".join(
        f'<a class="card" href="{href}" style="text-decoration:none;color:inherit"><h3>{html.escape(t)}</h3><p>{html.escape(d)}</p></a>'
        for t, d, href in cards
    )
    body = f"""<section class="hero"><h1>From qubits to post-quantum migration</h1>
<p class="lead">A hands-on, simulator-only lab: build quantum algorithms, watch them break toy cryptography, and turn that into a practical plan for replacing RSA and elliptic curves.</p>
<div class="buttons"><a class="btn primary" href="playground/index.html">Try it now: Circuit Playground</a><a class="btn" href="{CODESPACES}">Run the full lab in GitHub Codespaces</a><a class="btn" href="lessons/index.html">Read the lessons</a><a class="btn" href="{TREE}">Source on GitHub</a></div></section>
<div class="grid">{grid}</div>
<div class="note"><strong>Honest limits.</strong> Everything quantum runs on a classical simulator (Qiskit Aer). No quantum advantage is claimed: at these toy sizes the classical method usually wins, and every result sits next to an honestly counted classical baseline. Real-attack resource estimates are quoted from published papers with sources and years.</div>
<h2>Run it yourself</h2>
<p>The <a href="playground/index.html">Circuit Playground</a> and the Mosca calculator run right here in your browser. The rest of the dashboard (Bell Lab, the Security Lab's simulations on Aer) needs Python: open it in a codespace with the button above (GitHub builds the environment and opens the dashboard in your browser, private to you), or run it locally:</p>
<pre><code>git clone {TREE}.git && cd {REPO.split("/")[1]}
python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/python -m praxis_quantum_lab.dashboard_server --port 8765</code></pre>"""
    return layout("Praxis Quantum Lab", body, 0)


def build(out: Path) -> list[str]:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    mapping = pages()
    mapping_resolved = {path.resolve(): target for path, target in mapping.items()}
    written = []

    def write(rel: str, text: str) -> None:
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        written.append(rel)

    write("style.css", CSS.strip() + "\n")
    write("index.html", landing())
    lessons = [p for p in mapping if p.parent.name == "lessons" and LESSON_RE.match(p.name)]
    for source, site_path in mapping.items():
        extra = ""
        if source in lessons:
            extra = lesson_pager(lessons.index(source), lessons, mapping)
        write(site_path, render(source, site_path, mapping_resolved, extra))
    for rel, source in REPORTS.items():
        write(rel, source.read_text(encoding="utf-8"))
    write("playground/index.html", playground_page())
    presets = json.dumps(playground_presets(), ensure_ascii=False).replace("</", "<\\/")
    write("playground/presets.js", f"// Exported from praxis_quantum_lab.circuit_playground.PRESETS by tools/build_site.py.\nwindow.PLAYGROUND_PRESETS = {presets};\n")
    for rel, source in PLAYGROUND_FILES.items():
        write(f"playground/{rel}", source.read_text(encoding="utf-8"))
    write(".nojekyll", "")
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "_site")
    arguments = parser.parse_args()
    written = build(arguments.out)
    print(f"Wrote {len(written)} files to {arguments.out}")


if __name__ == "__main__":
    main()
