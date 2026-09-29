"""Two-qubit Grover search as an explicit list of gate layers (shared by lessons 05 and 06).

Basis labels follow Qiskit: "10" means qubit 1 = 1, qubit 0 = 0.
"""

from __future__ import annotations

from qiskit import QuantumCircuit

Layer = tuple[str, list[tuple[str, tuple[int, ...]]]]


def grover_layers(marked: str) -> list[Layer]:
    """One Grover iteration: prepare, oracle (mark), diffuse (amplify)."""
    if len(marked) != 2 or set(marked) - {"0", "1"}:
        raise ValueError("marked must be one of '00', '01', '10', '11'.")
    zero_qubits = [qubit for qubit in (0, 1) if marked[::-1][qubit] == "0"]
    flips = [("x", (qubit,)) for qubit in zero_qubits]
    both = lambda gate: [(gate, (0,)), (gate, (1,))]  # noqa: E731
    layers: list[Layer] = [("prepare: H on both", both("h"))]
    if flips:
        layers.append(("oracle: X on the qubits whose marked bit is 0", flips))
    layers.append(("oracle: CZ flips the sign of the marked item", [("cz", (0, 1))]))
    if flips:
        layers.append(("oracle: undo the X gates", flips))
    layers += [
        ("diffuse: H on both", both("h")),
        ("diffuse: X on both", both("x")),
        ("diffuse: CZ", [("cz", (0, 1))]),
        ("diffuse: X on both", both("x")),
        ("diffuse: H on both", both("h")),
    ]
    return layers


def stage_boundaries(marked: str) -> dict[str, int]:
    """Number of layers completed after each named stage."""
    layers = grover_layers(marked)
    oracle_end = max(i for i, (name, _) in enumerate(layers) if name.startswith("oracle")) + 1
    return {"prepare": 1, "oracle": oracle_end, "diffuse": len(layers)}


def circuit_from_layers(layers: list[Layer], *, measure: bool = False) -> QuantumCircuit:
    circuit = QuantumCircuit(2, 2 if measure else 0)
    for _, gates in layers:
        for gate, qubits in gates:
            getattr(circuit, gate)(*qubits)
    if measure:
        circuit.measure([0, 1], [0, 1])
    return circuit
