"""The dashboard as users start it: the documented entry point in a fresh interpreter."""

from __future__ import annotations

import json
from http.client import HTTPConnection

from praxis_quantum_lab import circuit_playground as cp


def post(port, path, payload):
    connection = HTTPConnection("127.0.0.1", port, timeout=60)
    try:
        connection.request("POST", path, json.dumps(payload), {"Content-Type": "application/json"})
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def test_repeated_simulations_do_not_crash_the_server(dashboard_process):
    """Regression: the original server segfaulted on its second simulation request.

    Qiskit was imported lazily inside a request thread; the next request crashed inside
    Qiskit's native circuit code. The server now loads Qiskit and Aer at start-up.
    """
    process, port = dashboard_process
    bell = {"channel": "bit_flip", "strength": 0.2, "shots": 64, "seed": 1, "step": 3}
    for step in (3, 2, 3):
        status, _ = post(port, "/api/bell", {**bell, "step": step})
        assert status == 200
        assert process.poll() is None
    for preset in cp.PRESETS:
        status, result = post(port, "/api/circuit", {"qubits": preset["qubits"], "gates": preset["gates"], "shots": 64, "seed": 2})
        assert status == 200, preset["id"]
        assert sum(result["counts"].values()) == 64
        assert process.poll() is None
