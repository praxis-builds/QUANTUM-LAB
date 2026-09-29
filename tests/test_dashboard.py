"""Local dashboard boundaries and scientific responses, without browser tooling."""

from __future__ import annotations

from http.client import HTTPConnection
import json
from threading import Thread

import numpy as np
import pytest

from praxis_quantum_lab import dashboard_server as dashboard


def bell_request(**changes):
    return {
        "channel": "bit_flip",
        "strength": 0.2,
        "shots": 256,
        "seed": 42,
        "step": 3,
        **changes,
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"channel": "unknown"},
        {"strength": -0.01},
        {"strength": 1.01},
        {"strength": float("nan")},
        {"strength": float("inf")},
        {"strength": True},
        {"strength": "0.2"},
        {"shots": 0},
        {"shots": 8193},
        {"shots": 128.0},
        {"shots": True},
        {"seed": -1},
        {"seed": 2147483648},
        {"seed": False},
        {"step": -1},
        {"step": 4},
        {"step": 1.0},
        {"step": True},
        {"unexpected": "field"},
    ],
)
def test_bell_request_rejects_invalid_values(changes) -> None:
    with pytest.raises(ValueError):
        dashboard.parse_bell_request(bell_request(**changes))


def test_bell_request_requires_object_and_complete_fields() -> None:
    for value in (None, [], "request", {}, {"shots": 128}):
        with pytest.raises(ValueError):
            dashboard.parse_bell_request(value)
    for changes in (
        {"strength": 0, "shots": 1, "seed": 0, "step": 0},
        {"strength": 1, "shots": 8192, "seed": 2147483647, "step": 3},
    ):
        dashboard.parse_bell_request(bell_request(**changes))


@pytest.mark.parametrize(
    "changes,expected_probabilities,expected_fidelity",
    [
        ({"step": 0}, [1.0, 0.0, 0.0, 0.0], 0.5),
        ({"step": 1}, [0.5, 0.5, 0.0, 0.0], 0.25),
        ({"step": 2}, [0.5, 0.0, 0.0, 0.5], 1.0),
        ({"strength": 0.0}, [0.5, 0.0, 0.0, 0.5], 1.0),
        ({"strength": 1.0}, [0.0, 0.5, 0.5, 0.0], 0.0),
        (
            {"channel": "amplitude_damping", "strength": 1.0},
            [0.5, 0.0, 0.5, 0.0],
            0.25,
        ),
        (
            {"channel": "depolarizing", "strength": 1.0},
            [0.25, 0.25, 0.25, 0.25],
            0.25,
        ),
    ],
)
def test_bell_stages_and_channel_limits_agree_with_aer(
    changes, expected_probabilities, expected_fidelity
) -> None:
    request = bell_request(**changes)
    response = dashboard.simulate_bell(request)
    assert response["step"] == request["step"]
    assert response["basis"] == ["00", "01", "10", "11"]
    assert len(response["applied_gates"]) == request["step"]
    assert response["parameter_convention"]
    assert response["stage"]
    for key in ("custom_probabilities", "aer_probabilities"):
        assert np.allclose(
            [response[key][basis] for basis in response["basis"]],
            expected_probabilities,
            atol=1e-10,
        )
    for key in ("custom_density_matrix", "aer_density_matrix"):
        encoded = np.asarray(response[key], dtype=float)
        assert encoded.shape == (4, 4, 2)
        matrix = encoded[:, :, 0] + 1j * encoded[:, :, 1]
        assert np.allclose(matrix, matrix.conj().T, atol=1e-10)
        assert np.trace(matrix) == pytest.approx(1.0)
        assert np.linalg.eigvalsh(matrix).min() >= -1e-10
    assert response["custom_bell_fidelity"] == pytest.approx(expected_fidelity)
    assert response["aer_bell_fidelity"] == pytest.approx(expected_fidelity)
    assert response["frobenius_error"] < 1e-10
    assert sum(response["counts"].values()) == request["shots"]
    assert set(response["counts"]) <= set(response["basis"])
    assert all(type(count) is int and count >= 0 for count in response["counts"].values())


def test_bell_counts_are_reproducible_with_fixed_seed() -> None:
    request = bell_request(channel="amplitude_damping", strength=0.37, shots=512)
    first = dashboard.simulate_bell(request)
    second = dashboard.simulate_bell(request)
    assert first["counts"] == second["counts"]
    assert first["custom_density_matrix"] == second["custom_density_matrix"]
    assert first["aer_density_matrix"] == second["aer_density_matrix"]


def test_saved_kernel_results_load_real_existing_data() -> None:
    result = dashboard.load_kernel_results()
    assert result["metadata"]["sample_size"] == 40
    assert result["metadata"]["train_size"] == 28
    assert result["metadata"]["test_size"] == 12
    assert [budget["shots"] for budget in result["shot_budgets"]] == [128, 512, 2048]
    for budget in result["shot_budgets"]:
        assert len(budget["replicates"]) == 5
        for replicate in budget["replicates"]:
            for key in ("raw_sampled_kernel_matrix", "psd_repaired_kernel_matrix"):
                assert np.asarray(replicate[key]).shape == (40, 40)
            assert replicate["evaluation_scope"]["repair_uses_test_labels"] is False
            assert "transductive" in replicate["evaluation_scope"]["repaired"]


def test_result_loading_rejects_missing_malformed_and_oversized_files(
    monkeypatch, tmp_path
) -> None:
    result_path = tmp_path / "approved-result.json"
    monkeypatch.setattr(dashboard, "RESULT_PATH", result_path)
    with pytest.raises((OSError, ValueError)):
        dashboard.load_kernel_results()
    for content in ("not json", "{}", "[]", '{"metadata": NaN}'):
        result_path.write_text(content, encoding="utf-8")
        with pytest.raises(ValueError):
            dashboard.load_kernel_results()
    monkeypatch.setattr(dashboard, "MAX_RESULT_BYTES", 4)
    result_path.write_text('{"oversized": true}', encoding="utf-8")
    with pytest.raises(ValueError):
        dashboard.load_kernel_results()


@pytest.fixture(scope="module")
def local_server():
    server = dashboard.make_server(port=0)
    assert server.server_address[0] == "127.0.0.1"
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive()


def http_request(server, method, path, body=None, headers=None):
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=15)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def test_get_routes_serve_only_dashboard_assets_and_saved_data(local_server, monkeypatch) -> None:
    def unexpected_simulation(*args, **kwargs):
        pytest.fail("GET routes must never launch a simulation")

    monkeypatch.setattr(dashboard, "simulate_bell", unexpected_simulation)
    for path, content_type in (
        ("/", "text/html"),
        ("/style.css", "text/css"),
        ("/app.js", "javascript"),
        ("/api/kernel-results", "application/json"),
    ):
        status, headers, body = http_request(local_server, "GET", path)
        assert status == 200
        assert content_type in headers["Content-Type"]
        assert body
    status, _, body = http_request(local_server, "GET", "/api/kernel-results")
    assert status == 200
    assert json.loads(body)["metadata"]["sample_size"] == 40


@pytest.mark.parametrize(
    "path",
    [
        "/../pyproject.toml",
        "/%2e%2e/pyproject.toml",
        "/%252e%252e/pyproject.toml",
        "/results/finite_shot_kernel_psd_repair.json",
        "/api/kernel-results?file=../../pyproject.toml",
        "/?path=pyproject.toml",
        "/unknown",
    ],
)
def test_unapproved_routes_and_traversal_are_rejected(local_server, path) -> None:
    status, _, body = http_request(local_server, "GET", path)
    assert status in (400, 404)
    assert "error" in json.loads(body)


@pytest.mark.parametrize(
    "headers",
    [
        {"Host": "example.com"},
        {"Host": "127.0.0.1.evil.example"},
        {"Origin": "https://example.com"},
        {"Origin": "null"},
    ],
)
def test_nonlocal_host_and_foreign_origin_are_rejected(local_server, headers) -> None:
    status, _, body = http_request(local_server, "GET", "/api/kernel-results", headers=headers)
    assert status == 403
    assert "error" in json.loads(body)


@pytest.mark.parametrize(
    "body,content_type,expected_status",
    [
        ("x" * 1025, "application/json", 413),
        ("{}", "text/plain", 415),
        ("not json", "application/json", 400),
        ("[]", "application/json", 400),
        ("{}", "application/json", 400),
        ('{"channel":"bit_flip","channel":"depolarizing"}', "application/json", 400),
        ('{"strength":NaN}', "application/json", 400),
    ],
)
def test_invalid_api_requests_are_bounded(local_server, body, content_type, expected_status) -> None:
    status, _, payload = http_request(
        local_server,
        "POST",
        "/api/bell",
        body,
        {"Content-Type": content_type},
    )
    assert status == expected_status
    assert "error" in json.loads(payload)


def test_api_returns_real_bell_simulation(local_server) -> None:
    status, headers, body = http_request(
        local_server,
        "POST",
        "/api/bell",
        json.dumps(bell_request(channel="amplitude_damping", strength=1.0)),
        {"Content-Type": "application/json"},
    )
    assert status == 200
    assert "application/json" in headers["Content-Type"]
    result = json.loads(body)
    assert result["custom_probabilities"]["10"] == pytest.approx(0.5)
    assert result["aer_bell_fidelity"] == pytest.approx(0.25)
    assert sum(result["counts"].values()) == 256


def test_unsupported_method_returns_error(local_server) -> None:
    status, _, body = http_request(local_server, "PUT", "/api/bell", "{}")
    assert status == 405
    assert "error" in json.loads(body)
