"""Lesson 02: interference. H then H returns |0>; a classical coin flipped twice does not."""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit

from _common import SEED, heading
from praxis_quantum_lab.qiskit_experiments import ideal_counts
from praxis_quantum_lab.state_vectors import (
    HADAMARD,
    apply_single_qubit_gate,
    basis_state,
    measurement_probabilities,
)

SHOTS = 2000


def circuit_with_hadamards(count: int) -> QuantumCircuit:
    circuit = QuantumCircuit(1, 1)
    for _ in range(count):
        circuit.h(0)
    circuit.measure(0, 0)
    return circuit


def main() -> dict:
    heading("Step 1: amplitudes at each step (NumPy, from state_vectors.py)")
    start = basis_state(0)
    after_one = apply_single_qubit_gate(HADAMARD, start)
    after_two = apply_single_qubit_gate(HADAMARD, after_one)
    for label, state in (("start |0>", start), ("after H", after_one), ("after H, H", after_two)):
        probabilities = measurement_probabilities(state)
        print(f"{label:<11}: amplitudes = ({state[0].real:+.3f}, {state[1].real:+.3f})  ->  P(0)={probabilities[0]:.2f}, P(1)={probabilities[1]:.2f}")

    heading("Step 2: why the second H gives 0 (two paths to |1> cancel)")
    h = HADAMARD.real
    via_0 = after_one[0].real * h[1, 0]
    via_1 = after_one[1].real * h[1, 1]
    print(f"amplitude of |1> via the |0> path: {after_one[0].real:+.3f} x {h[1, 0]:+.3f} = {via_0:+.3f}")
    print(f"amplitude of |1> via the |1> path: {after_one[1].real:+.3f} x {h[1, 1]:+.3f} = {via_1:+.3f}")
    print(f"total amplitude of |1>           : {via_0 + via_1:+.3f}   (cancelled: destructive interference)")
    up_0 = after_one[0].real * h[0, 0]
    up_1 = after_one[1].real * h[0, 1]
    print(f"total amplitude of |0>           : {up_0:+.3f} + {up_1:+.3f} = {up_0 + up_1:+.3f}   (added: constructive interference)")

    heading("Step 3: real measurements on local Aer")
    counts_one = ideal_counts(circuit_with_hadamards(1), shots=SHOTS, seed=SEED)
    counts_two = ideal_counts(circuit_with_hadamards(2), shots=SHOTS, seed=SEED)
    print(f"H then measure   : {counts_one}")
    print(f"H, H then measure: {counts_two}")

    heading("Step 4: a classical coin flipped twice")
    # A classical coin is described by probabilities, which can never be negative, so nothing can cancel.
    coin = np.array([[0.5, 0.5], [0.5, 0.5]])  # 'randomise': new bit is 0 or 1 with probability 1/2
    distribution = np.array([1.0, 0.0])
    for flip in (1, 2):
        distribution = coin @ distribution
        print(f"after {flip} random flip(s): P(0)={distribution[0]:.2f}, P(1)={distribution[1]:.2f}")

    return {
        "amplitudes_after_h": after_one.real.tolist(),
        "amplitudes_after_hh": after_two.real.tolist(),
        "amplitude_one_total": float(via_0 + via_1),
        "counts_h": counts_one,
        "counts_hh": counts_two,
        "classical_after_two": distribution.tolist(),
    }


if __name__ == "__main__":
    main()
