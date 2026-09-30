"""Shared fixtures."""

from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def dashboard_process(tmp_path_factory):
    """The documented entry point, in a fresh interpreter, on an OS-assigned port.

    Request logs go to a file (not an unread pipe, which could fill up and stall the server).
    """
    log = (tmp_path_factory.mktemp("dashboard") / "server.log").open("w")
    process = subprocess.Popen(
        [sys.executable, "-m", "praxis_quantum_lab.dashboard_server", "--port", "0"],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=log, text=True,
    )
    port = None
    deadline = time.time() + 60
    while time.time() < deadline and port is None:
        line = process.stdout.readline()
        match = re.search(r"http://127\.0\.0\.1:(\d+)", line or "")
        if match:
            port = int(match.group(1))
        elif process.poll() is not None:
            break
    if port is None:
        process.kill()
        pytest.fail("dashboard did not start")
    try:
        yield process, port
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        log.close()
