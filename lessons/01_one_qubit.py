"""Lesson 01: one qubit, amplitudes, the Born rule, and why we need shots."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from qiskit import QuantumCircuit

from _common import SEED, heading, out_dir
from praxis_quantum_lab.qiskit_experiments import ideal_counts
from praxis_quantum_lab.state_vectors import measurement_probabilities, state_from_amplitudes

SHOT_COUNTS = (1, 10, 100, 1000, 10000)
TRUE_P1 = 0.3  # the state below is built so that P(1) = 0.3


def build_state():
    """Amplitudes (sqrt(0.7), sqrt(0.3)); both are real numbers here."""
    return state_from_amplitudes([np.sqrt(1 - TRUE_P1), np.sqrt(TRUE_P1)])


def measured_circuit() -> QuantumCircuit:
    """The same state made from a gate: Ry(theta)|0> with cos(theta/2)^2 = 0.7."""
    theta = 2 * np.arccos(np.sqrt(1 - TRUE_P1))
    circuit = QuantumCircuit(1, 1)
    circuit.ry(theta, 0)
    circuit.measure(0, 0)
    return circuit


def main() -> dict:
    heading("Step 1: amplitudes are not probabilities")
    state = build_state()
    probabilities = measurement_probabilities(state)
    print(f"amplitudes   : |0> -> {state[0].real:.4f}, |1> -> {state[1].real:.4f}")
    print(f"Born rule    : P(0) = amplitude^2 = {probabilities[0]:.4f}, P(1) = {probabilities[1]:.4f}")
    print(f"probabilities add to {probabilities.sum():.4f}")

    heading("Step 2: measuring gives ONE bit per shot (local Aer)")
    estimates = {}
    for shots in SHOT_COUNTS:
        counts = ideal_counts(measured_circuit(), shots=shots, seed=SEED)
        estimates[shots] = counts.get("1", 0) / shots
        print(f"{shots:>6} shots: counts={counts}  estimated P(1) = {estimates[shots]:.4f}  (true {TRUE_P1})")

    heading("Step 3: how fast does the estimate improve? (200 repeats per size)")
    rng = np.random.default_rng(SEED)
    mean_error = {}
    for shots in SHOT_COUNTS:
        repeats = rng.binomial(shots, TRUE_P1, size=200) / shots
        mean_error[shots] = float(np.mean(np.abs(repeats - TRUE_P1)))
        print(f"{shots:>6} shots: typical error = {mean_error[shots]:.4f}   (0.4/sqrt(shots) = {0.4 / np.sqrt(shots):.4f})")

    figure, (left, right) = plt.subplots(1, 2, figsize=(10, 4))
    left.semilogx(SHOT_COUNTS, [estimates[s] for s in SHOT_COUNTS], "o-", label="one Aer run")
    left.axhline(TRUE_P1, color="k", ls="--", label="true P(1)")
    left.set_xlabel("shots")
    left.set_ylabel("estimated P(1)")
    left.legend()
    right.loglog(SHOT_COUNTS, [mean_error[s] for s in SHOT_COUNTS], "o-", label="typical error (200 repeats)")
    right.loglog(SHOT_COUNTS, [0.4 / np.sqrt(s) for s in SHOT_COUNTS], "k--", label="0.4 / sqrt(shots)")
    right.set_xlabel("shots")
    right.set_ylabel("|estimate - true|")
    right.legend()
    figure.tight_layout()
    path = out_dir() / "01_one_qubit_convergence.png"
    figure.savefig(path, dpi=130)
    plt.close(figure)
    print(f"\nsaved plot: {Path(path)}")
    return {
        "probabilities": probabilities.tolist(),
        "estimates": estimates,
        "mean_error": mean_error,
        "true_p1": TRUE_P1,
    }


if __name__ == "__main__":
    main()
