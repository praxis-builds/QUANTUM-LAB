"""Lesson 03: phase. |+> and |-> look the same when measured directly but differ after H."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from qiskit import QuantumCircuit

from _common import SEED, heading, out_dir
from praxis_quantum_lab.qiskit_experiments import ideal_counts
from praxis_quantum_lab.state_vectors import (
    HADAMARD,
    PAULI_Z,
    apply_single_qubit_gate,
    basis_state,
    measurement_probabilities,
)

SHOTS = 2000


def prepare(sign: str, *, hadamard_before_measuring: bool) -> QuantumCircuit:
    """|+> = H|0>, |-> = Z H|0> (Z flips the sign of the |1> amplitude)."""
    circuit = QuantumCircuit(1, 1)
    circuit.h(0)
    if sign == "-":
        circuit.z(0)
    if hadamard_before_measuring:
        circuit.h(0)
    circuit.measure(0, 0)
    return circuit


def phase_circuit(phi: float) -> QuantumCircuit:
    """(|0> + e^{i phi}|1>)/sqrt(2), then H, then measure."""
    circuit = QuantumCircuit(1, 1)
    circuit.h(0)
    circuit.p(phi, 0)
    circuit.h(0)
    circuit.measure(0, 0)
    return circuit


def main() -> dict:
    heading("Step 1: the two states, as amplitudes")
    plus = apply_single_qubit_gate(HADAMARD, basis_state(0))
    minus = apply_single_qubit_gate(PAULI_Z, plus)
    print(f"|+> amplitudes = ({plus[0].real:+.3f}, {plus[1].real:+.3f})")
    print(f"|-> amplitudes = ({minus[0].real:+.3f}, {minus[1].real:+.3f})   <- only the sign of the second amplitude differs")
    print(f"probabilities |+>: {measurement_probabilities(plus).round(3).tolist()}   |->: {measurement_probabilities(minus).round(3).tolist()}")

    heading("Step 2: measured directly (local Aer)")
    direct = {sign: ideal_counts(prepare(sign, hadamard_before_measuring=False), shots=SHOTS, seed=SEED) for sign in "+-"}
    for sign, counts in direct.items():
        print(f"|{sign}> measured directly: {counts}")

    heading("Step 3: apply H first, then measure")
    after_h = {sign: ideal_counts(prepare(sign, hadamard_before_measuring=True), shots=SHOTS, seed=SEED) for sign in "+-"}
    for sign, counts in after_h.items():
        print(f"|{sign}> then H then measured: {counts}")

    heading("Step 4: any phase angle, not just a sign flip")
    angles = np.linspace(0, 2 * np.pi, 13)
    measured, predicted = [], []
    for phi in angles:
        counts = ideal_counts(phase_circuit(float(phi)), shots=SHOTS, seed=SEED)
        measured.append(counts.get("0", 0) / SHOTS)
        predicted.append(float(np.cos(phi / 2) ** 2))
        print(f"phase = {phi / np.pi:4.2f} pi: measured P(0) = {measured[-1]:.3f}   cos^2(phase/2) = {predicted[-1]:.3f}")
    figure, axis = plt.subplots(figsize=(6, 4))
    axis.plot(angles / np.pi, predicted, "k-", label="cos^2(phase / 2)")
    axis.plot(angles / np.pi, measured, "o", label="Aer, 2000 shots")
    axis.set_xlabel("hidden phase (units of pi)")
    axis.set_ylabel("P(0) after the final H")
    axis.legend()
    figure.tight_layout()
    path = out_dir() / "03_phase_sweep.png"
    figure.savefig(path, dpi=130)
    plt.close(figure)
    print(f"\nsaved plot: {Path(path)}")
    return {
        "direct": direct,
        "after_h": after_h,
        "plus": plus.real.tolist(),
        "minus": minus.real.tolist(),
        "sweep_measured": measured,
        "sweep_predicted": predicted,
    }


if __name__ == "__main__":
    main()
