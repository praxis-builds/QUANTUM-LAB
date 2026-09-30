"""Kernel Observatory repair comparison: read-only, consistent with saved results, fails closed."""

from __future__ import annotations

import json
from http.client import HTTPConnection
from threading import Thread

import numpy as np
import pytest

from praxis_quantum_lab import dashboard_server as dashboard
from praxis_quantum_lab import observatory

SAVED_DISTANCES = json.loads(dashboard.DISTANCES_PATH.read_text())


@pytest.fixture(scope="module")
def report():
    return observatory.build_kernel_repairs(dashboard.RESULT_PATH, dashboard.DISTANCES_PATH)


def test_fifteen_entries_with_psd_unit_diagonal_higham(report):
    assert len(report["entries"]) == 15
    assert sorted({e["shots"] for e in report["entries"]}) == [128, 512, 2048]
    for entry in report["entries"]:
        higham = np.asarray(entry["higham_matrix"])
        assert higham.shape == (40, 40)
        assert np.linalg.eigvalsh(higham).min() >= -1e-10
        np.testing.assert_array_equal(np.diag(higham), 1.0)
        assert entry["higham_diagnostics"]["positive_semidefinite_within_tolerance"] is True


def test_distances_match_saved_results_and_the_documented_ordering(report):
    saved = {(r["shots"], r["replicate"]): r for r in SAVED_DISTANCES["rows"]}
    for entry in report["entries"]:
        row = saved[(entry["shots"], entry["replicate"])]
        for name in ("raw", "clipped", "higham"):
            assert entry["distance_to_exact"][name] == pytest.approx(row[name]["distance_to_exact"], abs=1e-8)
        assert entry["higham_iterations"] == row["higham"]["iterations"]
        d = entry["distance_to_exact"]
        assert d["higham"] < d["raw"] < d["clipped"]  # docs/higham-vs-clipping.md, all 15


def test_spectra_are_sorted_and_show_the_pathology(report):
    assert len(report["exact_eigenvalues"]) == 40
    assert min(report["exact_eigenvalues"]) > -1e-10
    for entry in report["entries"]:
        for name, values in entry["eigenvalues"].items():
            assert len(values) == 40 and values == sorted(values), name
        assert entry["eigenvalues"]["raw"][0] < -1e-3  # raw kernels are indefinite
        assert entry["eigenvalues"]["clipped"][0] >= -1e-10
        assert entry["eigenvalues"]["higham"][0] >= -1e-10


def test_saved_files_are_not_modified(report):
    before = (dashboard.RESULT_PATH.read_bytes(), dashboard.DISTANCES_PATH.read_bytes())
    observatory.build_kernel_repairs(dashboard.RESULT_PATH, dashboard.DISTANCES_PATH)
    assert (dashboard.RESULT_PATH.read_bytes(), dashboard.DISTANCES_PATH.read_bytes()) == before


def test_fails_closed_on_missing_malformed_or_inconsistent_files(tmp_path):
    with pytest.raises(OSError):
        observatory.build_kernel_repairs(tmp_path / "missing.json", dashboard.DISTANCES_PATH)
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    with pytest.raises(ValueError):
        observatory.build_kernel_repairs(dashboard.RESULT_PATH, bad)
    bad.write_text(json.dumps({"rows": [{"shots": 128}]}))
    with pytest.raises(ValueError):
        observatory.build_kernel_repairs(dashboard.RESULT_PATH, bad)
    tampered = json.loads(json.dumps(SAVED_DISTANCES))
    tampered["rows"][3]["higham"]["distance_to_exact"] += 1e-4
    bad.write_text(json.dumps(tampered))
    with pytest.raises(ValueError, match="disagree"):
        observatory.build_kernel_repairs(dashboard.RESULT_PATH, bad)
    partial = json.loads(json.dumps(SAVED_DISTANCES))
    partial["rows"] = partial["rows"][:14]
    bad.write_text(json.dumps(partial))
    with pytest.raises(ValueError):
        observatory.build_kernel_repairs(dashboard.RESULT_PATH, bad)
    huge = tmp_path / "huge.json"
    huge.write_bytes(b" " * (observatory.MAX_FILE_BYTES + 1))
    with pytest.raises(ValueError, match="size limit"):
        observatory.build_kernel_repairs(dashboard.RESULT_PATH, huge)


# ------------------------------------------------------------------ HTTP

@pytest.fixture()
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


def get(server, path):
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=60)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def test_repairs_route_is_cached_and_never_simulates(server, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("GET must not simulate")

    monkeypatch.setattr(dashboard, "simulate_bell", unexpected)
    monkeypatch.setattr(dashboard, "simulate_circuit", unexpected)
    monkeypatch.setattr(dashboard, "_repairs_cache", {})
    calls = []
    real = observatory.build_kernel_repairs
    monkeypatch.setattr(observatory, "build_kernel_repairs", lambda *a: calls.append(1) or real(*a))
    for _ in range(2):
        status, headers, body = get(server, "/api/kernel-repairs")
        assert status == 200 and "application/json" in headers["Content-Type"]
    assert len(calls) == 1
    assert len(json.loads(body)["entries"]) == 15


def test_repairs_route_fails_closed_with_503(server, monkeypatch, tmp_path):
    monkeypatch.setattr(dashboard, "_repairs_cache", {})
    monkeypatch.setattr(dashboard, "DISTANCES_PATH", tmp_path / "missing.json")
    status, _, body = get(server, "/api/kernel-repairs")
    assert status == 503 and "error" in json.loads(body)
    # the original saved-results route is unaffected
    status, _, _ = get(server, "/api/kernel-results")
    assert status == 200


def test_only_the_one_linked_document_is_served(server):
    status, headers, body = get(server, "/docs/higham-vs-clipping.md")
    assert status == 200 and headers["Content-Type"].startswith("text/plain")
    assert b"Higham" in body
    for path in ("/docs/", "/docs/dashboard.md", "/docs/higham-vs-clipping.md/", "/docs/../README.md", "/README.md"):
        status, _, _ = get(server, path)
        assert status in (400, 404), path
