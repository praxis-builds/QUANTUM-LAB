"""Lesson 25: thresholds. Below it, bigger codes help; above it, they hurt."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

from _common import heading, out_dir
from _qec import channel, pauli_channel_noise, repetition_logical_error, run_seed

DISTANCES = (1, 3, 5, 7)
BELOW = (0.01, 0.05, 0.1, 0.2, 0.3, 0.4)
ABOVE = (0.6, 0.7)
SHOTS = 20_000


def repetition_circuit(d: int, bit: int) -> QuantumCircuit:
    """Encode `bit` into d qubits, let the channel act, measure every qubit.

    Decoding is a majority vote over the measured bits. With perfect measurements that is exactly
    what minimum-weight syndrome decoding does, so no ancillas are needed for this experiment.
    """
    circuit = QuantumCircuit(d, d)
    if bit:
        circuit.x(0)
    for qubit in range(1, d):
        circuit.cx(0, qubit)
    channel(circuit, range(d))
    circuit.measure(range(d), range(d))
    return circuit


def measured_logical_error(d: int, p: float, run: int) -> float:
    """Logical error over SHOTS runs each of logical 0 and 1, with independent seeds (runs 2*run, 2*run + 1)."""
    simulator = AerSimulator(method="stabilizer", noise_model=pauli_channel_noise(p, "x"))
    failures = 0
    for bit in (0, 1):
        counts = simulator.run(repetition_circuit(d, bit), shots=SHOTS, seed_simulator=run_seed(2 * run + bit)).result().get_counts()
        failures += sum(n for key, n in counts.items() if (key.count("1") > d // 2) != bool(bit))
    return failures / (2 * SHOTS)


def plot(table: dict):
    figure, axis = plt.subplots(figsize=(7, 4.5))
    fine = np.linspace(0.005, 0.75, 300)
    for d in DISTANCES:
        axis.plot(fine, [repetition_logical_error(d, p) for p in fine], "-", label=f"d = {d} (formula)")
        points = [p for p in table[d] if table[d][p]["measured"] > 0]
        axis.plot(points, [table[d][p]["measured"] for p in points], "o", color=axis.lines[-1].get_color(), markersize=4)
    axis.axvline(0.5, color="grey", linestyle="--", linewidth=1, label="threshold p = 1/2 (this toy)")
    axis.set_yscale("log")
    axis.set_xlabel("physical bit-flip probability p")
    axis.set_ylabel("logical error rate")
    axis.set_title("Repetition codes: dots = Aer, lines = binomial formula")
    axis.legend(fontsize=8)
    figure.tight_layout()
    path = out_dir() / "25_threshold.png"
    figure.savefig(path, dpi=130)
    plt.close(figure)
    return path


def main() -> dict:
    heading(f"Step 1: repetition codes d = 3, 5, 7 under bit flips ({SHOTS} shots each for logical 0 and 1, independent seeds)")
    table = {}
    for i, d in enumerate(DISTANCES):
        table[d] = {}
        for j, p in enumerate(BELOW + ABOVE):
            table[d][p] = {"measured": measured_logical_error(d, p, 1 + i * len(BELOW + ABOVE) + j),
                           "formula": repetition_logical_error(d, p)}
    for p in BELOW + ABOVE:
        row = "  ".join(f"d={d}: {table[d][p]['measured']:.5f} ({table[d][p]['formula']:.5f})" for d in DISTANCES)
        trend = "bigger d helps" if table[7][p]["formula"] < table[3][p]["formula"] else "bigger d HURTS"
        print(f"p = {p:<4}: {row}   -> {trend}")
    print("(measured, then the exact binomial formula in brackets; d = 1 is an unprotected bit)")

    heading("Step 2: how fast the logical error falls below threshold")
    ratios = {}
    for p in (0.01, 0.05, 0.1):
        ratios[p] = [table[d][p]["formula"] / table[d + 2][p]["formula"] for d in (3, 5)]
        print(f"p = {p}: each step d -> d + 2 divides the logical error by {ratios[p][0]:.1f} (3->5) and {ratios[p][1]:.1f} (5->7)")
    print("The further below threshold, the bigger the gain per extra pair of qubits.")

    heading("Step 3: what this toy leaves out")
    print("- The threshold 1/2 assumes perfect encoding, perfect parity checks and perfect measurement.")
    print("  With faulty syndrome extraction (errors during the checks themselves) thresholds drop to")
    print("  around a percent for the surface code (see the lesson page for sources).")
    print("- One round only: real memories repeat syndrome rounds and must decode errors in time too.")
    print("- A repetition code handles ONE error type; a real code must handle X and Z (Lessons 23-24).")
    path = plot(table)
    print(f"\nSaved {path}")
    return {"table": table, "ratios": ratios}


if __name__ == "__main__":
    main()
