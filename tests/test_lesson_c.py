"""The C companion (lessons/c): builds and runs against liboqs when present, skips cleanly otherwise."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

C_DIR = Path(__file__).resolve().parents[1] / "lessons" / "c"
OQS_PREFIX = Path.home() / "_oqs"
HAVE_LIBOQS = (OQS_PREFIX / "include" / "oqs" / "oqs.h").exists() and any((OQS_PREFIX / "lib").glob("liboqs.so*"))
HAVE_TOOLS = shutil.which("make") is not None and shutil.which("cc") is not None


@pytest.mark.skipif(not (HAVE_LIBOQS and HAVE_TOOLS), reason="needs make, cc and liboqs in ~/_oqs (docs/DECISIONS.md D1)")
def test_c_demo_builds_and_reports_agreement(tmp_path):
    run = subprocess.run(["make", "-C", str(C_DIR), "run", f"BUILD={tmp_path}"], capture_output=True, text=True, timeout=180)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "public key 1184 bytes, secret key 2400 bytes, ciphertext 1088 bytes, shared secret 32 bytes" in run.stdout
    assert "shared secrets agree: yes" in run.stdout and "different secret: yes" in run.stdout


@pytest.mark.skipif(not HAVE_TOOLS, reason="needs make")
def test_c_demo_skips_cleanly_without_liboqs(tmp_path):
    run = subprocess.run(["make", "-C", str(C_DIR), "run", f"OQS_PREFIX={tmp_path}", f"BUILD={tmp_path / 'b'}"],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == 0 and "SKIP: liboqs not found" in run.stdout
    assert not (tmp_path / "b").exists()
