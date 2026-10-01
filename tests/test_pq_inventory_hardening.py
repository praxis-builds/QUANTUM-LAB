"""Regression tests for docs/REVIEW-FINDINGS.md: each test failed before its fix."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

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
