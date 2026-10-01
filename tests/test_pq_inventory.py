"""pq_inventory: detection quality on a planted corpus, safety guarantees, reports, diff, CI mode."""

from __future__ import annotations

import json
import os
import re
import shutil
from collections import Counter
from pathlib import Path

import pytest

from pq_inventory import algorithms, cli, detect_keys, reports, roadmap
from pq_inventory.scanner import scan, to_document

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CORPUS = FIXTURES / "pq_inventory"
EXPECTED = json.loads((FIXTURES / "pq_inventory_expected.json").read_text())
PACKAGE = Path(__file__).resolve().parents[1] / "tools" / "pq_inventory"
# Stated quality bars for the planted corpus (measured values are reported in docs/pq-inventory.md).
MIN_PRECISION = 0.95
MIN_RECALL = 0.95
needs_cryptography = pytest.mark.skipif(not detect_keys.HAVE_CRYPTOGRAPHY, reason="needs the [pqc] extra (cryptography)")


def corpus_doc():
    return to_document(scan(CORPUS), generated_at="2026-10-01T00:00:00+00:00")


def precision_recall(doc) -> tuple[float, float, Counter, Counter]:
    found = Counter((f["file"], f["algorithm"]) for f in doc["findings"])
    expected = Counter((file, alg) for file, algs in EXPECTED["expected"].items() for alg in algs)
    matched = sum((found & expected).values())
    return matched / max(sum(found.values()), 1), matched / max(sum(expected.values()), 1), found - expected, expected - found


# ------------------------------------------------------------------ detection quality

@needs_cryptography
def test_corpus_precision_and_recall_meet_the_stated_bars():
    precision, recall, false_positives, misses = precision_recall(corpus_doc())
    assert recall >= MIN_RECALL, f"missed: {dict(misses)}"
    assert precision >= MIN_PRECISION, f"unexpected: {dict(false_positives)}"


@needs_cryptography
def test_decoys_and_binaries_are_not_reported():
    doc = corpus_doc()
    files = {f["file"] for f in doc["findings"]}
    assert "clean/decoys.py" not in files and "clean/README.md" not in files
    assert {"file": "clean/blob.bin", "reason": "binary file"} in doc["skipped"]
    py = [f for f in doc["findings"] if f["file"] == "py/legacy_crypto.py"]
    assert all(f["line"] not in (8, 9) for f in py)  # the md5 comment and the rsa_value variable


@needs_cryptography
def test_classification_examples_from_the_corpus():
    by = {(f["file"], f["algorithm"]): f for f in corpus_doc()["findings"]}
    assert by[("js/crypto_utils.js", "RSA")]["risk"] == algorithms.CLASSICALLY_BROKEN  # 1024-bit
    assert by[("py/legacy_crypto.py", "RSA")]["risk"] == algorithms.QUANTUM_BROKEN
    assert by[("py/legacy_crypto.py", "AES-128")]["risk"] == algorithms.QUANTUM_WEAKENED
    assert by[("clean/modern.py", "AES-256")]["risk"] == algorithms.OK
    assert by[("keys/legacy_sha1_cert.pem", "SHA-1")]["risk"] == algorithms.CLASSICALLY_BROKEN
    assert by[("tls/nginx.conf", "HYBRID-PQ")]["risk"] == algorithms.OK
    assert by[("erp/DEFAULT.PFL", "ECDH")]["heuristic"] is True
    assert "FIPS 203" in by[("tls/nginx.conf", "ECDH")]["replacement"]
    assert "FIPS 204" in by[("ssh/authorized_keys", "EdDSA")]["replacement"]


@pytest.mark.parametrize("suite,expected", [
    ("ECDHE-RSA-AES128-GCM-SHA256", ["ECDH", "RSA-SIGNATURE", "AES-128", "SHA-256"]),
    ("AES256-SHA", ["RSA-KEX", "RSA-SIGNATURE", "AES-256", "HMAC-SHA1"]),
    ("DES-CBC3-SHA", ["RSA-KEX", "RSA-SIGNATURE", "3DES", "HMAC-SHA1"]),
    ("TLS_AES_256_GCM_SHA384", ["AES-256", "SHA-384"]),
    ("ECDHE-ECDSA-CHACHA20-POLY1305", ["ECDH", "ECDSA", "CHACHA20"]),
])
def test_cipher_suite_parsing(suite, expected):
    assert algorithms.suite_algorithms(suite) == expected


def test_cipher_strings_skip_exclusions_keywords_and_directives():
    assert algorithms.parse_cipher_string("HIGH:!aNULL:-RC4:ECDHE-RSA-AES256-GCM-SHA384:DEFAULT@SECLEVEL=2") == ["ECDHE-RSA-AES256-GCM-SHA384"]


def test_short_rsa_keys_are_classically_broken():
    assert algorithms.classify("RSA", 1024)[0] == algorithms.CLASSICALLY_BROKEN
    assert algorithms.classify("RSA", 4096)[0] == algorithms.QUANTUM_BROKEN


# ------------------------------------------------------------------------- safety

def _snapshot(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file() and not p.is_symlink()}


@needs_cryptography
def test_private_keys_report_only_metadata_never_material(tmp_path):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa

    tree = tmp_path / "tree"
    tree.mkdir()
    pem, pkcs8, none = serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    keys = {"rsa.key": rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(pem, pkcs8, none),
            "ec.key": ec.generate_private_key(ec.SECP384R1()).private_bytes(pem, serialization.PrivateFormat.TraditionalOpenSSL, none),
            "id_ed25519": ed25519.Ed25519PrivateKey.generate().private_bytes(pem, serialization.PrivateFormat.OpenSSH, none)}
    for name, data in keys.items():
        (tree / name).write_bytes(data)
    out = tmp_path / "out"
    assert cli.main(["scan", str(tree), "--out", str(out)]) == 0
    doc = json.loads((out / "scan.json").read_text())
    facts = {f["file"]: (f["algorithm"], f["key_size"], f["category"]) for f in doc["findings"]}
    assert facts == {"rsa.key": ("RSA", 2048, "private-key"), "ec.key": ("EC", 384, "private-key"),
                     "id_ed25519": ("EdDSA", 256, "private-key")}
    material = [line for data in keys.values() for line in data.decode().splitlines() if "-----" not in line and len(line) > 20]
    for report in out.iterdir():
        text = report.read_text()
        assert not any(chunk in text for chunk in material), report.name


@pytest.mark.skipif(os.name == "nt", reason="symlinks")
def test_symlink_loops_and_escapes_are_not_followed(tmp_path):
    tree = tmp_path / "tree"
    (tree / "sub").mkdir(parents=True)
    (tree / "sub" / "a.py").write_text("import hashlib\nhashlib.md5(b'x')\n")
    (tree / "sub" / "loop").symlink_to(tree, target_is_directory=True)
    outside = tmp_path / "outside.py"
    outside.write_text("import hashlib\nhashlib.sha1(b'x')\n")
    (tree / "escape.py").symlink_to(outside)
    result = scan(tree)
    assert [f.file for f in result.findings] == ["sub/a.py"]
    reasons = {s["file"]: s["reason"] for s in result.skipped}
    assert reasons["sub/loop/"] == "symlink (not followed)" and reasons["escape.py"] == "symlink (not followed)"


def test_size_limit_and_file_limit(tmp_path):
    (tmp_path / "big.py").write_text("x = 1\n" * 1000)
    (tmp_path / "small.py").write_text("import hashlib\nhashlib.md5(b'')\n")
    result = scan(tmp_path, max_bytes=100)
    assert {"file": "big.py", "reason": "larger than 100 bytes"} in result.skipped
    assert result.files_scanned == 1
    limited = scan(tmp_path, max_files=1)
    assert limited.files_scanned == 1 and any("file limit" in s["reason"] for s in limited.skipped)


@needs_cryptography
def test_scan_writes_only_inside_out_and_never_scans_its_own_reports(tmp_path):
    tree = tmp_path / "tree"
    shutil.copytree(CORPUS, tree)
    before = _snapshot(tree)
    out = tree / "reports"  # deliberately inside the scanned tree
    assert cli.main(["scan", str(tree), "--out", str(out)]) == 0
    after = {k: v for k, v in _snapshot(tree).items() if not k.startswith("reports/")}
    assert after == before
    assert cli.main(["scan", str(tree), "--out", str(out)]) == 0
    files = {f["file"] for f in json.loads((out / "scan.json").read_text())["findings"]}
    assert not any(f.startswith("reports/") for f in files)


def test_scanner_has_no_network_code():
    code = "\n".join(p.read_text() for p in PACKAGE.glob("*.py"))
    for forbidden in ("import socket", "urllib", "http.client", "requests", "subprocess", "import ssl"):
        assert forbidden not in code, forbidden


# ------------------------------------------------------------------- CLI and reports

@needs_cryptography
def test_cli_outputs_and_fail_on_exit_codes(tmp_path):
    out = tmp_path / "out"
    assert cli.main(["scan", str(CORPUS), "--out", str(out), "--timestamp", "2026-10-01T00:00:00+00:00"]) == 0
    assert {p.name for p in out.iterdir()} == {"scan.json", "report.html", "report.md", "cbom.cdx.json"}
    assert cli.main(["scan", str(CORPUS), "--out", str(out), "--fail-on", "quantum-broken", "--formats", "json"]) == 1
    assert cli.main(["scan", str(CORPUS / "clean"), "--out", str(out / "c"), "--fail-on", "quantum-weakened"]) == 0
    assert cli.main(["scan", str(tmp_path / "missing"), "--out", str(out)]) == 2
    assert cli.main(["scan", str(CORPUS), "--out", str(out), "--formats", "pdf"]) == 2


@needs_cryptography
def test_html_report_is_self_contained_and_escaped(tmp_path):
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "x<script>.py").write_text("import hashlib\nhashlib.md5(b'')\n")
    out = tmp_path / "out"
    cli.main(["scan", str(tree), "--out", str(out), "--formats", "html"])
    page = (out / "report.html").read_text()
    assert "<script" not in page.replace("&lt;script", "")
    assert not re.search(r"(src|href)\s*=\s*[\"']?https?://", page)
    assert "Executive summary" in page and "already weak today" in page


@needs_cryptography
def test_cbom_is_cyclonedx_shaped():
    bom = reports.cbom(corpus_doc())
    assert bom["bomFormat"] == "CycloneDX" and bom["specVersion"] == "1.6"
    assert bom["serialNumber"].startswith("urn:uuid:")
    types = Counter(c["cryptoProperties"]["assetType"] for c in bom["components"])
    assert {"algorithm", "certificate", "protocol", "related-crypto-material"} <= set(types)
    for component in bom["components"]:
        assert component["type"] == "cryptographic-asset" and component["evidence"]["occurrences"]
    assert reports.cbom(corpus_doc())["serialNumber"] == bom["serialNumber"]  # deterministic


@needs_cryptography
def test_diff_tracks_fixed_new_and_unchanged(tmp_path):
    tree = tmp_path / "tree"
    shutil.copytree(CORPUS, tree)
    assert cli.main(["scan", str(tree), "--out", str(tmp_path / "before"), "--formats", "json"]) == 0
    source = tree / "py" / "legacy_crypto.py"
    text = source.read_text().replace("hashlib.md5(data)", "hashlib.sha256(data)")
    source.write_text("# a new comment line shifts every line number\n" + text)
    (tree / "py" / "new.py").write_text("import hashlib\nhashlib.sha1(b'')\n")
    assert cli.main(["scan", str(tree), "--out", str(tmp_path / "after"), "--formats", "json"]) == 0
    code = cli.main(["diff", str(tmp_path / "before" / "scan.json"), str(tmp_path / "after" / "scan.json"),
                     "--out", str(tmp_path / "diff"), "--fail-on", "classically-broken"])
    result = json.loads((tmp_path / "diff" / "diff.json").read_text())
    fixed = [(f["file"], f["algorithm"]) for f in result["fixed"]]
    new = [(f["file"], f["algorithm"]) for f in result["new_findings"]]
    assert fixed == [("py/legacy_crypto.py", "MD5")]
    assert sorted(new) == [("py/legacy_crypto.py", "SHA-256"), ("py/new.py", "SHA-1")]
    assert code == 1  # a new SHA-1 finding fails the CI gate
    assert (tmp_path / "diff" / "diff.md").read_text().startswith("# Cryptography inventory: progress")


def test_user_rules_extend_detection_and_bad_rules_fail_cleanly(tmp_path):
    rules = tmp_path / "rules.json"
    rules.write_text(json.dumps({"rules": [{"id": "custom-blowfish", "files": [".py"], "pattern": r"Blowfish\.new\(", "algorithm": "DES"}]}))
    (tmp_path / "tree").mkdir()
    (tmp_path / "tree" / "x.py").write_text("c = Blowfish.new(key)\n")
    assert cli.main(["scan", str(tmp_path / "tree"), "--out", str(tmp_path / "o"), "--rules", str(rules), "--formats", "json"]) == 0
    assert [f["rule"] for f in json.loads((tmp_path / "o" / "scan.json").read_text())["findings"]] == ["custom-blowfish"]
    rules.write_text(json.dumps({"rules": [{"id": "broken", "pattern": "x"}]}))
    assert cli.main(["scan", str(tmp_path / "tree"), "--out", str(tmp_path / "o"), "--rules", str(rules)]) == 2
    yaml_rules = tmp_path / "rules.yaml"
    yaml_rules.write_text("rules: []\n")
    try:
        import yaml  # noqa: F401
    except ImportError:
        assert cli.main(["scan", str(tmp_path / "tree"), "--out", str(tmp_path / "o"), "--rules", str(yaml_rules)]) == 2


# --------------------------------------------------------------------------- roadmap

def test_roadmap_orders_systems_by_mosca_and_labels_assumptions(tmp_path):
    findings = [
        {"file": "archive/a.py", "risk": "QUANTUM-BROKEN", "severity": 2, "algorithm": "RSA", "replacement": "ML-KEM", "fingerprint": "1"},
        {"file": "web/b.py", "risk": "QUANTUM-BROKEN", "severity": 2, "algorithm": "ECDH", "replacement": "ML-KEM", "fingerprint": "2"},
        {"file": "legacy/c.py", "risk": "CLASSICALLY-BROKEN", "severity": 3, "algorithm": "MD5", "replacement": "SHA-256", "fingerprint": "3"},
        {"file": "batch/d.py", "risk": "QUANTUM-WEAKENED", "severity": 1, "algorithm": "AES-128", "replacement": "AES-256", "fingerprint": "4"},
    ]
    config_file = tmp_path / "systems.json"
    config_file.write_text(json.dumps({"assumptions": {"z_years": 10}, "systems": [
        {"name": "web", "paths": ["web/*"], "data_lifetime_years": 1, "migration_years": 2},
        {"name": "archive", "paths": ["archive/*"], "data_lifetime_years": 25, "migration_years": 5},
        {"name": "legacy", "paths": ["legacy/*"]},
        {"name": "batch", "paths": ["batch/*"], "data_lifetime_years": 1, "migration_years": 1}]}))
    plan = roadmap.build(findings, roadmap.load_config(config_file))
    assert [i["system"] for i in plan["items"]] == ["legacy", "archive", "web", "batch"]
    assert [i["tier"] for i in plan["items"]] == [1, 2, 3, 4]
    archive = plan["items"][1]
    assert archive["mosca_at_risk"] and archive["slack_years"] == -20
    legacy = plan["items"][0]
    assert legacy["x_from"] == "default assumption" and legacy["y_from"] == "default assumption"
    default = roadmap.load_config(None)
    assert "ASSUMPTION" in default["assumptions"]["z_source"] and "NOT a forecast" in default["assumptions"]["z_source"]
    assert default["assumptions"]["z_years"] == max(0, 2035 - default["assumptions"]["reference_year"])


def test_without_cryptography_keys_are_named_from_labels_and_oids(monkeypatch):
    monkeypatch.setattr(detect_keys, "HAVE_CRYPTOGRAPHY", False)
    result = scan(CORPUS / "keys")
    by_file = {(f.file, f.rule.endswith("-hash")): f for f in result.findings}
    legacy = by_file[("legacy_sha1_cert.pem", False)]
    assert legacy.algorithm == "RSA-SIGNATURE" and "from its OID" in legacy.detail and "install the [pqc] extra" in legacy.detail
    assert by_file[("legacy_sha1_cert.pem", True)].algorithm == "SHA-1"  # from the signature OID
    assert by_file[("ecdsa_cert.der", False)].algorithm == "ECDSA"
    assert by_file[("ec_p256_public.pem", False)].algorithm == "EC" and by_file[("ec_p256_public.pem", False)].key_size is None
    encrypted = by_file[("encrypted_private_key.pem", False)]
    assert (encrypted.category, encrypted.algorithm, encrypted.heuristic) == ("private-key", "UNKNOWN", True)
    assert any("'cryptography' package is not installed" in note for note in result.notes)
