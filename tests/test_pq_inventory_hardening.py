"""Regression tests for docs/REVIEW-FINDINGS.md: each test failed before its fix."""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path

import pytest

from pq_inventory import cli

# --------------------------------------------- 1. no literal values in any output

# Secrets of several lengths, all below the old 40-character redaction threshold except the last.
PLANTED_SECRETS = ["Kx9!pq", "Tr0ub4dor&3", "Sup3rS3cretKey!!24bytes!", "00112233445566778899aabbccddeeff",
                   "hunter2-hunter2-hunter2-hunter2-hunter2", "A" * 64]


def _plant_secrets(tree: Path) -> None:
    s = PLANTED_SECRETS
    tree.mkdir(parents=True, exist_ok=True)
    (tree / "app.py").write_text(
        "from Crypto.Cipher import DES3, AES\n"
        f"cipher = DES3.new(b\"{s[2]}\", DES3.MODE_CBC)\n"
        f"key = bytes.fromhex(\"{s[3]}\"); aes = AES.new(key, AES.MODE_GCM)  # pw {s[0]}\n"
        f"import hashlib; digest = hashlib.md5(b\"{s[5]}\")\n")
    (tree / "app.js").write_text(f'const c = crypto.createCipheriv("des-ede3-cbc", "{s[4]}", iv);\n')
    (tree / "partner.properties").write_text(f"as2.encryption=3des  # partner password: {s[1]}\n")
    (tree / "nginx.conf").write_text(f"ssl_protocols TLSv1 TLSv1.2; # admin password {s[1]}\n")


def _run(argv: list[str]) -> tuple[int, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(argv)
    return code, out.getvalue() + err.getvalue()


def test_no_literal_value_reaches_any_output(tmp_path):
    tree = tmp_path / "tree"
    _plant_secrets(tree)
    code, console = _run(["scan", str(tree), "--out", str(tmp_path / "a"), "--timestamp", "2026-10-01T00:00:00+00:00"])
    assert code == 0
    (tree / "app.py").write_text((tree / "app.py").read_text() + "import hashlib; hashlib.sha1(b'x')\n")
    code, console2 = _run(["scan", str(tree), "--out", str(tmp_path / "b"), "--formats", "json"])
    code, console3 = _run(["diff", str(tmp_path / "a" / "scan.json"), str(tmp_path / "b" / "scan.json"), "--out", str(tmp_path / "d")])
    outputs = {p.relative_to(tmp_path).as_posix(): p.read_text() for p in tmp_path.glob("[abd]/*") if p.is_file()}
    assert {"a/scan.json", "a/report.html", "a/report.md", "a/cbom.cdx.json", "d/diff.json", "d/diff.md"} <= set(outputs)
    outputs["console"] = console + console2 + console3
    for name, text in outputs.items():
        for secret in PLANTED_SECRETS:
            assert secret not in text, f"{secret!r} leaked into {name}"
    findings = json.loads(outputs["a/scan.json"])["findings"]
    assert len(findings) >= 5
    assert all(f["evidence"] in ("", "[redacted]") for f in findings)


# --------------------------------------------- 2. PEM parsing is linear, with a time budget

def _crafted_pem(size: int) -> bytes:
    """BEGIN headers with no END: the old lazy regex rescanned to the end of the file for each one."""
    unit = b"-----BEGIN A-----\n"
    return unit * (size // len(unit))


def test_crafted_2mib_pem_file_scans_in_under_two_seconds(tmp_path):
    import time

    from pq_inventory.scanner import scan

    (tmp_path / "evil.pem").write_bytes(_crafted_pem(2 * 1024 * 1024 - 64))
    # the same with one matching END at the very bottom: every BEGIN now has a candidate partner
    (tmp_path / "evil2.pem").write_bytes(_crafted_pem(2 * 1024 * 1024 - 256) + b"-----END A-----\n")
    for name in ("evil.pem", "evil2.pem"):
        start = time.perf_counter()
        result = scan(tmp_path / name)
        assert time.perf_counter() - start < 2.0, name
        assert result.files_scanned == 1


def test_pem_blocks_still_pair_begin_and_end_markers():
    from pq_inventory.detect_keys import pem_blocks

    data = (b"junk\n-----BEGIN A-----\n-----BEGIN CERTIFICATE-----\nAAAA\n-----END CERTIFICATE-----\n"
            b"-----BEGIN PUBLIC KEY-----\nBBBB\n-----END PUBLIC KEY-----\n-----END A-----\n")
    assert [(label, body.strip()) for label, body, _ in pem_blocks(data)] == [("CERTIFICATE", b"AAAA"), ("PUBLIC KEY", b"BBBB")]


def test_per_file_time_budget_stops_work_and_says_so(tmp_path):
    from pq_inventory.scanner import scan

    (tmp_path / "many.py").write_text("import hashlib\n" + "hashlib.md5(b'x')\n" * 20000)
    result = scan(tmp_path, time_budget=0.0)
    assert any(s["file"] == "many.py" and "time budget" in s["reason"] for s in result.skipped)


# --------------------------------------------- 3. FIFOs, sockets and devices are skipped, not opened

@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs POSIX FIFOs")
def test_fifo_and_socket_are_skipped_and_the_scan_finishes(tmp_path):
    import socket
    import threading

    from pq_inventory.scanner import scan

    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "a.py").write_text("import hashlib\nhashlib.md5(b'x')\n")
    os.mkfifo(tree / "pipe")  # no writer: opening or reading it blocks forever
    server = socket.socket(socket.AF_UNIX)
    server.bind(str(tree / "sock"))
    result: dict = {}
    worker = threading.Thread(target=lambda: result.setdefault("scan", scan(tree)), daemon=True)
    worker.start()
    worker.join(timeout=10)
    server.close()
    assert not worker.is_alive(), "scan hung on a FIFO"
    scanned = result["scan"]
    assert [f.file for f in scanned.findings] == ["a.py"] and scanned.files_scanned == 1
    reasons = {s["file"]: s["reason"] for s in scanned.skipped}
    assert reasons["pipe"] == "not a regular file (FIFO)" and reasons["sock"] == "not a regular file (socket)"


def test_read_is_capped_even_if_the_size_check_passes(tmp_path, monkeypatch):
    """A file that grows between stat and read (or reports size 0) is still read only up to the limit."""
    from pq_inventory import walker

    (tmp_path / "grow.py").write_text("x" * 500)

    def lying(real):
        def call(*args, **kwargs):
            st = real(*args, **kwargs)
            return os.stat_result((st.st_mode, st.st_ino, st.st_dev, st.st_nlink, st.st_uid, st.st_gid, 0, *st[7:10]))
        return call

    for name in ("stat", "lstat", "fstat"):  # every way the walker could ask for the size reports 0
        monkeypatch.setattr(os, name, lying(getattr(os, name)))
    skipped: list = []
    assert list(walker.walk(tmp_path, max_bytes=100, skipped=skipped)) == []
    assert {"file": "grow.py", "reason": "larger than 100 bytes"} in skipped


# --------------------------------------------- 4. ML-KEM / ML-DSA / SLH-DSA keys and certificates are OK

PQC_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "pq_inventory" / "keys" / "pqc"
PQC_EXPECTED = {"mlkem768_public.pem": ("ML-KEM", "ML-KEM-768", "public-key"),
                "mldsa65_public.pem": ("ML-DSA", "ML-DSA-65", "public-key"),
                "mldsa65_cert.pem": ("ML-DSA", "ML-DSA-65", "certificate"),
                "slh_dsa_sha2_128s_public.pem": ("SLH-DSA", "SLH-DSA-SHA2-128s", "public-key"),
                "slh_dsa_sha2_128s_cert.der": ("SLH-DSA", "SLH-DSA-SHA2-128s", "certificate")}


def _pqc_facts(result) -> dict:
    return {f.file: (f.algorithm, f.risk, f.category, f.detail) for f in result.findings}


@pytest.mark.parametrize("have_cryptography", [True, False])
def test_committed_pqc_fixtures_are_recognised_by_oid(monkeypatch, have_cryptography):
    from pq_inventory import detect_keys
    from pq_inventory.scanner import scan

    if have_cryptography and not detect_keys.HAVE_CRYPTOGRAPHY:
        pytest.skip("needs the [pqc] extra (cryptography)")
    monkeypatch.setattr(detect_keys, "HAVE_CRYPTOGRAPHY", have_cryptography and detect_keys.HAVE_CRYPTOGRAPHY)
    facts = _pqc_facts(scan(PQC_FIXTURES))
    assert set(facts) == set(PQC_EXPECTED)
    for name, (algorithm, parameter_set, category) in PQC_EXPECTED.items():
        found_algorithm, risk, found_category, detail = facts[name]
        assert (found_algorithm, risk, found_category) == (algorithm, "OK", category), name
        assert parameter_set in detail, (name, detail)


def test_real_ml_kem_and_ml_dsa_artefacts_are_ok(tmp_path):
    asymmetric = pytest.importorskip("cryptography.hazmat.primitives.asymmetric")
    try:
        from cryptography.hazmat.primitives.asymmetric import mldsa, mlkem
    except ImportError:
        pytest.skip("cryptography without ML-KEM/ML-DSA")
    import datetime

    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    from cryptography.x509.oid import NameOID

    del asymmetric
    pem, spki = serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    keys = {"mldsa44": mldsa.MLDSA44PrivateKey.generate(), "mldsa65": mldsa.MLDSA65PrivateKey.generate(),
            "mldsa87": mldsa.MLDSA87PrivateKey.generate(), "mlkem768": mlkem.MLKEM768PrivateKey.generate(),
            "mlkem1024": mlkem.MLKEM1024PrivateKey.generate()}
    for name, key in keys.items():
        (tmp_path / f"{name}_public.pem").write_bytes(key.public_key().public_bytes(pem, spki))
    (tmp_path / "mldsa65_private.pem").write_bytes(keys["mldsa65"].private_bytes(
        pem, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "pq.test.invalid")])
    start = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(keys["mldsa87"].public_key())
            .serial_number(1).not_valid_before(start).not_valid_after(start + datetime.timedelta(days=30))
            .sign(keys["mldsa87"], None))
    (tmp_path / "mldsa87_cert.pem").write_bytes(cert.public_bytes(pem))
    (tmp_path / "mldsa87_cert.der").write_bytes(cert.public_bytes(serialization.Encoding.DER))
    out = tmp_path / "out"
    assert cli.main(["scan", str(tmp_path), "--out", str(out), "--formats", "json", "--fail-on", "quantum-weakened"]) == 0
    facts = {f["file"]: (f["algorithm"], f["risk"], f["detail"]) for f in json.loads((out / "scan.json").read_text())["findings"]}
    expected = {"mldsa44_public.pem": ("ML-DSA", "ML-DSA-44"), "mldsa65_public.pem": ("ML-DSA", "ML-DSA-65"),
                "mldsa87_public.pem": ("ML-DSA", "ML-DSA-87"), "mlkem768_public.pem": ("ML-KEM", "ML-KEM-768"),
                "mlkem1024_public.pem": ("ML-KEM", "ML-KEM-1024"), "mldsa65_private.pem": ("ML-DSA", "ML-DSA-65"),
                "mldsa87_cert.pem": ("ML-DSA", "ML-DSA-87"), "mldsa87_cert.der": ("ML-DSA", "ML-DSA-87")}
    assert set(facts) == set(expected)
    for file, (algorithm, parameter_set) in expected.items():
        assert facts[file][:2] == (algorithm, "OK") and parameter_set in facts[file][2], (file, facts[file])
    assert "pq.test.invalid" in facts["mldsa87_cert.pem"][2]


def test_real_slh_dsa_public_key_from_liboqs_is_ok(tmp_path):
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lessons"))
    import _pqc

    oqs = _pqc.load_oqs()
    if oqs is None:
        pytest.skip(_pqc.missing_reason() or "liboqs missing")
    from pq_inventory.der import spki_pem
    from pq_inventory.scanner import scan

    with oqs.Signature("SLH_DSA_PURE_SHAKE_256F") as signer:
        public = signer.generate_keypair()
    (tmp_path / "slh.pem").write_bytes(spki_pem("2.16.840.1.101.3.4.3.31", public))
    (finding,) = scan(tmp_path).findings
    assert (finding.algorithm, finding.risk) == ("SLH-DSA", "OK") and "SLH-DSA-SHAKE-256f" in finding.detail


def test_losing_the_deprecated_dh_module_does_not_switch_off_key_parsing(monkeypatch):
    """Review #15: cryptography deprecates finite-field DH; its removal must not disable all parsing."""
    import importlib.util
    import sys

    asymmetric = pytest.importorskip("cryptography.hazmat.primitives.asymmetric")
    from pq_inventory import detect_keys

    monkeypatch.delattr(asymmetric, "dh", raising=False)
    monkeypatch.setitem(sys.modules, "cryptography.hazmat.primitives.asymmetric.dh", None)  # import now fails
    spec = importlib.util.spec_from_file_location("pq_inventory._detect_keys_probe", detect_keys.__file__)
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    assert probe.HAVE_CRYPTOGRAPHY and probe.dh is None
    ec_key = (PQC_FIXTURES.parent / "ec_p256_public.pem").read_bytes()
    (finding,) = probe.detect("ec.pem", ec_key, True)
    assert (finding.algorithm, finding.key_size) == ("EC", 256)


# --------------------------------------------- 5. --fail-on X means "X or worse"; the sample CI gate blocks QUANTUM-BROKEN

ONE_FINDING = {"OK": "import hashlib\nhashlib.sha256(b'x')\n",
               "QUANTUM-WEAKENED": "from cryptography.hazmat.primitives.ciphers.aead import AESGCM\nkey = AESGCM.generate_key(bit_length=128)\n",
               "QUANTUM-BROKEN": "from cryptography.hazmat.primitives.asymmetric import rsa\nrsa.generate_private_key(public_exponent=65537, key_size=4096)\n",
               "CLASSICALLY-BROKEN": "import hashlib\nhashlib.md5(b'x')\n"}
LEVELS = {"none": None, "quantum-weakened": 1, "quantum-broken": 2, "classically-broken": 3}
SEVERITY = {"OK": 0, "QUANTUM-WEAKENED": 1, "QUANTUM-BROKEN": 2, "CLASSICALLY-BROKEN": 3}


@pytest.mark.parametrize("worst", list(ONE_FINDING))
@pytest.mark.parametrize("level", list(LEVELS))
def test_fail_on_means_this_level_or_worse(tmp_path, worst, level):
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "app.py").write_text(ONE_FINDING[worst])
    code, _ = _run(["scan", str(tree), "--out", str(tmp_path / "out"), "--formats", "json", "--fail-on", level])
    risks = {f["risk"] for f in json.loads((tmp_path / "out" / "scan.json").read_text())["findings"]}
    assert max(SEVERITY[r] for r in risks) == SEVERITY[worst], risks  # the fixture really has this worst class
    expected = 1 if LEVELS[level] is not None and SEVERITY[worst] >= LEVELS[level] else 0
    assert code == expected


def test_sample_ci_workflow_gates_on_quantum_broken_and_says_so():
    workflow = (Path(__file__).resolve().parents[1] / "docs" / "ci" / "pq-inventory.yml").read_text()
    scan_step = workflow.split("- name: Scan", 1)[1].split("- name:", 1)[0]
    (run,) = [line for line in scan_step.splitlines() if line.strip().startswith("run:")]
    assert run.strip().endswith("--fail-on quantum-broken")
    assert "QUANTUM-BROKEN or worse" in scan_step


# --------------------------------------------- 6. a scan that read nothing fails every gate (exit 3)

@pytest.mark.parametrize("level", list(LEVELS))
def test_empty_scan_fails_every_gate_with_its_own_exit_code(tmp_path, level):
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "blob.bin").write_bytes(b"\x00\x01" * 10)  # skipped as binary: still nothing scanned
    code, console = _run(["scan", str(empty), "--out", str(tmp_path / "out"), "--fail-on", level])
    assert code == cli.EXIT_NOTHING_SCANNED == 3
    assert "nothing was scanned" in console


@pytest.mark.skipif(os.name == "nt", reason="symlinks")
def test_symlinked_root_is_not_a_silent_pass(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (real / "a.py").write_text("import hashlib\nhashlib.md5(b'x')\n")
    (tmp_path / "link").symlink_to(real, target_is_directory=True)
    code, console = _run(["scan", str(tmp_path / "link"), "--out", str(tmp_path / "out"), "--fail-on", "quantum-broken"])
    assert code == 3 and "symlink" in console


@pytest.mark.parametrize("option", ["--max-file-size", "--max-files"])
@pytest.mark.parametrize("value", ["0", "-1"])
def test_non_positive_limits_are_usage_errors(tmp_path, option, value):
    with pytest.raises(SystemExit) as error, contextlib.redirect_stderr(io.StringIO()):
        cli.main(["scan", str(tmp_path), "--out", str(tmp_path / "out"), option, value])
    assert error.value.code == 2


# --------------------------------------------- 7. table-driven cipher-string parsing

from pq_inventory import algorithms as alg  # noqa: E402

MOZILLA_INTERMEDIATE = ("ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:"
                        "ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:"
                        "DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:DHE-RSA-CHACHA20-POLY1305")


def _entries(value: str) -> list[tuple[str, list[str], bool]]:
    return [(e.token, e.algorithms, e.heuristic) for e in alg.cipher_entries(value)]


@pytest.mark.parametrize("suite,expected", [
    ("ECDHE-RSA-AES128-GCM-SHA256", ["ECDH", "RSA-SIGNATURE", "AES-128", "SHA-256"]),
    ("DHE-RSA-CHACHA20-POLY1305", ["DH", "RSA-SIGNATURE", "CHACHA20"]),
    ("ECDH-ECDSA-AES128-SHA", ["ECDH", "ECDSA", "AES-128", "HMAC-SHA1"]),
    ("EDH-DSS-DES-CBC3-SHA", ["DH", "DSA", "3DES", "HMAC-SHA1"]),
    ("AES256-SHA", ["RSA-KEX", "RSA-SIGNATURE", "AES-256", "HMAC-SHA1"]),
    ("RC4-MD5", ["RSA-KEX", "RSA-SIGNATURE", "RC4", "HMAC-MD5"]),
    ("NULL-SHA256", ["RSA-KEX", "RSA-SIGNATURE", "NULL-CIPHER", "SHA-256"]),
    ("ADH-AES128-SHA256", ["DH", "ANON-KEX", "AES-128", "SHA-256"]),
    ("AECDH-AES256-SHA", ["ECDH", "ANON-KEX", "AES-256", "HMAC-SHA1"]),
    ("PSK-AES128-GCM-SHA256", ["PSK", "AES-128", "SHA-256"]),
    ("ECDHE-PSK-CHACHA20-POLY1305", ["ECDH", "PSK", "CHACHA20"]),
    ("RSA-PSK-AES256-GCM-SHA384", ["RSA-KEX", "PSK", "AES-256", "SHA-384"]),
    ("EXP-RC4-MD5", ["EXPORT", "RSA-KEX", "RSA-SIGNATURE", "RC4", "HMAC-MD5"]),
    ("TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256", ["ECDH", "RSA-SIGNATURE", "AES-128", "SHA-256"]),
    ("TLS_RSA_WITH_3DES_EDE_CBC_SHA", ["RSA-KEX", "RSA-SIGNATURE", "3DES", "HMAC-SHA1"]),
    ("TLS_DH_anon_WITH_AES_128_CBC_SHA", ["DH", "ANON-KEX", "AES-128", "HMAC-SHA1"]),
    ("TLS_AES_256_GCM_SHA384", ["AES-256", "SHA-384"]),
])
def test_explicit_suites_decompose_by_table(suite, expected):
    assert alg.suite_algorithms(suite) == expected


def test_mozilla_intermediate_has_no_rsa_key_transport():
    entries = _entries(MOZILLA_INTERMEDIATE)
    assert len(entries) == 9 and not any(heuristic for _, _, heuristic in entries)
    assert all(algs[0] in ("ECDH", "DH") and "RSA-KEX" not in algs for _, algs, _ in entries)


@pytest.mark.parametrize("value,expected", [
    ("EECDH+AESGCM:EDH+AESGCM", [("EECDH+AESGCM", ["ECDH", "AES"], True), ("EDH+AESGCM", ["DH", "AES"], True)]),
    ("ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:!aNULL:!MD5:!DSS",
     [("ECDHE+AESGCM", ["ECDH", "AES"], True), ("ECDHE+CHACHA20", ["ECDH", "CHACHA20"], True), ("DHE+AESGCM", ["DH", "AES"], True)]),
    ("kEECDH+aRSA+AES256GCM", [("kEECDH+aRSA+AES256GCM", ["ECDH", "RSA-SIGNATURE", "AES-256"], True)]),
    ("HIGH:!aNULL:!MD5", []),  # nginx's default: class keywords depend on the OpenSSL build
    ("ALL:!ADH:!EXPORT:!SSLv2:RC4+RSA:+HIGH:+MEDIUM:+LOW", [("RC4+RSA", ["RC4", "RSA-KEX"], True)]),
    ("DEFAULT@SECLEVEL=2", []),
    ("aNULL", [("aNULL", ["ANON-KEX"], True)]),
    ("eNULL:EXPORT", [("eNULL", ["NULL-CIPHER"], True), ("EXPORT", ["EXPORT"], True)]),
    ("TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256,TLS_RSA_WITH_AES_128_CBC_SHA",
     [("TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256", ["ECDH", "ECDSA", "CHACHA20", "SHA-256"], False),
      ("TLS_RSA_WITH_AES_128_CBC_SHA", ["RSA-KEX", "RSA-SIGNATURE", "AES-128", "HMAC-SHA1"], False)]),
])
def test_real_cipher_strings(value, expected):
    assert _entries(value) == expected


@pytest.mark.parametrize("token,risk", [("NULL-SHA256", "CLASSICALLY-BROKEN"), ("ADH-AES128-SHA256", "CLASSICALLY-BROKEN"),
                                        ("EXP-RC4-MD5", "CLASSICALLY-BROKEN"), ("PSK-AES256-GCM-SHA384", "OK"),
                                        ("EECDH+AESGCM", "QUANTUM-BROKEN")])
def test_suite_risk_is_its_worst_component(token, risk):
    (entry,) = alg.cipher_entries(token)
    assert alg.worst(alg.classify(a)[0] for a in entry.algorithms) == risk


# --------------------------------------------- 8. unreadable keys and certificates: UNKNOWN with a reason, never "RSA assumed"

KEYS = PQC_FIXTURES.parent


def _odd_oid_certificate() -> bytes:
    """The committed ECDSA certificate with its key OID 1.2.840.10045.2.1 changed to the unassigned ...2.9."""
    der_cert = (KEYS / "ecdsa_cert.der").read_bytes()
    ec_oid = bytes.fromhex("06072a8648ce3d0201")
    assert der_cert.count(ec_oid) == 1
    return der_cert.replace(ec_oid, bytes.fromhex("06072a8648ce3d0209"))


def _pem(label: str, der_bytes: bytes) -> bytes:
    from pq_inventory.der import to_pem

    return to_pem(label, der_bytes)


@pytest.mark.parametrize("have_cryptography", [True, False])
def test_unreadable_certificates_are_unknown_with_a_reason(tmp_path, monkeypatch, have_cryptography):
    from pq_inventory import detect_keys
    from pq_inventory.scanner import scan

    if have_cryptography and not detect_keys.HAVE_CRYPTOGRAPHY:
        pytest.skip("needs the [pqc] extra (cryptography)")
    monkeypatch.setattr(detect_keys, "HAVE_CRYPTOGRAPHY", have_cryptography)
    (tmp_path / "odd_key.pem").write_bytes(_pem("CERTIFICATE", _odd_oid_certificate()))
    (tmp_path / "garbage.pem").write_bytes(b"-----BEGIN CERTIFICATE-----\nTm90IGEgY2VydGlmaWNhdGU=\n-----END CERTIFICATE-----\n")
    by_file = {f.file: f for f in scan(tmp_path).findings}
    odd, garbage = by_file["odd_key.pem"], by_file["garbage.pem"]
    assert (odd.algorithm, odd.category, odd.heuristic) == ("UNKNOWN", "certificate", True)
    assert "1.2.840.10045.2.9" in odd.detail
    assert garbage.algorithm == "UNKNOWN" and "could not be parsed" in garbage.detail
    for finding in (odd, garbage):
        assert "assumed" not in finding.detail and "RSA" not in finding.detail
        assert ("install" in finding.detail) == (not have_cryptography)


@pytest.mark.parametrize("have_cryptography", [True, False])
def test_corpus_never_reports_an_assumed_algorithm(monkeypatch, have_cryptography):
    from pq_inventory import detect_keys
    from pq_inventory.scanner import scan

    if have_cryptography and not detect_keys.HAVE_CRYPTOGRAPHY:
        pytest.skip("needs the [pqc] extra (cryptography)")
    monkeypatch.setattr(detect_keys, "HAVE_CRYPTOGRAPHY", have_cryptography)
    findings = scan(KEYS).findings
    assert findings and not [f.detail for f in findings if "assumed" in f.detail]
    by_file = {(f.file, f.rule.endswith("-hash")): f for f in findings}
    legacy = by_file[("legacy_sha1_cert.pem", False)]
    assert legacy.algorithm == "RSA-SIGNATURE"  # from the certificate's key OID, with or without cryptography
    assert by_file[("ecdsa_cert.der", False)].algorithm == "ECDSA"


def test_encrypted_private_key_type_is_unknown_not_rsa(tmp_path):
    serialization = pytest.importorskip("cryptography.hazmat.primitives.serialization")
    from cryptography.hazmat.primitives.asymmetric import ec

    from pq_inventory.scanner import scan

    key = ec.generate_private_key(ec.SECP256R1())  # an EC key: guessing "RSA" would be wrong
    (tmp_path / "enc.pem").write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                         serialization.BestAvailableEncryption(b"generated-at-test-time")))
    (finding,) = scan(tmp_path).findings
    assert (finding.algorithm, finding.category, finding.heuristic) == ("UNKNOWN", "private-key", True)
    assert "encrypted" in finding.detail


# --------------------------------------------- 10. exit codes: 1 only for a threshold, 2 for bad input, 4 for a crash

def _corpus_scan_json(tmp_path) -> Path:
    tree = tmp_path / "tree"
    tree.mkdir(exist_ok=True)
    (tree / "a.py").write_text("import hashlib\nhashlib.md5(b'x')\n")
    assert _run(["scan", str(tree), "--out", str(tmp_path / "s"), "--formats", "json"])[0] == 0
    return tmp_path / "s" / "scan.json"


@pytest.mark.parametrize("bad", ['{"root": "x"}', '[]', '{"findings": "nope", "root": "x", "generated_at": "t", "summary": {}}'])
def test_diff_with_a_malformed_scan_is_an_input_error(tmp_path, bad):
    good = _corpus_scan_json(tmp_path)
    (tmp_path / "bad.json").write_text(bad)
    code, console = _run(["diff", str(good), str(tmp_path / "bad.json"), "--out", str(tmp_path / "d")])
    assert code == 2 and "error" in console and "Traceback" not in console


@pytest.mark.parametrize("config", ['{"assumptions": {"z_years": "soon"}}', '{"systems": [{"name": "x", "migration_years": "two"}]}',
                                    '{"systems": "all"}'])
def test_bad_systems_config_is_an_input_error(tmp_path, config):
    _corpus_scan_json(tmp_path)
    (tmp_path / "systems.json").write_text(config)
    code, console = _run(["scan", str(tmp_path / "tree"), "--out", str(tmp_path / "o"), "--systems", str(tmp_path / "systems.json")])
    assert code == 2 and "error" in console


def test_out_that_is_a_file_is_an_input_error(tmp_path):
    _corpus_scan_json(tmp_path)
    (tmp_path / "not-a-dir").write_text("")
    code, console = _run(["scan", str(tmp_path / "tree"), "--out", str(tmp_path / "not-a-dir")])
    assert code == 2 and "not a directory" in console


def test_an_internal_error_is_exit_4_not_1(tmp_path, monkeypatch):
    _corpus_scan_json(tmp_path)
    monkeypatch.setattr(cli, "scan", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    code, console = _run(["scan", str(tmp_path / "tree"), "--out", str(tmp_path / "o")])
    assert code == cli.EXIT_INTERNAL == 4 and "boom" in console


# --------------------------------------------- 14. no private key is committed, not even an encrypted test key

def test_no_private_key_block_is_committed_in_fixtures_or_examples():
    root = Path(__file__).resolve().parents[1]
    marker = b"-----BEGIN " + b"(?:[A-Z]+ )*PRIVATE KEY-----"
    import re

    offenders = [p.relative_to(root).as_posix() for base in (root / "tests" / "fixtures", root / "examples")
                 for p in base.rglob("*") if p.is_file() and re.search(marker, p.read_bytes())]
    assert offenders == []
