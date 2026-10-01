"""Security Lab backend: BB84, toy RSA break with Shor, Grover key search (dashboard routes).

Each simulation reuses the lessons' own code (lessons/_qkd.py, lesson 28's distill, lessons/_shor.py,
lesson 18's cipher oracle, lessons/_grover_n.py), so the dashboard shows exactly what the lessons
teach. That needs a repository checkout. Without one (e.g. a wheel install), preload() records why,
the dashboard still starts, and the three routes answer 503 with that reason.
Every parser validates all limits before any simulator is touched.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path
from typing import Any

LESSONS_DIR = Path(__file__).resolve().parents[2] / "lessons"
MAX_SEED = 2**31 - 1
MAX_SECURITY_BODY_BYTES = 256
_modules: dict[str, Any] = {}
_unavailable: str | None = None  # why the lesson modules could not be loaded, if they could not
LESSON_NAMES = ("_qkd", "28_raw_to_secret_key", "_shor", "_grover_n", "18_toy_key_search")


def lesson_module(name: str):
    """Import a lessons/ module by file stem (e.g. '_qkd' or '28_raw_to_secret_key'), once."""
    if name not in _modules:
        if str(LESSONS_DIR) not in sys.path:
            sys.path.insert(0, str(LESSONS_DIR))
        spec = importlib.util.spec_from_file_location(f"praxis_lesson_{name}", LESSONS_DIR / f"{name}.py")
        if spec is None or spec.loader is None:
            raise RuntimeError(f"lesson module {name} not found")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _modules[name] = module
    return _modules[name]


def preload() -> bool:
    """Import every lesson module the routes use (on the server's main thread; see preload_simulators).
    Returns False, and remembers the reason, if they cannot be loaded: the Security Lab is then
    unavailable but the rest of the dashboard keeps working."""
    global _unavailable
    try:
        if not LESSONS_DIR.is_dir():
            raise FileNotFoundError(f"no lessons/ directory at {LESSONS_DIR}")
        for name in LESSON_NAMES:
            lesson_module(name)
    except Exception as error:  # noqa: BLE001 - any failure only disables this tab
        _unavailable = (f"The Security Lab needs a repository checkout: it reuses the lessons' code, and loading it "
                        f"failed ({error.__class__.__name__}: {error}). The other tabs work.")
        return False
    _unavailable = None
    return True


def unavailable_reason() -> str | None:
    return _unavailable


def _is_int(value: object) -> bool:
    return type(value) is int


def _exact_fields(payload: object, fields: set[str]) -> dict:
    if not isinstance(payload, dict) or set(payload) != fields:
        raise ValueError(f"Provide exactly {', '.join(sorted(fields))}.")
    return payload


def _int_in(payload: dict, field: str, low: int, high: int) -> int:
    value = payload[field]
    if not _is_int(value) or not low <= value <= high:
        raise ValueError(f"{field} must be an integer from {low} to {high}.")
    return value


# --------------------------------------------------------------------------- BB84

BB84_FIELDS = {"qubits", "noise", "sample", "eve", "seed"}


def parse_bb84_request(payload: object) -> dict[str, Any]:
    payload = _exact_fields(payload, BB84_FIELDS)
    noise = payload["noise"]
    if type(noise) not in (int, float) or not 0 <= noise <= 0.2 or not math.isfinite(noise):
        raise ValueError("noise must be a finite number from 0 to 0.2.")
    if type(payload["eve"]) is not bool:
        raise ValueError("eve must be true or false.")
    return {"qubits": _int_in(payload, "qubits", 200, 20000), "noise": float(noise),
            "sample": _int_in(payload, "sample", 10, 2000), "eve": payload["eve"],
            "seed": _int_in(payload, "seed", 0, MAX_SEED)}


BB84_RUNS_PER_SEED = 40  # bb84_round starts at most 32 Aer runs (base_run + 0..31)


def bb84_base_run(seed: int) -> int:
    """First Aer run index for a user seed. Each seed owns its own block of run indices, and
    run_seed() puts consecutive indices 10**7 apart (CLAUDE.md: Aer seeds shot i as seed + i, so
    independent runs need seeds at least `shots` apart). No two user seeds share an Aer run: the
    largest index, for seed 2**31 - 1, still gives an Aer seed below 2**63."""
    return 10_000 + seed * BB84_RUNS_PER_SEED


def simulate_bb84(parameters: dict[str, Any]) -> dict[str, Any]:
    import numpy as np

    qkd = lesson_module("_qkd")
    distill = lesson_module("28_raw_to_secret_key").distill
    rng = np.random.default_rng(parameters["seed"])
    round_ = qkd.bb84_round(parameters["qubits"], rng, base_run=bb84_base_run(parameters["seed"]),
                            noise_p=parameters["noise"], eve_fraction=1.0 if parameters["eve"] else 0.0)
    sifted = int(qkd.sift(round_).sum())
    sample = min(parameters["sample"], sifted // 2)
    row = distill(round_, rng, sample_size=sample)
    q_true = qkd.qber(round_)
    keep = qkd.sift(round_)
    eve_knows = float(np.mean(round_["intercepted"][keep] & (round_["eve_bases"][keep] == round_["alice_bases"][keep]))) if parameters["eve"] else 0.0
    return {
        "qubits": parameters["qubits"], "sifted": sifted, "sample": sample, "sample_clipped": sample < parameters["sample"],
        "qber_true": q_true, "qber_estimate": row["q_est"], "qber_bound": row["q_bound"], "sample_errors": row["sample_errors"],
        "errors_seen": row["sample_errors"] > 0,  # noise also causes errors: Alice and Bob cannot tell them apart
        "p_detect": 1 - (1 - q_true) ** sample,
        "p_detect_formula": (1 - 0.75**sample) if parameters["eve"] else None,
        "eve": parameters["eve"], "eve_knows_fraction": eve_knows,
        "status": row["status"], "key_bits": row["m"], "remaining_after_sample": row["n"],
        "leaked": row.get("leaked"), "keys_equal": row.get("keys_equal"),
        "shannon_fraction": row["asymptotic_fraction"], "threshold": 0.11,
    }


# ---------------------------------------------------------------------- toy RSA

RSA_FIELDS = {"n", "seed"}
TOY_KEYS = {15: {"e": 3, "message": "HELLO", "alphabet": "ABCDEFGHIJKLMNO"},
            21: {"e": 5, "message": "HIDE", "alphabet": "ABCDEFGHIJKLMNOPQRST"}}
MAX_ATTEMPTS = 24


def parse_rsa_request(payload: object) -> dict[str, Any]:
    payload = _exact_fields(payload, RSA_FIELDS)
    if not _is_int(payload["n"]) or payload["n"] not in TOY_KEYS:
        raise ValueError("n must be 15 or 21.")
    return {"n": payload["n"], "seed": _int_in(payload, "seed", 0, MAX_SEED)}


def simulate_rsa(parameters: dict[str, Any]) -> dict[str, Any]:
    import numpy as np

    shor = lesson_module("_shor")
    n, seed = parameters["n"], parameters["seed"]
    key = TOY_KEYS[n]
    t = 2 * shor.work_qubits(n)
    rng = np.random.default_rng(seed)
    units = [a for a in range(2, n) if math.gcd(a, n) == 1]
    attempts, factors, chosen = [], None, None
    for a in rng.permutation(units).tolist():
        runs = shor.sample_runs(a, n, 8, (seed * 37 + a) % MAX_SEED)
        for m in runs:
            candidate = shor.period_from_measurement(m, t, n)
            passes = pow(a, candidate, n) == 1
            result, reason = shor.factors_from_order(a, n, candidate) if passes else (None, f"{a}^{candidate} mod {n} != 1")
            attempts.append({"a": a, "m": m, "fraction": f"{m}/{2 ** t}", "candidate": candidate, "check": passes,
                             "outcome": f"factors {result[0]} x {result[1]}" if result else reason})
            if result or len(attempts) >= MAX_ATTEMPTS or (passes and not result):
                break
        if result:
            factors, chosen = result, a
            break
        if len(attempts) >= MAX_ATTEMPTS:
            break
    out: dict[str, Any] = {"n": n, "e": key["e"], "counting_qubits": t, "qubits": t + shor.work_qubits(n), "attempts": attempts}
    if not factors:
        return {**out, "status": "no factors within the attempt limit; try another seed"}
    p, q = factors
    phi = (p - 1) * (q - 1)
    d = pow(key["e"], -1, phi)
    plain = [key["alphabet"].index(ch) for ch in key["message"]]
    cipher = [pow(m, key["e"], n) for m in plain]
    decrypted = "".join(key["alphabet"][pow(c, d, n)] for c in cipher)
    probabilities = shor.readout_distribution(chosen, n)
    peaks = [m for m in sorted(range(len(probabilities)), key=lambda m: -probabilities[m])[:6] if probabilities[m] > 1e-3]
    return {**out, "status": "key recovered", "a": chosen, "period": shor.order(chosen, n), "factors": [p, q], "phi": phi, "d": d,
            "message": key["message"], "ciphertext": cipher, "decrypted": decrypted,
            "peaks": [{"m": m, "probability": round(float(probabilities[m]), 4),
                       "candidate": shor.period_from_measurement(m, t, n)} for m in sorted(peaks)]}


# ------------------------------------------------------------------- Grover key

GROVER_FIELDS = {"key", "iterations", "pairs", "seed"}
MAX_ITERATIONS = 8
GROVER_SHOTS = 1000
PLAINTEXTS = (0b0001, 0b0000)


def parse_grover_request(payload: object) -> dict[str, Any]:
    payload = _exact_fields(payload, GROVER_FIELDS)
    if not _is_int(payload["pairs"]) or payload["pairs"] not in (1, 2):
        raise ValueError("pairs must be 1 or 2.")
    return {"key": _int_in(payload, "key", 0, 15), "iterations": _int_in(payload, "iterations", 0, MAX_ITERATIONS),
            "pairs": payload["pairs"], "seed": _int_in(payload, "seed", 0, MAX_SEED)}


def simulate_grover(parameters: dict[str, Any]) -> dict[str, Any]:
    cipher = lesson_module("18_toy_key_search")
    grover = lesson_module("_grover_n")
    from .qiskit_experiments import ideal_counts

    pairs = [(p, cipher.encrypt(parameters["key"], p)) for p in PLAINTEXTS[: parameters["pairs"]]]
    matching = cipher.matching_keys(pairs)
    oracle, extra = cipher.key_oracle(pairs)
    k = parameters["iterations"]
    circuit = grover.grover_circuit(cipher.KEY_BITS, oracle, k, extra_qubits=extra, measure=True)
    counts = ideal_counts(circuit, shots=GROVER_SHOTS, seed=parameters["seed"])
    secret = format(parameters["key"], "04b")
    M = len(matching)
    return {
        "key": secret, "pairs": [{"plaintext": format(p, "04b"), "ciphertext": format(c, "04b")} for p, c in pairs],
        "matching_keys": [format(m, "04b") for m in matching], "iterations": k, "qubits": circuit.num_qubits,
        "optimal_iterations": grover.optimal_iterations(16, M),
        "curve": [{"iterations": j, "p_match": grover.success_probability(j, 16, M), "p_secret": grover.success_probability(j, 16, M) / M}
                  for j in range(MAX_ITERATIONS + 1)],
        "measured_secret": counts.get(secret, 0) / GROVER_SHOTS,
        "measured_match": sum(v for key, v in counts.items() if int(key, 2) in matching) / GROVER_SHOTS,
        "top_counts": dict(sorted(counts.items(), key=lambda item: -item[1])[:4]), "shots": GROVER_SHOTS,
        "classical_expected_trials": (16 + 1) / 2,
    }
