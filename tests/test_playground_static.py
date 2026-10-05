"""The browser Circuit Playground on the static site: the JavaScript simulator matches the Python one
(to 1e-12, on a fixture Python writes), and the built page runs with no server and no network."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "playground_states.json"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="Node.js is not installed")


def _module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_cross_check_fixture_is_what_python_computes_now():
    generator = _module("generate_playground_states", ROOT / "tests" / "fixtures" / "generate_playground_states.py")
    current = json.loads(json.dumps(generator.build(), ensure_ascii=False))
    assert json.loads(FIXTURE.read_text(encoding="utf-8")) == current, \
        "stale: run tests/fixtures/generate_playground_states.py"
    assert len(current["random"]) == 50 and set(current["presets"]) == {p["id"] for p in generator.cp.PRESETS}
    assert {g["gate"] for r in current["random"] for g in r["gates"]} >= {"h", "x", "y", "z", "s", "t", "rx", "ry", "rz", "cx",
                                                                        "cz", "cp", "swap", "ccz", "ccx", "measure"}


@needs_node
def test_javascript_simulator_matches_python_to_1e_12():
    run = subprocess.run([NODE, str(ROOT / "tests" / "js" / "circuit_sim.test.js")], capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr + run.stdout
    assert run.stdout.startswith("CIRCUIT-SIM-OK") and int(run.stdout.split()[1]) > 4000


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    pytest.importorskip("markdown")
    out = tmp_path_factory.mktemp("site") / "_site"
    _module("build_site", ROOT / "tools" / "build_site.py").build(out)
    return out


def test_playground_page_is_built_with_local_scripts_and_exported_presets(site):
    from praxis_quantum_lab.circuit_playground import presets_payload

    folder = site / "playground"
    page = (folder / "index.html").read_text(encoding="utf-8")
    for name in ("circuit_sim.js", "presets.js", "playground_backend.js", "playground.js", "security.js"):
        assert f'<script src="{name}" defer></script>' in page and (folder / name).is_file(), name
    assert "browser sampling, not Aer" in page and "BROWSER SAMPLING, NOT AER" in page
    assert "local Aer" not in page and "LOCAL AER" not in page
    assert 'id="mosca-form"' in page and 'id="pg-circuit"' in page and 'id="bb84-form"' not in page
    text = (folder / "presets.js").read_text(encoding="utf-8")
    exported = json.loads(text[text.index("=") + 1:].strip().rstrip(";"))
    assert exported == json.loads(json.dumps(presets_payload()["presets"]))
    for name in ("circuit_sim.js", "playground.js", "security.js"):
        assert (folder / name).read_text() == (ROOT / "src" / "praxis_quantum_lab" / "dashboard_assets" / name).read_text()
    landing = (site / "index.html").read_text(encoding="utf-8")
    assert 'href="playground/index.html">Try it now' in landing


@needs_node
def test_built_playground_page_runs_on_the_dom_stub_without_network(site):
    run = subprocess.run([NODE, str(ROOT / "tests" / "js" / "site_playground_smoke.js"), str(site / "playground")],
                         capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr + run.stdout
    assert run.stdout.endswith("SITE-PLAYGROUND-OK")
