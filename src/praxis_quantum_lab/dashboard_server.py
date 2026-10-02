"""Loopback-only research dashboard; no general file serving or experiment jobs."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULT_PATH = PROJECT_ROOT / "results" / "finite_shot_kernel_psd_repair.json"
DISTANCES_PATH = PROJECT_ROOT / "results" / "higham_vs_clipping.json"
DOC_ROUTES = {
    "/docs/higham-vs-clipping.md": PROJECT_ROOT / "docs" / "higham-vs-clipping.md",
}
ASSET_ROOT = Path(__file__).resolve().parent / "dashboard_assets"
MAX_BODY_BYTES = 1024
MAX_CIRCUIT_BODY_BYTES = 4096
MAX_RESULT_BYTES = 8 * 1024 * 1024
MAX_SHOTS = 8192
MAX_SEED = 2**31 - 1
CHANNEL_NAMES = {"bit_flip", "amplitude_damping", "depolarizing"}
POST_ROUTES = {
    "/api/bell": (MAX_BODY_BYTES, "Invalid Bell request. Check channel, strength, shots, seed, and step limits."),
    "/api/circuit": (MAX_CIRCUIT_BODY_BYTES, "Invalid circuit request. Check qubits, gates, shots, and seed limits."),
    "/api/security/bb84": (256, "Invalid BB84 request. Check qubits (200-20000), noise (0-0.2), sample (10-2000), eve, and seed."),
    "/api/security/rsa": (256, "Invalid RSA request. Use n = 15 or 21 and an integer seed."),
    "/api/security/grover": (256, "Invalid Grover request. Check key (0-15), iterations (0-8), pairs (1 or 2), and seed."),
}
STATIC_ROUTES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/playground.js": ("playground.js", "text/javascript; charset=utf-8"),
    "/security.js": ("security.js", "text/javascript; charset=utf-8"),
}


def parse_bell_request(payload: object) -> dict[str, Any]:
    """Validate all work limits before importing or invoking any simulator."""
    fields = {"channel", "strength", "shots", "seed", "step"}
    if not isinstance(payload, dict) or set(payload) != fields:
        raise ValueError("Provide exactly channel, strength, shots, seed, and step.")
    if not isinstance(payload["channel"], str) or payload["channel"] not in CHANNEL_NAMES:
        raise ValueError("Unsupported noise channel.")
    strength = payload["strength"]
    if type(strength) not in (float, int) or not 0 <= strength <= 1 or not math.isfinite(strength):
        raise ValueError("strength must be a finite number from 0 to 1.")
    for field, low, high in (("shots", 1, MAX_SHOTS), ("seed", 0, MAX_SEED), ("step", 0, 3)):
        if type(payload[field]) is not int or not low <= payload[field] <= high:
            raise ValueError(f"{field} must be an integer from {low} to {high}.")
    return {**payload, "strength": float(strength)}


def simulate_bell(payload: object) -> dict[str, Any]:
    """Adapt existing lab operations to one deterministic Bell circuit prefix.

    Each request starts from |00>. Stepping never depends on server session
    state. The density matrix is saved before measurement; counts are sampled
    by Aer and do not collapse the ensemble matrix displayed in the UI.
    """
    parameters = parse_bell_request(payload)
    import numpy as np
    from qiskit.quantum_info import Kraus
    from qiskit_aer import AerSimulator

    from .density_matrices import (
        apply_local_kraus_channel,
        measurement_probabilities_from_density_matrix,
        pure_state_to_density_matrix,
    )
    from .density_matrix_noise import (
        CHANNELS,
        _complex_matrix_for_json,
        _probability_record,
        bell_state_density_matrix,
        initial_bell_fidelity,
    )
    from .qiskit_experiments import two_qubit_entanglement_circuit
    from .state_vectors import HADAMARD

    step = parameters["step"]
    factory, convention = CHANNELS[parameters["channel"]]
    operators = factory(parameters["strength"])
    custom = pure_state_to_density_matrix([1, 0, 0, 0])
    if step == 1:
        custom = apply_local_kraus_channel(custom, (HADAMARD,), qubit=0)
    elif step >= 2:
        custom = bell_state_density_matrix()
    if step == 3:
        custom = apply_local_kraus_channel(custom, operators, qubit=0)

    circuit = two_qubit_entanglement_circuit()
    circuit.data = circuit.data[:min(step, 2)]
    if step == 3:
        circuit.append(Kraus(list(operators)).to_instruction(), [0])
    circuit.save_density_matrix()
    circuit.measure_all()
    simulator = AerSimulator(method="density_matrix", max_parallel_threads=1)
    result = simulator.run(
        circuit, shots=parameters["shots"], seed_simulator=parameters["seed"]
    ).result()
    if not result.success:
        raise RuntimeError("Local Aer simulation failed.")
    aer = np.asarray(result.data(0)["density_matrix"], dtype=np.complex128)
    counts = result.get_counts(0)
    basis = ["00", "01", "10", "11"]
    return {
        **parameters,
        "stage": ["Initial |00>", "After H(q0)", "Bell state after CX(q0, q1)",
                  "After local noise on q0"][step],
        "applied_gates": ["H(q0)", "CX(q0, q1)", "noise(q0)"][:step],
        "basis": basis,
        "basis_convention": "|q1 q0>; q0 is the rightmost bit",
        "parameter_convention": convention,
        "custom_density_matrix": _complex_matrix_for_json(custom),
        "aer_density_matrix": _complex_matrix_for_json(aer),
        "custom_probabilities": _probability_record(measurement_probabilities_from_density_matrix(custom)),
        "aer_probabilities": _probability_record(measurement_probabilities_from_density_matrix(aer)),
        "counts": {state: int(counts.get(state, 0)) for state in basis},
        "custom_bell_fidelity": initial_bell_fidelity(custom),
        "aer_bell_fidelity": initial_bell_fidelity(aer),
        "frobenius_error": float(np.linalg.norm(custom - aer, ord="fro")),
    }


def parse_circuit_request(payload: object) -> dict[str, Any]:
    """Circuit Playground validation (imported lazily so the server starts light)."""
    from .circuit_playground import parse_circuit_request as parse

    return parse(payload)


def simulate_circuit(payload: object) -> dict[str, Any]:
    from .circuit_playground import simulate_circuit as simulate

    return simulate(payload)


def circuit_presets() -> dict[str, Any]:
    from .circuit_playground import presets_payload

    return presets_payload()


_repairs_lock = threading.Lock()
_repairs_cache: dict[str, Any] = {}


def kernel_repairs() -> dict[str, Any]:
    """Read-only Observatory repair comparison, built once per process (no sampling)."""
    with _repairs_lock:
        if "report" not in _repairs_cache:
            from .observatory import build_kernel_repairs

            _repairs_cache["report"] = build_kernel_repairs(RESULT_PATH, DISTANCES_PATH)
        return _repairs_cache["report"]


def _finite_number(value: object) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def load_kernel_results() -> dict[str, Any]:
    """Read only the approved saved report, checking its dashboard-facing schema."""
    with RESULT_PATH.open("rb") as source:
        data = source.read(MAX_RESULT_BYTES + 1)
    if len(data) > MAX_RESULT_BYTES:
        raise ValueError("Saved result exceeds the size limit.")
    try:
        report = json.loads(data)
        metadata = report["metadata"]
        size = metadata["sample_size"]
        if type(size) is not int or not 1 <= size <= 200:
            raise ValueError("Invalid matrix size.")
        if metadata["train_size"] + metadata["test_size"] != size:
            raise ValueError("Invalid split sizes.")
        budgets = report["shot_budgets"]
        if not isinstance(budgets, list) or not 1 <= len(budgets) <= 50:
            raise ValueError("Invalid budgets.")
        for budget in budgets:
            if type(budget["shots"]) is not int or budget["shots"] < 1:
                raise ValueError("Invalid shot budget.")
            if not isinstance(budget["replicates"], list) or not 1 <= len(budget["replicates"]) <= 100:
                raise ValueError("Invalid replicates.")
            for replicate in budget["replicates"]:
                if type(replicate["shot_seed"]) is not int:
                    raise ValueError("Invalid shot seed.")
                for key in ("raw_sampled_kernel_matrix", "psd_repaired_kernel_matrix"):
                    matrix = replicate[key]
                    if not isinstance(matrix, list) or len(matrix) != size or any(
                        not isinstance(row, list) or len(row) != size or
                        any(not _finite_number(value) for value in row) for row in matrix
                    ):
                        raise ValueError("Invalid saved matrix.")
                for key in ("raw_matrix_diagnostics", "repaired_matrix_diagnostics"):
                    diagnostics = replicate[key]
                    for metric in ("minimum_eigenvalue", "frobenius_distance_from_raw", "psd_tolerance"):
                        if not _finite_number(diagnostics[metric]):
                            raise ValueError("Invalid saved diagnostics.")
                    if type(diagnostics["positive_semidefinite_within_tolerance"]) is not bool:
                        raise ValueError("Invalid saved PSD status.")
                for model in ("raw_finite_shot_kernel", "psd_repaired_transductive_kernel"):
                    for metric in ("accuracy", "f1"):
                        value = replicate["classifier_results"][model][metric]
                        if not _finite_number(value) or not 0 <= value <= 1:
                            raise ValueError("Invalid saved classifier metrics.")
        return report
    except (KeyError, TypeError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Invalid saved PSD report schema.") from error


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field.")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("Non-finite JSON numbers are not accepted.")


def _post_handlers() -> dict[str, tuple]:
    from . import security_lab

    return {
        "/api/bell": (parse_bell_request, simulate_bell),
        "/api/circuit": (parse_circuit_request, simulate_circuit),
        "/api/security/bb84": (security_lab.parse_bb84_request, security_lab.simulate_bb84),
        "/api/security/rsa": (security_lab.parse_rsa_request, security_lab.simulate_rsa),
        "/api/security/grover": (security_lab.parse_grover_request, security_lab.simulate_grover),
    }


class DashboardHandler(BaseHTTPRequestHandler):
    """Exact route allowlist, bounded JSON requests, and local-origin checks."""

    server_version = "PraxisLocal/1"

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(5)

    def _respond(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, status: int, value: Any) -> None:
        self._respond(status, json.dumps(value, allow_nan=False).encode(), "application/json; charset=utf-8")

    def _error(self, status: int, message: str) -> None:
        self._json(status, {"error": message})

    def _check_request(self) -> bool:
        if len(self.path) > 1024 or sum(len(k) + len(v) for k, v in self.headers.items()) > 8192:
            self._error(431, "Request headers or target too large.")
            return False
        hosts = self.headers.get_all("Host", [])
        allowed_hosts, allowed_origins = self.server.allowed_hosts_and_origins()
        if len(hosts) != 1 or hosts[0] not in allowed_hosts:
            if self.server.forwarded_host is not None:
                # Codespaces only: say which Host arrived, in the server log (never in the response).
                print(f"dashboard: rejected Host {hosts!r}", file=sys.stderr, flush=True)
            self._error(403, "Only the local dashboard host is allowed.")
            return False
        origins = self.headers.get_all("Origin", [])
        forwarded_hosts = self.headers.get_all("X-Forwarded-Host", [])
        if forwarded_hosts and (self.server.forwarded_host is None or forwarded_hosts != [self.server.forwarded_host]):
            self._error(403, "Only the local dashboard host is allowed.")
            return False
        if (origins and (len(origins) != 1 or origins[0] not in allowed_origins)) or self.headers.get("Sec-Fetch-Site") == "cross-site":
            self._error(403, "Cross-origin requests are not allowed.")
            return False
        if self.headers.get("Transfer-Encoding") is not None:
            self._error(400, "Transfer encoding is not supported.")
            return False
        try:
            parsed = urlsplit(self.path)
        except ValueError:
            self._error(400, "Invalid route.")
            return False
        if parsed.query or parsed.fragment or not self.path.startswith("/") or any(
            part in self.path for part in ("%", "\\", "..", "//")
        ):
            self._error(400, "Invalid route.")
            return False
        return True

    def do_GET(self) -> None:
        if not self._check_request():
            return
        if self.path in STATIC_ROUTES:
            filename, mime = STATIC_ROUTES[self.path]
            try:
                self._respond(200, (ASSET_ROOT / filename).read_bytes(), mime)
            except OSError:
                self._error(503, "Dashboard assets unavailable.")
        elif self.path in DOC_ROUTES:
            try:
                self._respond(200, DOC_ROUTES[self.path].read_bytes(), "text/plain; charset=utf-8")
            except OSError:
                self._error(503, "Document unavailable.")
        elif self.path == "/api/kernel-repairs":
            try:
                self._json(200, kernel_repairs())
            except (OSError, ValueError, RuntimeError):
                self._error(503, "Saved repair results unavailable or inconsistent.")
        elif self.path == "/api/circuit-presets":
            self._json(200, circuit_presets())
        elif self.path == "/api/security/status":
            from . import security_lab

            reason = security_lab.unavailable_reason()
            self._json(200, {"available": reason is None, "reason": reason})
        elif self.path == "/api/kernel-results":
            try:
                report = load_kernel_results()
                self._json(200, report)
            except (OSError, ValueError):
                self._error(503, "Saved PSD results unavailable or invalid.")
        else:
            self._error(404, "Route not found.")

    def do_POST(self) -> None:
        if not self._check_request():
            return
        route = POST_ROUTES.get(self.path)
        if route is None:
            self._error(404, "Route not found.")
            return
        limit, invalid_message = route
        if self.path.startswith("/api/security/"):
            from . import security_lab

            if security_lab.unavailable_reason():
                self._error(503, security_lab.unavailable_reason())
                return
        lengths = self.headers.get_all("Content-Length", [])
        if len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdecimal():
            self._error(400, "One valid Content-Length is required.")
            return
        if len(lengths[0]) > 10:
            self._error(413, f"Request body exceeds {limit} bytes.")
            return
        length = int(lengths[0])
        if length > limit:
            self._error(413, f"Request body exceeds {limit} bytes.")
            return
        if self.headers.get_content_type() != "application/json":
            self._error(415, "Use application/json.")
            return
        # Look the functions up now so each route uses its own validator and simulator.
        parse, simulate = _post_handlers()[self.path]
        try:
            body = self.rfile.read(length)
            if len(body) != length:
                raise ValueError("Incomplete JSON body.")
            payload = json.loads(body, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
            parameters = parse(payload)
        except (ValueError, UnicodeError, RecursionError, OverflowError):
            self._error(400, invalid_message)
            return
        except (TimeoutError, socket.timeout):
            self._error(408, "Request body timed out.")
            return
        if not self.server.simulation_lock.acquire(blocking=False):
            self._error(429, "A local simulation is running. Try again shortly.")
            return
        try:
            self._json(200, simulate(parameters))
        except Exception:
            self._error(500, "Local simulation failed; see server terminal.")
            import traceback
            traceback.print_exc()
        finally:
            self.server.simulation_lock.release()

    def _unsupported(self) -> None:
        self._error(405, "Method not supported.")

    do_HEAD = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _unsupported


_CODESPACE_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,98}[a-z0-9])?")
_FORWARDING_DOMAIN = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+")


def codespaces_host(port: int, environ: dict[str, str] | None = None) -> str:
    """The one forwarded host name GitHub Codespaces gives this port, read from its environment.

    Codespaces forwards a port as https://<codespace-name>-<port>.<forwarding-domain>; the
    forwarded URL is private to the codespace owner unless they change its visibility. The
    server still binds 127.0.0.1 only; this just lets that single forwarded name through the
    Host/Origin check. Raises ValueError outside Codespaces or on unexpected values.
    """
    env = os.environ if environ is None else environ
    if env.get("CODESPACES") != "true":
        raise ValueError("--codespaces works only inside a GitHub codespace (CODESPACES=true not set).")
    name = env.get("CODESPACE_NAME", "")
    domain = env.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "")
    if not _CODESPACE_LABEL.fullmatch(name) or not _FORWARDING_DOMAIN.fullmatch(domain):
        raise ValueError("Unexpected CODESPACE_NAME or GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN.")
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("--codespaces needs a fixed port from 1 to 65535.")
    return f"{name}-{port}.{domain}"


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port: int, forwarded_host: str | None = None):
        self.simulation_lock = threading.Lock()
        self._connections = threading.BoundedSemaphore(8)
        self.forwarded_host = forwarded_host
        super().__init__(("127.0.0.1", port), DashboardHandler)

    def allowed_hosts_and_origins(self) -> tuple[frozenset[str], frozenset[str]]:
        """Accepted Host headers and accepted Origin headers.

        Default: only 127.0.0.1:<port> and its http origin. In Codespaces mode the port
        forwarder may present either the codespace's own forwarded name or the loopback
        name it connected to (localhost:<port>), so both are accepted, together with the
        forwarded https origin. Any other host, any foreign origin, any X-Forwarded-Host
        other than this codespace's, and cross-site fetches are still refused.
        """
        local = f"127.0.0.1:{self.server_port}"
        hosts = {local}
        origins = {f"http://{local}"}
        if self.forwarded_host is not None:
            loopback = f"localhost:{self.server_port}"
            hosts |= {loopback, self.forwarded_host}
            origins |= {f"http://{loopback}", f"https://{self.forwarded_host}"}
        return frozenset(hosts), frozenset(origins)

    def process_request(self, request: socket.socket, client_address: tuple) -> None:
        if not self._connections.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._connections.release()
            raise

    def process_request_thread(self, request: socket.socket, client_address: tuple) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._connections.release()


def preload_simulators() -> None:
    """Import Qiskit, Aer and the simulation adapters on the thread that creates the server.

    If they are first imported lazily inside a short-lived request thread, the *next*
    simulation request crashes the whole process with a segmentation fault inside
    Qiskit's native circuit code (seen with Qiskit 2.5.2 / Aer 0.17.2, and reproduced with
    the original dashboard). Loading them once up front avoids it. No simulation runs here.
    """
    import qiskit  # noqa: F401
    import qiskit_aer  # noqa: F401

    from . import circuit_playground, density_matrix_noise, qiskit_experiments, security_lab  # noqa: F401

    security_lab.preload()  # the lesson modules the Security Lab routes reuse (False: that tab is unavailable)


def make_server(*, port: int = 8765, forwarded_host: str | None = None) -> DashboardServer:
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("port must be an integer from 0 to 65535.")
    preload_simulators()
    return DashboardServer(port, forwarded_host)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--codespaces",
        action="store_true",
        help="also accept this codespace's own forwarded URL (GitHub Codespaces only; still binds 127.0.0.1)",
    )
    arguments = parser.parse_args()
    forwarded = None
    if arguments.codespaces:
        try:
            forwarded = codespaces_host(arguments.port)
        except ValueError as error:
            parser.error(str(error))
    print("Loading Qiskit and Aer…", flush=True)
    with make_server(port=arguments.port, forwarded_host=forwarded) as server:
        print(f"Praxis Quantum Lab: http://127.0.0.1:{server.server_port}", flush=True)
        if forwarded:
            print(f"Codespaces URL (private to you): https://{forwarded}", flush=True)
        print("Local Aer only. Ctrl+C stops the dashboard.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
