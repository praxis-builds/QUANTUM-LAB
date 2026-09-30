"""Lesson 12: phase estimation. Read a gate's hidden rotation amount off counting qubits."""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from _common import SEED, heading, out_dir
from _qft import phase_error, qpe_circuit, qpe_distribution
from praxis_quantum_lab.circuit_playground import bloch_vectors
from praxis_quantum_lab.qiskit_experiments import ideal_counts

SHOTS = 2000
EXACT = {"T": 1 / 8, "S": 1 / 4}  # T|1> = e^{2 pi i/8}|1>, S|1> = e^{2 pi i/4}|1>
THIRD = 1 / 3
COUNTING = (2, 3, 4, 5)
TOLERANCE = 0.05


def kickback_angles(phase: float, counting: int) -> list[float]:
    """Before the inverse QFT, counting qubit k is (|0> + e^{2 pi i phase 2^k}|1>)/sqrt 2.
    Returns each qubit's Bloch-vector angle around the equator, in turns."""
    circuit = QuantumCircuit(counting + 1)
    circuit.x(counting)
    circuit.h(range(counting))
    for k in range(counting):
        circuit.cp(2 * math.pi * phase * 2**k, k, counting)
    vectors = bloch_vectors(Statevector(circuit).data, counting + 1)
    return [round((math.atan2(v[1], v[0]) / (2 * math.pi)) % 1.0, 12) for v in vectors[:counting]]


def summarise(phase: float, counting: int) -> dict:
    probabilities = qpe_distribution(phase, counting)
    size = 2**counting
    nearest = round(phase * size) % size
    errors = [phase_error(m, counting, phase) for m in range(size)]
    return {
        "probabilities": probabilities.tolist(),
        "nearest": nearest,
        "p_nearest": float(probabilities[nearest]),
        "p_within": float(sum(p for p, e in zip(probabilities, errors) if e < TOLERANCE)),
        "nearest_error": errors[nearest],
    }


def plot(third: dict):
    figure, (left, right) = plt.subplots(1, 2, figsize=(11, 4))
    for t in (3, 5):
        size = 2**t
        left.bar(np.arange(size) / size, third[t]["probabilities"], width=0.8 / size, alpha=0.7, label=f"t = {t}")
    left.axvline(THIRD, color="black", linestyle="--", linewidth=1, label="true phase 1/3")
    left.set_xlabel("estimate m / 2^t")
    left.set_ylabel("probability")
    left.set_title("Phase 1/3: readout distribution")
    left.legend()
    right.plot(COUNTING, [third[t]["p_nearest"] for t in COUNTING], "o-", label="P(nearest estimate)")
    right.plot(COUNTING, [third[t]["p_within"] for t in COUNTING], "s-", label=f"P(|error| < {TOLERANCE})")
    right.axhline(4 / math.pi**2, color="grey", linestyle=":", label="4/pi^2 lower bound")
    right.set_xlabel("counting qubits t")
    right.set_ylim(0, 1.05)
    right.set_xticks(COUNTING)
    right.set_title("More qubits: sharper, not more certain")
    right.legend(fontsize=8)
    figure.tight_layout()
    path = out_dir() / "12_phase_estimation.png"
    figure.savefig(path, dpi=130)
    plt.close(figure)
    return path


def main() -> dict:
    heading("Step 1: the phase is kicked back onto the counting qubits (T, phase 1/8, t = 3)")
    angles = kickback_angles(EXACT["T"], 3)
    for k, angle in enumerate(angles):
        print(f"counting qubit {k} (controls T^{2**k}): phase = {angle:.3f} turns  (= 2^{k} x 1/8)")
    print("Qubit k holds the phase shifted k binary places (2^k x 1/8), by Lesson 07's kickback.")

    heading(f"Step 2: exact case, then the inverse QFT reads it out ({SHOTS} shots)")
    exact = {}
    for gate, phase in EXACT.items():
        probabilities = qpe_distribution(phase, 3)
        counts = ideal_counts(qpe_circuit(phase, 3, measure=True), shots=SHOTS, seed=SEED)
        exact[gate] = {"probabilities": probabilities.tolist(), "counts": counts}
        best = int(np.argmax(probabilities))
        print(f"{gate} on |1> (phase {phase}): P({best:03b}) = {probabilities[best]:.6f}, counts = {counts}  "
              f"->  {best}/8 = {best / 8}")

    heading("Step 3: phase 1/3 cannot be written in binary with t digits")
    third = {t: summarise(THIRD, t) for t in COUNTING}
    for t in COUNTING:
        row = third[t]
        top = sorted(range(2**t), key=lambda m: -row["probabilities"][m])[:3]
        spread = ", ".join(f"{m:0{t}b}: {row['probabilities'][m]:.3f}" for m in top)
        print(f"t = {t}: nearest {row['nearest']}/{2 ** t} = {row['nearest'] / 2 ** t:.4f} (error {row['nearest_error']:.4f}); "
              f"P(nearest) = {row['p_nearest']:.4f}; P(|error| < {TOLERANCE}) = {row['p_within']:.4f}; top: {spread}")
    counts3 = ideal_counts(qpe_circuit(THIRD, 3, measure=True), shots=SHOTS, seed=SEED)
    print(f"Aer, t = 3, {SHOTS} shots: {dict(sorted(counts3.items(), key=lambda item: -item[1]))}")
    print("More counting qubits halve the error of the best estimate, and make a close estimate more")
    print("likely. They do NOT make the single nearest value more likely: it stays near 0.68.")

    heading("Step 4: the classical baseline")
    matrix = np.diag([1, np.exp(2j * math.pi * THIRD)])
    eigenphases = sorted(float((np.angle(v) / (2 * math.pi)) % 1.0) for v in np.linalg.eigvals(matrix))
    print(f"np.linalg.eigvals of the 2x2 matrix gives the phases {eigenphases} directly.")
    print("Phase estimation only helps when U is a circuit too big to write down as a matrix. Its cost:")
    print("digit k needs U applied 2^k times, 2^t - 1 in all, unless U^(2^k) has a shortcut")
    print("(modular multiplication has one, which is what Shor uses).")

    heading("Step 5: the bridge to Shor (program step 4)")
    print("Shor's algorithm is phase estimation applied to U: |y> -> |a*y mod N>. Its phases are s/r,")
    print("where r is the period of a^x mod N. Continued fractions turn the estimate into r, and r")
    print("usually gives a factor of N. That is what threatens RSA; this lesson breaks nothing.")
    path = plot(third)
    print(f"\nSaved {path}")
    return {"angles": angles, "exact": exact, "third": third, "counts_third_t3": counts3, "eigenphases": eigenphases}


if __name__ == "__main__":
    main()
