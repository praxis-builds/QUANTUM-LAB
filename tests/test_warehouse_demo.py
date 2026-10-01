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


@needs_cryptography
def test_every_committed_report_file_is_what_the_documented_commands_write(tmp_path, monkeypatch):
    """Byte for byte: scan.json, report.md, report.html, cbom.cdx.json for both states, diff.json and diff.md.
    Fingerprints alone would let risk, replacement, detail, roadmap or the rendered reports drift."""
    from pq_inventory import cli

    monkeypatch.chdir(DEMO.parents[1])  # the README commands run from the repository root with relative paths
    demo = "examples/warehouse-demo"
    for state in ("before", "after"):
        assert cli.main(["scan", f"{demo}/{state}", "--out", str(tmp_path / state), "--systems", f"{demo}/systems.json",
                         "--timestamp", "2026-10-01T09:00:00+00:00"]) == 0
    fresh_diff = tmp_path / "diff"
    cli.main(["diff", str(tmp_path / "before" / "scan.json"), str(tmp_path / "after" / "scan.json"), "--out", str(fresh_diff)])
    committed = sorted(p.relative_to(DEMO / "reports").as_posix() for p in (DEMO / "reports").rglob("*") if p.is_file())
    assert committed == ["after/cbom.cdx.json", "after/report.html", "after/report.md", "after/scan.json",
                         "before/cbom.cdx.json", "before/report.html", "before/report.md", "before/scan.json",
                         "diff/diff.json", "diff/diff.md"]
    stale = [name for name in committed if (tmp_path / name).read_bytes() != (DEMO / "reports" / name).read_bytes()]
    assert stale == [], "regenerate with the commands in examples/warehouse-demo/README.md"


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
