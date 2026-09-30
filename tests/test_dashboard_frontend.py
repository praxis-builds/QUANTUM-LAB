"""Dashboard front end and process-level checks.

No browser is available here, so the scripts are checked three ways: static checks
against index.html, pure-logic tests under Node, and a UI smoke run of the real
playground.js on a small DOM stub against a real dashboard process. Node tests are
skipped when Node is not installed; the static and process tests always run.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from praxis_quantum_lab import circuit_playground as cp

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src" / "praxis_quantum_lab" / "dashboard_assets"
JS_TESTS = ROOT / "tests" / "js"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="Node.js is not installed")


def html() -> str:
    return (ASSETS / "index.html").read_text(encoding="utf-8")


def script_ids(name: str) -> set[str]:
    source = (ASSETS / name).read_text(encoding="utf-8")
    return set(re.findall(r'(?:byId|\$)\("([A-Za-z0-9_-]+)"\)', source))


def test_every_script_id_exists_exactly_once_in_index_html():
    ids = re.findall(r'\bid="([^"]+)"', html())
    duplicates = {i for i in ids if ids.count(i) > 1}
    assert not duplicates
    for name in ("app.js", "playground.js"):
        missing = script_ids(name) - set(ids)
        assert not missing, f"{name} uses ids missing from index.html: {sorted(missing)}"
    # template ids built from the tab list
    for area in ("playground", "bell", "kernel"):
        assert f"{area}-tab" in ids and f"{area}-area" in ids


def test_html_respects_the_content_security_policy():
    page = html()
    assert "style=" not in page, "inline style attributes are blocked by the CSP"
    assert "<style" not in page
    assert re.findall(r"<script[^>]*>", page) == ['<script src="/app.js" defer>', '<script src="/playground.js" defer>']
    assert not re.search(r"\son[a-z]+=", page), "inline event handlers are blocked by the CSP"
    assert not re.search(r"(src|href)=\"(https?:)?//", page), "no external assets"
    for name in ("app.js", "playground.js", "style.css"):
        source = (ASSETS / name).read_text(encoding="utf-8")
        assert "http://" not in source.replace("http://www.w3.org/2000/svg", "") and "https://" not in source
        assert "setAttribute(\"style\"" not in source and "innerHTML" not in source and "eval(" not in source


def test_playground_is_the_default_tab_and_others_start_hidden():
    page = html()
    assert re.search(r'id="playground-tab" class="tab active" aria-pressed="true"', page)
    assert re.search(r'<section id="bell-area"[^>]*hidden', page)
    assert re.search(r'<section id="kernel-area"[^>]*hidden', page)
    assert not re.search(r'<section id="playground-area"[^>]*hidden', page)


@needs_node
@pytest.mark.parametrize("name", ["app.js", "playground.js"])
def test_scripts_parse(name):
    subprocess.run([NODE, "--check", str(ASSETS / name)], check=True, capture_output=True, timeout=30)


@needs_node
def test_playground_core_logic_and_limits_match_the_server():
    run = subprocess.run([NODE, str(JS_TESTS / "playground_core.test.js")], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    limits = json.loads(run.stdout)
    assert limits["MAX_QUBITS"] == cp.MAX_QUBITS
    assert limits["MAX_GATES"] == cp.MAX_GATES
    assert limits["MAX_SHOTS"] == cp.MAX_SHOTS
    assert limits["MAX_SEED"] == cp.MAX_SEED
    assert set(limits["PALETTE"]) == cp.GATE_NAMES
    assert set(limits["ANGLE"]) == cp.ROTATION_GATES
    assert set(limits["TWO"]) == cp.TWO_QUBIT_GATES


@needs_node
def test_playground_ui_smoke_against_real_server(dashboard_process):
    process, port = dashboard_process
    run = subprocess.run([NODE, str(JS_TESTS / "playground_ui_smoke.js"), str(port)], capture_output=True, text=True, timeout=240)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "UI-SMOKE-OK" in run.stdout
    assert process.poll() is None


def test_new_static_route_is_served_with_security_headers(dashboard_process):
    from http.client import HTTPConnection

    _, port = dashboard_process
    for path, kind in (("/playground.js", "javascript"), ("/api/circuit-presets", "application/json")):
        connection = HTTPConnection("127.0.0.1", port, timeout=30)
        connection.request("GET", path)
        response = connection.getresponse()
        body = response.read()
        connection.close()
        assert response.status == 200 and kind in response.getheader("Content-Type") and body
        assert "script-src 'self'" in response.getheader("Content-Security-Policy")
        assert response.getheader("X-Content-Type-Options") == "nosniff"
