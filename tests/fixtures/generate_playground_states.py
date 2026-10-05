"""Expected Circuit Playground states from the Python simulator, for the JavaScript port's cross-check.

    .venv/bin/python tests/fixtures/generate_playground_states.py

Writes tests/fixtures/playground_states.json: every preset (all steps), 50 random circuits from
np.random.default_rng(20261005) (final state, every label), and requests with the Python
validator's verdict. Values are unrounded floats (JSON keeps full double precision).
tests/js/circuit_sim.test.js checks the JavaScript simulator against it to 1e-12, and
tests/test_playground_static.py fails if this file is stale.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from praxis_quantum_lab import circuit_playground as cp  # noqa: E402
from praxis_quantum_lab.state_vectors import measurement_probabilities  # noqa: E402

OUT = Path(__file__).resolve().parent / "playground_states.json"
SEED = 20261005
GATE_ARITY = {**{g: 1 for g in ("h", "x", "y", "z", "s", "t", "rx", "ry", "rz")},
              **{g: 2 for g in ("cx", "cz", "cp", "swap")}, "ccz": 3, "ccx": 3}


def _pairs(state: np.ndarray) -> list[list[float]]:
    return [[float(a.real), float(a.imag)] for a in state]


def _record(qubits: int, gates: list[dict], all_steps: bool) -> dict:
    parameters = cp.parse_circuit_request({"qubits": qubits, "gates": gates, "shots": 1, "seed": 0})
    states = cp.circuit_states(parameters)
    measured = sorted(g["qubits"][0] for g in parameters["gates"] if g["gate"] == "measure") or list(range(qubits))
    chosen = range(len(states)) if all_steps else [len(states) - 1]
    return {
        "qubits": qubits, "gates": parameters["gates"],
        "labels": [cp._gate_label(g) for g in parameters["gates"]],
        "steps": {str(i): {"amplitudes": _pairs(states[i]),
                           "probabilities": [float(p) for p in measurement_probabilities(states[i])],
                           "bloch": cp.bloch_vectors(states[i], qubits)} for i in chosen},
        "measured_qubits": measured,
        "measured_probabilities": [float(p) for p in cp.marginal_probabilities(measurement_probabilities(states[-1]), measured)],
    }


def _random_circuit(rng: np.random.Generator) -> tuple[int, list[dict]]:
    qubits = int(rng.integers(1, 4))
    names = [g for g, arity in GATE_ARITY.items() if arity <= qubits]
    gates = []
    for _ in range(int(rng.integers(1, 16))):
        name = names[int(rng.integers(len(names)))]
        wires = [int(w) for w in rng.permutation(qubits)[:GATE_ARITY[name]]]
        gate = {"gate": name, "qubits": wires}
        if name in cp.ROTATION_GATES:
            gate["angle"] = float(rng.uniform(-4 * math.pi, 4 * math.pi))
        gates.append(gate)
    for qubit in range(qubits):  # measure some qubits at the end (measurement must come last on a wire)
        if rng.random() < 0.4:
            gates.append({"gate": "measure", "qubits": [qubit]})
    return qubits, gates


VALIDATION = [
    {"qubits": 2, "gates": [], "shots": 1, "seed": 0},
    {"qubits": 0, "gates": [], "shots": 1, "seed": 0},
    {"qubits": 4, "gates": [], "shots": 1, "seed": 0},
    {"qubits": True, "gates": [], "shots": 1, "seed": 0},
    {"qubits": "2", "gates": [], "shots": 1, "seed": 0},
    {"qubits": 2, "gates": [], "shots": 0, "seed": 0},
    {"qubits": 2, "gates": [], "shots": 8193, "seed": 0},
    {"qubits": 2, "gates": [], "shots": 8192, "seed": 2147483647},
    {"qubits": 2, "gates": [], "shots": 1, "seed": -1},
    {"qubits": 2, "gates": [], "shots": 1, "seed": 2147483648},
    {"qubits": 2, "gates": [], "shots": 1},
    {"qubits": 2, "gates": [], "shots": 1, "seed": 0, "extra": 1},
    {"qubits": 1, "gates": [{"gate": "h", "qubits": [0]}] * 30, "shots": 1, "seed": 0},
    {"qubits": 1, "gates": [{"gate": "h", "qubits": [0]}] * 31, "shots": 1, "seed": 0},
    {"qubits": 2, "gates": [{"gate": "cx", "qubits": [0, 0]}], "shots": 1, "seed": 0},
    {"qubits": 2, "gates": [{"gate": "cx", "qubits": [0]}], "shots": 1, "seed": 0},
    {"qubits": 2, "gates": [{"gate": "h", "qubits": [2]}], "shots": 1, "seed": 0},
    {"qubits": 2, "gates": [{"gate": "h", "qubits": [-1]}], "shots": 1, "seed": 0},
    {"qubits": 2, "gates": [{"gate": "foo", "qubits": [0]}], "shots": 1, "seed": 0},
    {"qubits": 2, "gates": [{"gate": "h"}], "shots": 1, "seed": 0},
    {"qubits": 2, "gates": [{"gate": "h", "qubits": [0], "angle": 1}], "shots": 1, "seed": 0},
    {"qubits": 2, "gates": [{"gate": "rx", "qubits": [0]}], "shots": 1, "seed": 0},
    {"qubits": 2, "gates": [{"gate": "rx", "qubits": [0], "angle": 13}], "shots": 1, "seed": 0},
    {"qubits": 2, "gates": [{"gate": "rx", "qubits": [0], "angle": -12.5}], "shots": 1, "seed": 0},
    {"qubits": 2, "gates": [{"gate": "rx", "qubits": [0], "angle": "1"}], "shots": 1, "seed": 0},
    {"qubits": 2, "gates": [{"gate": "rx", "qubits": [0], "angle": True}], "shots": 1, "seed": 0},
    {"qubits": 2, "gates": [{"gate": "cp", "qubits": [0, 1], "angle": 1.5}], "shots": 1, "seed": 0},
    {"qubits": 2, "gates": [{"gate": "ccx", "qubits": [0, 1, 1]}], "shots": 1, "seed": 0},
    {"qubits": 3, "gates": [{"gate": "ccx", "qubits": [0, 1, 2]}], "shots": 1, "seed": 0},
    {"qubits": 2, "gates": [{"gate": "measure", "qubits": [0]}, {"gate": "measure", "qubits": [0]}], "shots": 1, "seed": 0},
    {"qubits": 2, "gates": [{"gate": "measure", "qubits": [0]}, {"gate": "cx", "qubits": [1, 0]}], "shots": 1, "seed": 0},
    {"qubits": 2, "gates": [{"gate": "measure", "qubits": [0]}, {"gate": "h", "qubits": [1]}], "shots": 1, "seed": 0},
    {"qubits": 2, "gates": "h", "shots": 1, "seed": 0},
    [],
    None,
]


def _verdict(payload) -> dict:
    try:
        cp.parse_circuit_request(payload)
    except ValueError as error:
        return {"payload": payload, "accepted": False, "error": str(error)}
    return {"payload": payload, "accepted": True, "error": None}


def build() -> dict:
    rng = np.random.default_rng(SEED)
    return {
        "source": "src/praxis_quantum_lab/circuit_playground.py (NumPy); generated by tests/fixtures/generate_playground_states.py",
        "seed": SEED,
        "presets": {p["id"]: _record(p["qubits"], p["gates"], all_steps=True) for p in cp.PRESETS},
        "random": [_record(*_random_circuit(rng), all_steps=False) for _ in range(50)],
        "validation": [_verdict(payload) for payload in VALIDATION],
    }


if __name__ == "__main__":
    OUT.write_text(json.dumps(build(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes)")
