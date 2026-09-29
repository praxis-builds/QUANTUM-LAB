"""Lesson 04: entanglement (product state vs Bell state) and why the kernel's final CZ cancels."""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, partial_trace

from _common import SEED, heading
from praxis_quantum_lab.kernel_spectrum import feature_map_q, make_subset_features
from praxis_quantum_lab.qiskit_experiments import ideal_counts

SHOTS = 4000


def product_circuit() -> QuantumCircuit:
    circuit = QuantumCircuit(2, 2)
    circuit.h(0)
    circuit.h(1)
    circuit.measure([0, 1], [0, 1])
    return circuit


def bell_circuit() -> QuantumCircuit:
    circuit = QuantumCircuit(2, 2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure([0, 1], [0, 1])
    return circuit


def summarize(counts: dict[str, int]) -> dict[str, float]:
    """Counts use Qiskit's |q1 q0> label order: the left character is qubit 1."""
    total = sum(counts.values())
    q0_is_one = sum(v for k, v in counts.items() if k[-1] == "1") / total
    q1_is_one = sum(v for k, v in counts.items() if k[0] == "1") / total
    same = sum(v for k, v in counts.items() if k[0] == k[1]) / total
    return {"p_q0_is_1": q0_is_one, "p_q1_is_1": q1_is_one, "p_same": same}


def without_cz(circuit: QuantumCircuit) -> QuantumCircuit:
    """The same circuit with every CZ removed."""
    stripped = QuantumCircuit(circuit.num_qubits)
    for instruction in circuit.data:
        if instruction.operation.name != "cz":
            stripped.append(instruction.operation, instruction.qubits)
    return stripped


def overlap_squared(first: QuantumCircuit, second: QuantumCircuit) -> float:
    return float(abs(Statevector(first).inner(Statevector(second))) ** 2)


def main() -> dict:
    heading("Step 1: product state (H on each qubit) vs Bell state (H, then CNOT)")
    results = {}
    for name, circuit in (("product", product_circuit()), ("bell", bell_circuit())):
        counts = ideal_counts(circuit, shots=SHOTS, seed=SEED)
        results[name] = summarize(counts)
        print(f"{name:<8}: counts={dict(sorted(counts.items()))}")
        print(f"          qubit 0 alone shows 1 with {results[name]['p_q0_is_1']:.3f}; qubit 1 alone shows 1 with {results[name]['p_q1_is_1']:.3f}")
        print(f"          the two qubits agree with probability {results[name]['p_same']:.3f}")

    heading("Step 2: how entangled is a state? (purity of one qubit alone)")
    purities = {}
    for name, circuit in (("product", product_circuit()), ("bell", bell_circuit())):
        state = Statevector(circuit.remove_final_measurements(inplace=False))
        purities[name] = float(np.real(partial_trace(state, [1]).purity()))
        print(f"{name:<8}: purity of qubit 0 alone = {purities[name]:.3f}  (1.0 = fully definite state, 0.5 = maximally mixed)")

    heading("Step 3: the lab's feature map ends with a CZ, which entangles ...")
    features = make_subset_features(8, 0)
    x, z = features[0], features[1]
    full_x = feature_map_q(x, 2)
    print(f"sample x = {np.round(x, 3).tolist()}: purity of qubit 0 with CZ    = {float(np.real(partial_trace(Statevector(full_x), [1]).purity())):.3f}")
    print(f"sample x = {np.round(x, 3).tolist()}: purity of qubit 0 without CZ = {float(np.real(partial_trace(Statevector(without_cz(full_x)), [1]).purity())):.3f}")

    heading("Step 4: ... yet the kernel does not care")
    full_kernel = overlap_squared(full_x, feature_map_q(z, 2))
    plain_kernel = overlap_squared(without_cz(full_x), without_cz(feature_map_q(z, 2)))
    print(f"kernel value K(x, z) = |<phi(z)|phi(x)>|^2 with the CZ    : {full_kernel:.12f}")
    print(f"kernel value K(x, z) = |<phi(z)|phi(x)>|^2 without the CZ : {plain_kernel:.12f}")
    print(f"difference: {abs(full_kernel - plain_kernel):.2e}")
    print("Reason: the CZ is the LAST gate and is the same for every sample. Applying the same")
    print("reversible operation to both states does not change how much they overlap.")
    return {
        "results": results,
        "purities": purities,
        "kernel_with_cz": full_kernel,
        "kernel_without_cz": plain_kernel,
        "purity_with_cz": float(np.real(partial_trace(Statevector(full_x), [1]).purity())),
    }


if __name__ == "__main__":
    main()
