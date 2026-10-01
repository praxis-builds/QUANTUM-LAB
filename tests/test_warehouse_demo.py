"""The committed warehouse-demo reports must match a fresh scan (so the case study cannot drift)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pq_inventory import detect_keys, diff, roadmap
from pq_inventory.scanner import scan, to_document

DEMO = Path(__file__).resolve().parents[1] / "examples" / "warehouse-demo"
needs_cryptography = pytest.mark.skipif(not detect_keys.HAVE_CRYPTOGRAPHY, reason="needs the [pqc] extra (cryptography)")


def fresh(state: str) -> dict:
    return to_document(scan(DEMO / state), generated_at="2026-10-01T09:00:00+00:00")


@needs_cryptography
@pytest.mark.parametrize("state", ["before", "after"])
def test_committed_reports_match_a_fresh_scan(state):
    committed = json.loads((DEMO / "reports" / state / "scan.json").read_text())
    assert {f["fingerprint"] for f in committed["findings"]} == {f["fingerprint"] for f in fresh(state)["findings"]}


def test_demo_contains_no_private_keys():
    for path in DEMO.rglob("*"):
        if path.is_file():
            assert b"PRIVATE KEY" not in path.read_bytes().replace(b'"PRIVATE KEY"', b""), path


@needs_cryptography
def test_migration_wave_one_numbers():
    before, after = fresh("before"), fresh("after")
    assert before["summary"]["by_risk"] == {"CLASSICALLY-BROKEN": 16, "QUANTUM-BROKEN": 17, "QUANTUM-WEAKENED": 2, "OK": 2}
    assert after["summary"]["by_risk"] == {"CLASSICALLY-BROKEN": 1, "QUANTUM-BROKEN": 11, "QUANTUM-WEAKENED": 0, "OK": 14}
    result = diff.compare(before, after)
    assert result["counts"]["fixed"]["CLASSICALLY-BROKEN"] == 15
    plan = roadmap.build(after["findings"], roadmap.load_config(DEMO / "systems.json"))
    assert plan["items"][0]["system"] == "Supplier EDI feed" and plan["unassigned_findings"] == 0
