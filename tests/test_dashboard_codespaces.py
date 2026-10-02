"""Opt-in GitHub Codespaces mode: exactly one extra forwarded host, nothing else."""

from __future__ import annotations

import json
from http.client import HTTPConnection
from threading import Thread

import pytest

from praxis_quantum_lab import dashboard_server as dashboard

ENV = {
    "CODESPACES": "true",
    "CODESPACE_NAME": "praxis-lab-x7q9",
    "GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN": "app.github.dev",
}
FORWARDED = "praxis-lab-x7q9-8765.app.github.dev"


def test_codespaces_host_is_built_from_the_environment() -> None:
    assert dashboard.codespaces_host(8765, ENV) == FORWARDED


@pytest.mark.parametrize(
    "changes",
    [
        {"CODESPACES": "false"},
        {"CODESPACES": ""},
        {"CODESPACE_NAME": ""},
        {"CODESPACE_NAME": "evil.example.com"},
        {"CODESPACE_NAME": "Name-With-Caps"},
        {"CODESPACE_NAME": "a/b"},
        {"GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN": ""},
        {"GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN": "localhost"},
        {"GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN": "app.github.dev:443"},
        {"GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN": "app.github.dev/x"},
    ],
)
def test_codespaces_host_refuses_outside_codespaces_or_odd_values(changes) -> None:
    with pytest.raises(ValueError):
        dashboard.codespaces_host(8765, {**ENV, **changes})


@pytest.mark.parametrize("port", [0, -1, 65536, True, 8765.0])
def test_codespaces_host_needs_a_fixed_port(port) -> None:
    with pytest.raises(ValueError):
        dashboard.codespaces_host(port, ENV)


def _serve(forwarded_host):
    server = dashboard.make_server(port=0, forwarded_host=forwarded_host)
    assert server.server_address[0] == "127.0.0.1"  # still loopback only
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _stop(server, thread) -> None:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def _get(server, headers, path="/api/kernel-results"):
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=15)
    try:
        connection.putrequest("GET", path, skip_host=True)
        for key, value in headers.items():
            connection.putheader(key, value)
        connection.endheaders()
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


@pytest.fixture
def codespace_server():
    server, thread = _serve(FORWARDED)
    try:
        yield server
    finally:
        _stop(server, thread)


def test_forwarded_host_and_its_https_origin_are_accepted(codespace_server) -> None:
    status, _ = _get(codespace_server, {"Host": FORWARDED, "Origin": f"https://{FORWARDED}"})
    assert status == 200
    status, _ = _get(codespace_server, {"Host": FORWARDED})
    assert status == 200


def test_forwarder_loopback_host_with_forwarded_origin_is_accepted(codespace_server) -> None:
    # The Codespaces port forwarder may connect as localhost:<port> while the browser's
    # Origin is the forwarded https URL (seen in a real codespace: the forwarded Host alone was refused).
    loopback = f"localhost:{codespace_server.server_port}"
    assert _get(codespace_server, {"Host": loopback})[0] == 200
    assert _get(codespace_server, {"Host": loopback, "Origin": f"https://{FORWARDED}"})[0] == 200
    assert _get(codespace_server, {"Host": loopback, "X-Forwarded-Host": FORWARDED})[0] == 200


def test_local_host_still_works_in_codespaces_mode(codespace_server) -> None:
    local = f"127.0.0.1:{codespace_server.server_port}"
    assert _get(codespace_server, {"Host": local, "Origin": f"http://{local}"})[0] == 200


@pytest.mark.parametrize(
    "headers",
    [
        {"Host": "other-codespace-8765.app.github.dev"},
        {"Host": f"{FORWARDED}.evil.example"},
        {"Host": "example.com"},
        {"Host": FORWARDED, "Origin": f"http://{FORWARDED}"},  # wrong scheme
        {"Host": FORWARDED, "Origin": "https://example.com"},
        {"Host": FORWARDED, "Sec-Fetch-Site": "cross-site"},
        {"Host": FORWARDED, "X-Forwarded-Host": "evil.example"},
        {"Host": FORWARDED, "Origin": "https://other-codespace-8765.app.github.dev"},
        {"Host": "localhost:1"},
    ],
)
def test_codespaces_mode_rejects_everything_else(codespace_server, headers) -> None:
    status, body = _get(codespace_server, headers)
    assert status == 403
    assert "error" in json.loads(body)


def test_default_server_rejects_the_forwarded_host() -> None:
    server, thread = _serve(None)
    try:
        assert _get(server, {"Host": FORWARDED})[0] == 403
        assert _get(server, {"Host": f"localhost:{server.server_port}"})[0] == 403
        local = f"127.0.0.1:{server.server_port}"
        assert _get(server, {"Host": local, "X-Forwarded-Host": FORWARDED})[0] == 403
        assert _get(server, {"Host": local, "Origin": f"https://{FORWARDED}"})[0] == 403
    finally:
        _stop(server, thread)
