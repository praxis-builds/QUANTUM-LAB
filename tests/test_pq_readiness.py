"""pq_readiness: sections, no secrets, determinism, escaping, input errors and the committed demo."""

from __future__ import annotations

import contextlib
import copy
import html
import io
import json
import re
from pathlib import Path

import pytest

from pq_inventory import detect_keys
from pq_readiness import build, cli, render

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "readiness-demo"
SAMPLE = ROOT / "examples" / "pq-tls" / "sample-results.json"
WAREHOUSE = ROOT / "examples" / "warehouse-demo"
NOTE = "Northwind is fictional, so these are four real public websites checked on 2026-10-05 as stand-ins, not Northwind's own."
DEMO_ARGS = ["report", "--client", "Northwind Warehouse (fictional)", "--code", "examples/warehouse-demo/before",
             "--systems", "examples/warehouse-demo/systems.json", "--sites-json", "examples/pq-tls/sample-results.json",
             "--sites-note", NOTE, "--date", "2026-10-05"]
SECTIONS = {"summary": "Executive summary", "websites": "Websites: key exchange", "findings": "Code and configuration findings",
            "timeline": "Migration timeline (Mosca)", "actions": "Prioritised actions", "method": "Methodology and honest limits"}
needs_cryptography = pytest.mark.skipif(not detect_keys.HAVE_CRYPTOGRAPHY, reason="needs the [pqc] extra (cryptography)")


def _run(argv, cwd=None):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(argv)
    return code, out.getvalue() + err.getvalue()


def _demo(tmp_path, monkeypatch) -> tuple[str, dict]:
    monkeypatch.chdir(ROOT)
    assert _run(DEMO_ARGS + ["--out", str(tmp_path / "r")])[0] == 0
    return (tmp_path / "r" / "readiness-report.html").read_text(), json.loads((tmp_path / "r" / "readiness-report.json").read_text())


def test_every_section_is_present_with_content(tmp_path, monkeypatch):
    page, data = _demo(tmp_path, monkeypatch)
    for section_id, heading in SECTIONS.items():
        assert f'id="{section_id}"' in page and heading in page, section_id
    assert page.count("<tr>") > 40  # websites, risk table, findings, Mosca table
    assert "<svg" in page and "z = 9 years (2035, assumed)" in page
    for word in ("Now", "Next (12–24 months)", "Later (as the ecosystem allows)"):
        assert f"<h3>{word}</h3>" in page
    assert data["versions"]["pq_inventory"] and data["versions"]["pq_tls"] and data["date"] == "2026-10-05"
    assert [row["key_exchange"] for row in data["websites"]["rows"]] == ["PQ-HYBRID", "PQ-HYBRID", "PQ-HYBRID", "CLASSICAL"]
    assert html.escape(NOTE) in page and "not a live check" in page


def test_print_stylesheet_and_self_contained(tmp_path, monkeypatch):
    page, _ = _demo(tmp_path, monkeypatch)
    assert "@media print" in page and "@page" in page
    assert "<script" not in page.lower()
    assert not re.search(r"(src|href)\s*=\s*[\"']?(https?:)?//", page)  # no external assets


def test_same_inputs_give_the_same_bytes(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    for name in ("a", "b"):
        assert _run(DEMO_ARGS + ["--out", str(tmp_path / name)])[0] == 0
    for file in ("readiness-report.html", "readiness-report.json"):
        assert (tmp_path / "a" / file).read_bytes() == (tmp_path / "b" / file).read_bytes()


@needs_cryptography
def test_committed_demo_is_what_the_documented_command_writes(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    assert _run(DEMO_ARGS + ["--out", str(tmp_path / "r")])[0] == 0
    for file in ("readiness-report.html", "readiness-report.json"):
        assert (tmp_path / "r" / file).read_bytes() == (DEMO / file).read_bytes(), \
            f"{file} is stale: regenerate with the command in examples/readiness-demo/README.md"


SECRETS = ["Kx9!pq", "Tr0ub4dor&3", "Sup3rS3cretKey!!24bytes!", "00112233445566778899aabbccddeeff", "A" * 64]


def test_no_source_text_or_key_material_reaches_the_report(tmp_path):
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "app.py").write_text("from Crypto.Cipher import DES3\n"
                                 f"cipher = DES3.new(b\"{SECRETS[2]}\", DES3.MODE_CBC)  # pw {SECRETS[0]}\n"
                                 f"key = bytes.fromhex(\"{SECRETS[3]}\")\nimport hashlib; hashlib.md5(b\"{SECRETS[4]}\")\n")
    (tree / "partner.properties").write_text(f"as2.encryption=3des  # partner password: {SECRETS[1]}\n")
    serialization = pytest.importorskip("cryptography.hazmat.primitives.serialization")
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)  # generated at test time (D9)
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    (tree / "server.key").write_bytes(pem)
    code, console = _run(["report", "--client", "Test", "--code", str(tree), "--out", str(tmp_path / "r"), "--date", "2026-10-05"])
    assert code == 0
    material = [line for line in pem.decode().splitlines() if "-----" not in line]
    for name in ("readiness-report.html", "readiness-report.json"):
        text = (tmp_path / "r" / name).read_text()
        for secret in SECRETS + material:
            assert secret not in text, f"{secret[:12]!r} leaked into {name}"
        assert "[redacted]" not in text and "evidence" not in text
    data = json.loads((tmp_path / "r" / "readiness-report.json").read_text())
    algorithms = {f["algorithm"] for findings in data["code"]["findings_by_risk"].values() for f in findings}
    assert {"3DES", "MD5", "RSA"} <= algorithms  # the findings themselves are there


def test_everything_from_the_inputs_is_escaped(tmp_path):
    hostile = '<script>alert("x")</script>'
    results = json.loads(SAMPLE.read_text())
    poisoned = copy.deepcopy(results)
    poisoned["hosts"][0]["host"] = "<img src=x onerror=alert(1)>"
    poisoned["hosts"][0]["verdict"]["recommendation"] = hostile
    poisoned["hosts"][0]["connection"]["certificate_key"] = "</td><b>bold</b>"
    (tmp_path / "sites.json").write_text(json.dumps(poisoned))
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "x<b>y.py").write_text("import hashlib\nhashlib.md5(b'')\n")
    code, _ = _run(["report", "--client", hostile, "--code", str(tree), "--sites-json", str(tmp_path / "sites.json"),
                    "--sites-note", "<i>note</i>", "--out", str(tmp_path / "r"), "--date", "2026-10-05"])
    assert code == 0
    page = (tmp_path / "r" / "readiness-report.html").read_text()
    for raw in ("<script", "<img", "<b>bold", "</td><b>", "<i>note", "x<b>y"):
        assert raw not in page, raw
    assert "&lt;script&gt;" in page and "&lt;img src=x" in page


@pytest.mark.parametrize("argv,message", [
    (["--client", "X", "--out", "o"], "give --code, --sites or --sites-json"),
    (["--client", "X", "--code", "missing-dir", "--out", "o"], "does not exist"),
    (["--client", " ", "--code", "examples/warehouse-demo/before", "--out", "o"], "must not be empty"),
    (["--client", "X", "--sites-json", "pyproject.toml", "--out", "o"], "pq_tls results"),
])
def test_input_errors_exit_2(tmp_path, monkeypatch, argv, message):
    monkeypatch.chdir(ROOT)
    argv = [a if a != "o" else str(tmp_path / "o") for a in argv]
    code, console = _run(["report", *argv])
    assert code == 2 and message in console


def test_bad_site_results_are_rejected(tmp_path):
    for bad in ({"tool": "pq_tls", "hosts": [{"host": "a", "verdict": {"key_exchange": "MAYBE"}}]}, {"tool": "x"}, []):
        (tmp_path / "s.json").write_text(json.dumps(bad))
        with pytest.raises(build.InputError):
            build.load_site_results(tmp_path / "s.json")


def test_live_sites_go_through_pq_tls(tmp_path, monkeypatch):
    calls = []

    def fake_run(hosts, port=443, **kwargs):
        calls.append(hosts)
        results = json.loads(SAMPLE.read_text())
        results["hosts"] = [dict(results["hosts"][0], host=h) for h in hosts]
        return results

    import pq_tls.probe

    monkeypatch.setattr(pq_tls.probe, "run", fake_run)
    code, _ = _run(["report", "--client", "Live", "--sites", "a.example", "b.example", "a.example", "--out", str(tmp_path / "r"),
                    "--date", "2026-10-05"])
    assert code == 0 and calls == [["a.example", "b.example"]]
    data = json.loads((tmp_path / "r" / "readiness-report.json").read_text())
    assert data["websites"]["source"].startswith("checked live on") and data["code"] is None
    with pytest.raises(SystemExit) as error, contextlib.redirect_stderr(io.StringIO()):
        cli.main(["report", "--client", "X", "--sites", "10.0.0.0/24", "--out", str(tmp_path / "r")])
    assert error.value.code == 2


def test_actions_are_ordered_now_next_later(tmp_path, monkeypatch):
    _, data = _demo(tmp_path, monkeypatch)
    now = [a["what"] for a in data["actions"]["now"]]
    assert any("weak today" in what for what in now) and any("start the post-quantum migration now" in what for what in now)
    assert any("github.com: enable hybrid key exchange" in a["what"] for a in data["actions"]["next"])
    assert any("Certificates" in a["what"] for a in data["actions"]["later"])
    assert render.render(data) == (DEMO / "readiness-report.html").read_text() or not detect_keys.HAVE_CRYPTOGRAPHY
