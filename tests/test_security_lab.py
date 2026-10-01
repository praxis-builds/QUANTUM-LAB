"""Security Lab routes: strict validation, results that match the lessons, HTTP behaviour."""

from __future__ import annotations

import json
import math
from http.client import HTTPConnection
from threading import Thread

import pytest

from praxis_quantum_lab import dashboard_server as dashboard
from praxis_quantum_lab import security_lab as lab

BB84 = {"qubits": 4000, "noise": 0.0, "sample": 200, "eve": False, "seed": 7}
RSA = {"n": 21, "seed": 3}
GROVER = {"key": 11, "iterations": 3, "pairs": 2, "seed": 5}


@pytest.mark.parametrize("payload", [
    None, [], {}, {**BB84, "extra": 1}, {k: v for k, v in BB84.items() if k != "eve"},
    {**BB84, "qubits": 199}, {**BB84, "qubits": 20001}, {**BB84, "qubits": True}, {**BB84, "qubits": 4000.0},
    {**BB84, "noise": -0.01}, {**BB84, "noise": 0.21}, {**BB84, "noise": "0.1"}, {**BB84, "noise": float("nan")},
    {**BB84, "noise": True}, {**BB84, "sample": 9}, {**BB84, "sample": 2001}, {**BB84, "eve": 1}, {**BB84, "eve": "true"},
    {**BB84, "seed": -1}, {**BB84, "seed": 2**31},
])
def test_bb84_validation_rejects(payload):
    with pytest.raises(ValueError):
        lab.parse_bb84_request(payload)


@pytest.mark.parametrize("payload", [
    {**RSA, "n": 33}, {**RSA, "n": 15.0}, {**RSA, "n": True}, {**RSA, "seed": -1}, {"n": 21}, {**RSA, "x": 1},
])
def test_rsa_validation_rejects(payload):
    with pytest.raises(ValueError):
        lab.parse_rsa_request(payload)


@pytest.mark.parametrize("payload", [
    {**GROVER, "key": 16}, {**GROVER, "key": -1}, {**GROVER, "iterations": 9}, {**GROVER, "iterations": True},
    {**GROVER, "pairs": 3}, {**GROVER, "pairs": 2.0}, {**GROVER, "seed": 2**31}, {"key": 1, "iterations": 1, "pairs": 1},
])
def test_grover_validation_rejects(payload):
    with pytest.raises(ValueError):
        lab.parse_grover_request(payload)


def test_bb84_results_match_the_lessons():
    clean = lab.simulate_bb84(lab.parse_bb84_request(BB84))
    assert clean["qber_true"] == 0 and clean["status"] == "key" and clean["keys_equal"] and clean["key_bits"] > 0
    assert clean["sifted"] == pytest.approx(2000, abs=150)
    eve = lab.simulate_bb84(lab.parse_bb84_request({**BB84, "eve": True}))
    assert eve["qber_true"] == pytest.approx(0.25, abs=4 * math.sqrt(0.25 * 0.75 / eve["sifted"]))
    assert eve["status"].startswith("ABORT") and eve["key_bits"] == 0
    assert eve["p_detect_formula"] == pytest.approx(1 - 0.75**200)
    assert eve["eve_knows_fraction"] == pytest.approx(0.5, abs=0.05)
    tiny = lab.simulate_bb84(lab.parse_bb84_request({**BB84, "qubits": 200, "sample": 2000}))
    assert tiny["sample_clipped"] and tiny["sample"] <= tiny["sifted"] // 2


@pytest.mark.parametrize("n,factors,message", [(15, [3, 5], "HELLO"), (21, [3, 7], "HIDE")])
def test_rsa_break_recovers_the_message(n, factors, message):
    result = lab.simulate_rsa(lab.parse_rsa_request({"n": n, "seed": 3}))
    assert result["status"] == "key recovered" and result["factors"] == factors and result["decrypted"] == message
    assert pow(result["e"] * result["d"], 1, result["phi"]) == 1
    assert result["attempts"][-1]["candidate"] == result["period"]
    assert all(peak["probability"] > 1e-3 for peak in result["peaks"])


def test_grover_success_matches_theory_and_shows_over_rotation():
    best = lab.simulate_grover(lab.parse_grover_request(GROVER))
    assert best["matching_keys"] == ["1011"] and best["optimal_iterations"] == 3
    assert best["measured_secret"] == pytest.approx(best["curve"][3]["p_secret"], abs=0.04)
    over = lab.simulate_grover(lab.parse_grover_request({**GROVER, "iterations": 6}))
    assert over["measured_secret"] < best["measured_secret"] - 0.3  # over-rotation
    one_pair = lab.simulate_grover(lab.parse_grover_request({**GROVER, "pairs": 1, "iterations": 2}))
    assert len(one_pair["matching_keys"]) == 2 and one_pair["measured_secret"] == pytest.approx(0.5, abs=0.06)


# ----------------------------------------------------------------------------- HTTP

@pytest.fixture(scope="module")
def server():
    srv = dashboard.make_server(port=0)
    thread = Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield srv
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=5)


def post(server, path, body, headers=None):
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=60)
    try:
        payload = body if isinstance(body, str) else json.dumps(body)
        connection.request("POST", path, body=payload, headers=headers or {"Content-Type": "application/json"})
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


@pytest.mark.parametrize("path,body,key", [
    ("/api/security/bb84", BB84, "qber_true"), ("/api/security/rsa", RSA, "factors"), ("/api/security/grover", GROVER, "curve"),
])
def test_http_routes_happy_path(server, path, body, key):
    status, result = post(server, path, body)
    assert status == 200 and key in result
    name = path.rsplit("/", 1)[-1]
    direct = getattr(lab, f"simulate_{name}")(getattr(lab, f"parse_{name}_request")(body))
    assert result == json.loads(json.dumps(direct))  # the route returns exactly what the checked function computes


@pytest.mark.parametrize("path", ["/api/security/bb84", "/api/security/rsa", "/api/security/grover"])
def test_http_routes_reject_bad_bodies(server, path):
    assert post(server, path, "x" * 257)[0] == 413
    assert post(server, path, {"bogus": 1})[0] == 400
    assert post(server, path, "{}", {"Content-Type": "text/plain"})[0] == 415
    assert post(server, path, '{"n":21,"n":15,"seed":1}')[0] == 400
    assert post(server, path, BB84 | {"qubits": 1e400} if path.endswith("bb84") else "NaN")[0] == 400


def test_http_security_routes_respect_the_simulation_lock(server):
    assert server.simulation_lock.acquire(blocking=False)
    try:
        assert post(server, "/api/security/rsa", RSA)[0] == 429
    finally:
        server.simulation_lock.release()


def test_security_script_is_served(server):
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=10)
    try:
        connection.request("GET", "/security.js")
        response = connection.getresponse()
        assert response.status == 200 and "javascript" in response.getheader("Content-Type")
        assert b"SecurityCore" in response.read()
    finally:
        connection.close()


# ------------------------------------------------- review #11: no lessons/ directory (e.g. a wheel install)

def test_dashboard_starts_without_lessons_and_the_security_lab_degrades(monkeypatch, tmp_path):
    monkeypatch.setattr(lab, "LESSONS_DIR", tmp_path / "no-lessons")
    monkeypatch.setattr(lab, "_modules", {})
    monkeypatch.setattr(lab, "_unavailable", None)
    srv = dashboard.make_server(port=0)  # used to raise FileNotFoundError: every tab went down
    thread = Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        connection = HTTPConnection("127.0.0.1", srv.server_port, timeout=30)
        connection.request("GET", "/api/security/status")
        response = connection.getresponse()
        status = json.loads(response.read())
        assert response.status == 200 and status["available"] is False and "lessons" in status["reason"]
        connection.request("GET", "/api/circuit-presets")  # the other tabs still work
        response = connection.getresponse()
        assert response.status == 200 and json.loads(response.read())
        connection.close()
        code, body = post(srv, "/api/security/rsa", RSA)
        assert code == 503 and "lessons" in body["error"]
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=5)


def test_security_status_reports_available_with_a_checkout(server):
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=10)
    try:
        connection.request("GET", "/api/security/status")
        response = connection.getresponse()
        assert response.status == 200 and json.loads(response.read()) == {"available": True, "reason": None}
    finally:
        connection.close()


def test_security_tab_shows_the_unavailable_reason_and_disables_simulations():
    assets = dashboard.ASSET_ROOT
    assert 'id="security-unavailable"' in (assets / "index.html").read_text()
    script = (assets / "security.js").read_text()
    assert '"/api/security/status"' in script and '["bb84-run", "rsa-run", "grover-run"]' in script
