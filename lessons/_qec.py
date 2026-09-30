"""Noise and quantum error correction on toy codes (shared by lessons 21-25).

Conventions: Qiskit qubit order; data qubits first, then syndrome ancillas. Noise that plays the
role of "the channel" is attached to `id` gates, so it hits exactly where the circuit places them.
"""

from __future__ import annotations

from qiskit import QuantumCircuit, transpile
from qiskit_aer.noise import NoiseModel, depolarizing_error

BASIS = ["u", "cx"]


def per_gate_noise(p: float, *, qubits_1q: set[int] | None = None, pairs_2q: set[tuple[int, int]] | None = None) -> NoiseModel:
    """Depolarizing error of strength p after EVERY u and cx gate (the circuit must be transpiled
    to BASIS first). Optionally restrict it to some qubits / qubit pairs.

    The lab's local_noise_model (qiskit_experiments.py) only adds noise to h and cx; after
    transpiling, most gates are u gates, so lesson 21 needs this per-gate version.
    """
    model = NoiseModel(basis_gates=BASIS)
    if p == 0:
        return model
    one, two = depolarizing_error(p, 1), depolarizing_error(p, 2)
    if qubits_1q is None and pairs_2q is None:
        model.add_all_qubit_quantum_error(one, ["u"])
        model.add_all_qubit_quantum_error(two, ["cx"])
        return model
    for q in qubits_1q or ():
        model.add_quantum_error(one, ["u"], [q])
    for a, b in pairs_2q or ():
        model.add_quantum_error(two, ["cx"], [a, b])
    return model


def to_basis(circuit: QuantumCircuit, seed: int) -> QuantumCircuit:
    return transpile(circuit, basis_gates=BASIS, optimization_level=1, seed_transpiler=seed)


def gate_count(circuit: QuantumCircuit) -> int:
    ops = circuit.count_ops()
    return int(ops.get("u", 0) + ops.get("cx", 0))
