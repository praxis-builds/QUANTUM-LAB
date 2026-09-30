"""Lesson 22: the 3-qubit bit-flip code. Three copies, a syndrome, and a majority that fixes one flip."""

from __future__ import annotations

from itertools import product

import matplotlib.pyplot as plt
import numpy as np
from qiskit_aer import AerSimulator

from _common import SEED, heading, out_dir
from _qec import INPUT_STATES, bit_flip_code, logical_error_rate, pauli_channel_noise, run_seed

RATES = (0.01, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6)
SHOTS = 4000


def formula(p: float) -> float:
    """Fails when 2 or 3 of the 3 copies flip: 3p^2(1-p) + p^3 = 3p^2 - 2p^3."""
    return 3 * p**2 - 2 * p**3


def one_shot(errors: list[tuple[int, str]], state: str) -> tuple[str, bool]:
    """Run once with fixed errors: (syndrome bits, logical state survived?)."""
    memory = AerSimulator(method="stabilizer").run(bit_flip_code(state, errors), shots=1, seed_simulator=SEED, memory=True)
    out, syndrome = memory.result().get_memory()[0].split()
    return syndrome, int(out) == (1 if state in ("1", "-", "-i") else 0)


def plot(sweep: dict):
    rates = list(sweep)
    fine = np.linspace(0, 0.65, 200)
    figure, axis = plt.subplots(figsize=(7, 4.5))
    axis.plot(fine, fine, "k:", label="no code: error p")
    axis.plot(fine, [formula(p) for p in fine], "-", label="3p² − 2p³")
    axis.plot(rates, [sweep[p]["measured"] for p in rates], "o", label=f"Aer, {SHOTS} shots x 2 inputs")
    axis.axvline(0.5, color="grey", linestyle="--", linewidth=1, label="break-even p = 1/2")
    axis.set_xlabel("physical bit-flip probability p (each qubit)")
    axis.set_ylabel("logical error rate")
    axis.set_title("3-qubit bit-flip code")
    axis.legend(fontsize=8)
    figure.tight_layout()
    path = out_dir() / "22_bit_flip_code.png"
    figure.savefig(path, dpi=130)
    plt.close(figure)
    return path


def main() -> dict:
    heading("Step 1: every single X error, on every data qubit, for every input state")
    single = {}
    for qubit in range(3):
        results = [one_shot([(qubit, "x")], state) for state in INPUT_STATES]
        single[qubit] = {"syndrome": results[0][0], "all_corrected": all(ok for _, ok in results)}
        print(f"X on data qubit {qubit}: syndrome {single[qubit]['syndrome']} -> corrected on all 6 inputs: "
              f"{single[qubit]['all_corrected']}")
    no_error = all(one_shot([], state)[1] for state in INPUT_STATES)
    print(f"no error: syndrome {one_shot([], '0')[0]}, state intact on all 6 inputs: {no_error}")

    heading("Step 2: two or three flips (inputs |0> and |1>)")
    multi = {}
    for qubits in ((0, 1), (0, 2), (1, 2), (0, 1, 2)):
        results = [one_shot([(q, "x") for q in qubits], state) for state in ("0", "1")]
        multi[qubits] = {"syndrome": results[0][0], "failed": not any(ok for _, ok in results)}
        print(f"X on {qubits}: syndrome {multi[qubits]['syndrome']} -> logical bit flipped: {multi[qubits]['failed']}")
    print("Two flips look like one flip on the remaining qubit, so the 'correction' completes a logical")
    print("flip. Three flips give syndrome 00: the error is invisible.")

    heading("Step 3: exact error rate by listing all 8 error patterns")
    patterns = {}
    for flips in product((0, 1), repeat=3):
        errors = [(q, "x") for q, bit in enumerate(flips) if bit]
        patterns[flips] = not one_shot(errors, "0")[1]
    enumerated = {p: sum((p ** sum(f)) * ((1 - p) ** (3 - sum(f))) for f, failed in patterns.items() if failed) for p in RATES}
    print("failing patterns: " + ", ".join("".join(map(str, f)) for f, failed in patterns.items() if failed))
    print("sum of their probabilities = 3p^2(1-p) + p^3 = 3p^2 - 2p^3 "
          f"(max difference from the formula over the sweep: {max(abs(enumerated[p] - formula(p)) for p in RATES):.1e})")

    heading(f"Step 4: random X errors with probability p on each qubit ({SHOTS} seeded shots per input)")
    sweep = {}
    for index, p in enumerate(RATES):
        noise = pauli_channel_noise(p, "x")
        measured = np.mean([logical_error_rate(bit_flip_code(state), state, shots=SHOTS, seed=run_seed(1 + 2 * index + k), noise=noise)
                            for k, state in enumerate(("0", "1"))])
        sigma = np.sqrt(formula(p) * (1 - formula(p)) / (2 * SHOTS))
        sweep[p] = {"measured": float(measured), "formula": formula(p), "sigma": float(sigma)}
        print(f"p = {p:<4}: logical error {measured:.4f}, formula {formula(p):.4f} "
              f"(difference {measured - formula(p):+.4f}, {abs(measured - formula(p)) / sigma if sigma else 0:.1f} sigma);  "
              f"unprotected {p:.4f}")
    print("Below p = 1/2 the code helps; at 1/2 the curves meet (3p^2 - 2p^3 = p); above, it hurts.")
    path = plot(sweep)
    print(f"\nSaved {path}")
    return {"single": single, "no_error": no_error, "multi": multi, "patterns": patterns, "enumerated": enumerated, "sweep": sweep}


if __name__ == "__main__":
    main()
