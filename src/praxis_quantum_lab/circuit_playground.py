"""Circuit Playground backend: strict request validation and 1-3 qubit simulation.

The exact state comes from NumPy (reusing the project's Hadamard, Pauli and
Born-rule code); shots come from local Aer.  Basis labels are |q2 q1 q0> and
index = sum of bit_k << k, matching the rest of the lab.  ``measure`` marks the
qubits covered by the sampled histogram (deferred measurement at the end); it
never collapses the exact state shown in the live views.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from .state_vectors import (
    HADAMARD,
    PAULI_X,
    PAULI_Y,
    PAULI_Z,
    measurement_probabilities,
    validate_state,
)

MAX_QUBITS = 3
MAX_GATES = 30
MAX_SHOTS = 8192
MAX_SEED = 2**31 - 1
MAX_ANGLE = 4 * math.pi
MAX_CIRCUIT_BODY_BYTES = 4096

SINGLE_QUBIT_GATES = {"h", "x", "y", "z", "s", "t"}
ROTATION_GATES = {"rx", "ry", "rz", "cp"}  # gates that take an angle
TWO_QUBIT_GATES = {"cx", "cz", "swap", "cp"}
GATE_NAMES = SINGLE_QUBIT_GATES | ROTATION_GATES | TWO_QUBIT_GATES | {"measure"}
REQUEST_FIELDS = {"qubits", "gates", "shots", "seed"}

S_GATE = np.array([[1, 0], [0, 1j]], dtype=np.complex128)
T_GATE = np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]], dtype=np.complex128)
FIXED_GATES = {"h": HADAMARD, "x": PAULI_X, "y": PAULI_Y, "z": PAULI_Z, "s": S_GATE, "t": T_GATE}


def rotation_matrix(name: str, angle: float) -> np.ndarray:
    """RX, RY, RZ in Qiskit's convention (RZ has the symmetric global phase). CP is applied in apply_gate."""
    cosine, sine = math.cos(angle / 2), math.sin(angle / 2)
    if name == "rx":
        return np.array([[cosine, -1j * sine], [-1j * sine, cosine]], dtype=np.complex128)
    if name == "ry":
        return np.array([[cosine, -sine], [sine, cosine]], dtype=np.complex128)
    if name == "rz":
        return np.array([[np.exp(-0.5j * angle), 0], [0, np.exp(0.5j * angle)]], dtype=np.complex128)
    raise ValueError(f"Unknown rotation gate: {name}")


def _is_int(value: object) -> bool:
    return type(value) is int


def _parse_gate(item: object, qubits: int) -> dict[str, Any]:
    if not isinstance(item, dict) or not {"gate", "qubits"} <= set(item) or not set(item) <= {"gate", "qubits", "angle"}:
        raise ValueError("Each gate needs exactly gate and qubits (plus angle for rx, ry, rz, cp).")
    name = item["gate"]
    if not isinstance(name, str) or name not in GATE_NAMES:
        raise ValueError("Unsupported gate.")
    wires = item["qubits"]
    arity = 2 if name in TWO_QUBIT_GATES else 1
    if not isinstance(wires, list) or len(wires) != arity or not all(_is_int(w) and 0 <= w < qubits for w in wires):
        raise ValueError(f"Gate {name} needs {arity} qubit index(es) inside the circuit.")
    if len(set(wires)) != len(wires):
        raise ValueError("A two-qubit gate needs two different qubits.")
    gate: dict[str, Any] = {"gate": name, "qubits": list(wires)}
    if name in ROTATION_GATES:
        angle = item.get("angle")
        # Range first: math.isfinite raises OverflowError on huge JSON integers.
        if type(angle) not in (int, float) or not abs(angle) <= MAX_ANGLE:
            raise ValueError("angle must be a finite number from -4*pi to 4*pi.")
        gate["angle"] = float(angle)
    elif "angle" in item:
        raise ValueError(f"Gate {name} does not take an angle.")
    return gate


def parse_circuit_request(payload: object) -> dict[str, Any]:
    """Validate every limit before any simulator is imported."""
    if not isinstance(payload, dict) or set(payload) != REQUEST_FIELDS:
        raise ValueError("Provide exactly qubits, gates, shots, and seed.")
    qubits = payload["qubits"]
    if not _is_int(qubits) or not 1 <= qubits <= MAX_QUBITS:
        raise ValueError(f"qubits must be an integer from 1 to {MAX_QUBITS}.")
    for field, low, high in (("shots", 1, MAX_SHOTS), ("seed", 0, MAX_SEED)):
        if not _is_int(payload[field]) or not low <= payload[field] <= high:
            raise ValueError(f"{field} must be an integer from {low} to {high}.")
    raw_gates = payload["gates"]
    if not isinstance(raw_gates, list) or len(raw_gates) > MAX_GATES:
        raise ValueError(f"gates must be a list of at most {MAX_GATES} gates.")
    gates = [_parse_gate(item, qubits) for item in raw_gates]
    measured: set[int] = set()
    for gate in gates:
        if gate["gate"] == "measure":
            if gate["qubits"][0] in measured:
                raise ValueError("A qubit can be measured only once.")
            measured.add(gate["qubits"][0])
        elif measured & set(gate["qubits"]):
            raise ValueError("A measured qubit cannot be used by a later gate.")
    return {"qubits": qubits, "gates": gates, "shots": payload["shots"], "seed": payload["seed"]}


def apply_gate(state: np.ndarray, gate: dict[str, Any], num_qubits: int) -> np.ndarray:
    """Apply one validated gate to a state vector (index = sum bit_k << k)."""
    name, wires = gate["gate"], gate["qubits"]
    if name == "measure":
        return state
    if name in TWO_QUBIT_GATES:
        indices = np.arange(2**num_qubits)
        first, second = wires
        if name == "cx":
            return state[np.where((indices >> first) & 1, indices ^ (1 << second), indices)]
        if name in ("cz", "cp"):
            phase = -1.0 if name == "cz" else np.exp(1j * gate["angle"])
            return state * np.where(((indices >> first) & 1) & ((indices >> second) & 1), phase, 1.0)
        differ = ((indices >> first) & 1) != ((indices >> second) & 1)
        return state[np.where(differ, indices ^ (1 << first) ^ (1 << second), indices)]
    matrix = rotation_matrix(name, gate["angle"]) if name in ROTATION_GATES else FIXED_GATES[name]
    axis = num_qubits - 1 - wires[0]
    tensor = state.reshape((2,) * num_qubits)
    return np.moveaxis(np.tensordot(matrix, tensor, axes=([1], [axis])), 0, axis).reshape(-1)


def bloch_vectors(state: np.ndarray, num_qubits: int) -> list[list[float]]:
    """Bloch vector of each qubit from its reduced density matrix (rho = (I + r.sigma)/2).

    For a pure global state, |r| < 1 exactly when the qubit is entangled with the rest.
    """
    tensor = validate_state(state).reshape((2,) * num_qubits)
    vectors = []
    for qubit in range(num_qubits):
        rows = np.moveaxis(tensor, num_qubits - 1 - qubit, 0).reshape(2, -1)
        rho = rows @ rows.conj().T
        vectors.append([float(2 * rho[0, 1].real), float(-2 * rho[0, 1].imag), float((rho[0, 0] - rho[1, 1]).real)])
    return vectors


def circuit_states(parameters: dict[str, Any]) -> list[np.ndarray]:
    """State after each prefix of the gate list: index 0 is |0...0>."""
    num_qubits = parameters["qubits"]
    state = np.zeros(2**num_qubits, dtype=np.complex128)
    state[0] = 1.0
    states = [state]
    for gate in parameters["gates"]:
        state = apply_gate(state, gate, num_qubits)
        states.append(state)
    return states


def _clean(value: float) -> float:
    return round(float(value), 12) + 0.0


def _step(index: int, label: str, state: np.ndarray, num_qubits: int) -> dict[str, Any]:
    probabilities = measurement_probabilities(state)
    vectors = bloch_vectors(state, num_qubits)
    return {
        "index": index,
        "label": label,
        "amplitudes": [[_clean(a.real), _clean(a.imag)] for a in state],
        "probabilities": [_clean(p) for p in probabilities],
        "bloch": [[_clean(c) for c in vector] for vector in vectors],
        "bloch_length": [_clean(math.sqrt(sum(c * c for c in vector))) for vector in vectors],
    }


def _gate_label(gate: dict[str, Any]) -> str:
    wires = ",".join(f"q{w}" for w in gate["qubits"])
    angle = f" ({gate['angle'] / math.pi:.3g}π)" if "angle" in gate else ""
    return f"{gate['gate'].upper()}{angle} on {wires}"


def marginal_probabilities(probabilities: np.ndarray, measured: list[int]) -> np.ndarray:
    """Exact probabilities of the measured qubits, label order = highest measured qubit first."""
    result = np.zeros(2 ** len(measured))
    for index, probability in enumerate(probabilities):
        key = sum(((index >> qubit) & 1) << position for position, qubit in enumerate(measured))
        result[key] += probability
    return result


def sample_counts_with_aer(parameters: dict[str, Any], measured: list[int]) -> dict[str, int]:
    from qiskit import QuantumCircuit
    from qiskit_aer import AerSimulator

    circuit = QuantumCircuit(parameters["qubits"], len(measured))
    for gate in parameters["gates"]:
        name, wires = gate["gate"], gate["qubits"]
        if name == "measure":
            continue
        if name in ROTATION_GATES:
            getattr(circuit, name)(gate["angle"], *wires)
        else:
            getattr(circuit, name)(*wires)
    for position, qubit in enumerate(measured):
        circuit.measure(qubit, position)
    result = (
        AerSimulator(method="statevector", max_parallel_threads=1)
        .run(circuit, shots=parameters["shots"], seed_simulator=parameters["seed"])
        .result()
    )
    if not result.success:
        raise RuntimeError("Local Aer simulation failed.")
    raw = result.get_counts(0)
    width = len(measured)
    return {format(key, f"0{width}b"): int(raw.get(format(key, f"0{width}b"), 0)) for key in range(2**width)}


def simulate_circuit(payload: object) -> dict[str, Any]:
    """Exact per-step states (NumPy) plus sampled counts (local Aer)."""
    parameters = parse_circuit_request(payload)
    num_qubits = parameters["qubits"]
    gates = parameters["gates"]
    states = circuit_states(parameters)
    steps = [_step(0, "Start |" + "0" * num_qubits + "⟩", states[0], num_qubits)]
    for index, (gate, state) in enumerate(zip(gates, states[1:]), start=1):
        steps.append(_step(index, _gate_label(gate), state, num_qubits))
    measured = sorted(gate["qubits"][0] for gate in gates if gate["gate"] == "measure") or list(range(num_qubits))
    final_probabilities = measurement_probabilities(states[-1])
    return {
        "qubits": num_qubits,
        "gates": gates,
        "shots": parameters["shots"],
        "seed": parameters["seed"],
        "basis": [format(i, f"0{num_qubits}b") for i in range(2**num_qubits)],
        "basis_convention": "|q2 q1 q0>; q0 is the rightmost bit",
        "steps": steps,
        "measured_qubits": measured,
        "measured_labels": [format(i, f"0{len(measured)}b") for i in range(2 ** len(measured))],
        "measured_probabilities": [_clean(p) for p in marginal_probabilities(final_probabilities, measured)],
        "counts": sample_counts_with_aer(parameters, measured),
    }


def _gate(name: str, *wires: int, angle: float | None = None) -> dict[str, Any]:
    gate: dict[str, Any] = {"gate": name, "qubits": list(wires)}
    if angle is not None:
        gate["angle"] = angle
    return gate


PRESETS: list[dict[str, Any]] = [
    {
        "id": "superposition",
        "title": "Superposition (H)",
        "caption": "H turns a definite 0 into an equal mix of 0 and 1: measuring gives 50/50.",
        "qubits": 1,
        "gates": [_gate("h", 0)],
    },
    {
        "id": "interference",
        "title": "Interference (H·H)",
        "caption": "The second H makes the two paths to 1 cancel, so the qubit returns to 0 every time.",
        "qubits": 1,
        "gates": [_gate("h", 0), _gate("h", 0)],
    },
    {
        "id": "phase",
        "title": "Phase is invisible until H (H·Z·H)",
        "caption": "Z only flips a sign, which no measurement sees, but H turns that sign into a definite 1.",
        "qubits": 1,
        "gates": [_gate("h", 0), _gate("z", 0), _gate("h", 0)],
    },
    {
        "id": "bell",
        "title": "Bell state",
        "caption": "H then CNOT: each qubit alone looks random, yet the two always agree.",
        "qubits": 2,
        "gates": [_gate("h", 0), _gate("cx", 0, 1)],
    },
    {
        "id": "ghz",
        "title": "GHZ (3 qubits)",
        "caption": "Three qubits that all read 000 or all read 111, each half the time.",
        "qubits": 3,
        "gates": [_gate("h", 0), _gate("cx", 0, 1), _gate("cx", 1, 2)],
    },
    {
        "id": "grover",
        "title": "Grover search on 2 qubits",
        "caption": "One marked item out of four (|11⟩) found with probability 1; the final minus sign is a global sign.",
        "qubits": 2,
        "gates": [
            _gate("h", 0), _gate("h", 1), _gate("cz", 0, 1),
            _gate("h", 0), _gate("h", 1), _gate("x", 0), _gate("x", 1),
            _gate("cz", 0, 1), _gate("x", 0), _gate("x", 1), _gate("h", 0), _gate("h", 1),
        ],
    },
    {
        "id": "kickback",
        "title": "Phase kickback",
        "caption": "The target (|−⟩) does not change, but the control's phase flips, so a final H turns |+⟩ into a definite 1.",
        "qubits": 2,
        "gates": [_gate("x", 1), _gate("h", 1), _gate("h", 0), _gate("cx", 0, 1), _gate("h", 0)],
    },
    {
        "id": "dj_constant",
        "title": "Deutsch–Jozsa: constant",
        "caption": "Constant oracle f(x) = 1 (X on the |−⟩ qubit q2) only adds a global sign, so q1 q0 read 00 every time.",
        "qubits": 3,
        "gates": [
            _gate("x", 2), _gate("h", 2), _gate("h", 0), _gate("h", 1),
            _gate("x", 2),
            _gate("h", 0), _gate("h", 1), _gate("measure", 0), _gate("measure", 1),
        ],
    },
    {
        "id": "dj_balanced",
        "title": "Deutsch–Jozsa: balanced",
        "caption": "Balanced oracle f = x0 XOR x1 (two CNOTs into the |−⟩ qubit q2): the signs cancel on 00, so q1 q0 read 11, never 00.",
        "qubits": 3,
        "gates": [
            _gate("x", 2), _gate("h", 2), _gate("h", 0), _gate("h", 1),
            _gate("cx", 0, 2), _gate("cx", 1, 2),
            _gate("h", 0), _gate("h", 1), _gate("measure", 0), _gate("measure", 1),
        ],
    },
    {
        "id": "bv_101",
        "title": "Bernstein–Vazirani (s = 101)",
        "caption": "One query reads out s = 101; the oracle is written as the phase it kicks back, Z on q0 and q2 (what CNOTs into |−⟩ reduce to).",
        "qubits": 3,
        "gates": [
            _gate("h", 0), _gate("h", 1), _gate("h", 2),
            _gate("z", 0), _gate("z", 2),
            _gate("h", 0), _gate("h", 1), _gate("h", 2),
        ],
    },
    {
        "id": "simon_11",
        "title": "Simon (s = 11)",
        "caption": "Hidden period s = 11 with f(x) = x0 XOR x1 on a one-qubit output q2: q1 q0 read only 00 or 11, both with y·s = 0 mod 2.",
        "qubits": 3,
        "gates": [
            _gate("h", 0), _gate("h", 1),
            _gate("cx", 0, 2), _gate("cx", 1, 2),
            _gate("h", 0), _gate("h", 1), _gate("measure", 0), _gate("measure", 1),
        ],
    },
    {
        "id": "qft_period2",
        "title": "QFT of a period-2 input",
        "caption": "H on q1, q2 spreads over 0, 2, 4, 6 (period 2); the QFT turns that into two peaks, |000⟩ and |100⟩ (multiples of 8/2).",
        "qubits": 3,
        "gates": [
            _gate("h", 1), _gate("h", 2),
            _gate("h", 2), _gate("cp", 1, 2, angle=math.pi / 2), _gate("cp", 0, 2, angle=math.pi / 4),
            _gate("h", 1), _gate("cp", 0, 1, angle=math.pi / 2),
            _gate("h", 0), _gate("swap", 0, 2),
        ],
    },
    {
        "id": "qpe_s",
        "title": "Phase estimation of S",
        "caption": "S multiplies |1⟩ (on q2) by e^{2πi/4}; kickback onto q0, q1 and an inverse QFT read that phase as 01 = 1/4, every shot.",
        "qubits": 3,
        "gates": [
            _gate("x", 2), _gate("h", 0), _gate("h", 1),
            _gate("cp", 0, 2, angle=math.pi / 2), _gate("cp", 1, 2, angle=math.pi),
            _gate("swap", 0, 1), _gate("h", 0), _gate("cp", 0, 1, angle=-math.pi / 2), _gate("h", 1),
            _gate("measure", 0), _gate("measure", 1),
        ],
    },
]


def presets_payload() -> dict[str, Any]:
    """Static preset data, checked against the same validator as user circuits."""
    for preset in PRESETS:
        parse_circuit_request({"qubits": preset["qubits"], "gates": preset["gates"], "shots": 1, "seed": 0})
    return {"presets": PRESETS}
