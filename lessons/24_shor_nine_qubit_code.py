"""Lesson 24: Shor's 9-qubit code corrects ANY single-qubit error (X, Y or Z)."""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
import numpy as np
from qiskit.quantum_info import Statevector, partial_trace, state_fidelity
from qiskit_aer import AerSimulator

from _common import SEED, heading, out_dir
from _qec import INPUT_STATES, depolarizing_channel_noise, logical_error_rate, shor9_code

RY_ANGLE = 0.7
RY_ERRORS = ([], [(4, "x")], [(7, "y")], [(0, "z")], [(8, "y")])
TWO_ERRORS = {
    "X on 0 and X on 3 (different blocks)": [(0, "x"), (3, "x")],
    "X on 0 and X on 1 (same block)": [(0, "x"), (1, "x")],
    "Z on 0 and Z on 1 (same block)": [(0, "z"), (1, "z")],
    "Z on 0 and Z on 3 (different blocks)": [(0, "z"), (3, "z")],
    "X on 2 and Z on 7": [(2, "x"), (7, "z")],
}
RATES = (0.001, 0.003, 0.01, 0.03, 0.05, 0.1, 0.2, 0.3)
SWEEP_STATES = ("0", "+", "+i")  # one eigenstate of each Pauli: each is flipped by two of X, Y, Z
SHOTS = 4000


def one_shot(state: str, errors) -> tuple[bool, str]:
    """(state survived?, syndrome registers as printed by Aer: phase, block2, block1, block0)."""
    memory = AerSimulator(method="stabilizer").run(shor9_code(state, errors), shots=1, seed_simulator=SEED, memory=True)
    out, *syndromes = memory.result().get_memory()[0].split()
    return int(out) == (1 if state in ("1", "-", "-i") else 0), " ".join(syndromes)


def ry_fidelity(errors, *, correct: bool = True) -> float:
    """Fidelity of the decoded qubit 0 (reduced state, phases included) with the input RY(angle)|0>.
    With one fixed Pauli error every syndrome measurement has a certain outcome, so a single
    statevector run gives the exact final state."""
    simulator = AerSimulator(method="statevector")
    circuit = shor9_code("0", errors, correct=correct, ry_angle=RY_ANGLE, save_state=True)
    state = Statevector(simulator.run(circuit, shots=1, seed_simulator=SEED).result().get_statevector())
    reduced = partial_trace(state, list(range(1, state.num_qubits)))
    target = Statevector([math.cos(RY_ANGLE / 2), math.sin(RY_ANGLE / 2)])
    return round(float(state_fidelity(reduced, target)), 12) + 0.0  # + 0.0 turns -0.0 into 0.0


def plot(sweep: dict):
    rates = list(sweep)
    figure, axis = plt.subplots(figsize=(7, 4.5))
    seen = [p for p in rates if sweep[p]["encoded"] > 0]
    unseen = [p for p in rates if sweep[p]["encoded"] == 0]
    axis.loglog(seen, [sweep[p]["encoded"] for p in seen], "o-", label="Shor's 9-qubit code (measured)")
    total = SHOTS * len(SWEEP_STATES)
    if unseen:
        axis.loglog(unseen, [1 / total] * len(unseen), "v", color="tab:blue",
                    label=f"no logical error in {total:,} shots (below this line)")
    axis.loglog(rates, [2 * p / 3 for p in rates], "k:", label="one bare qubit: 2p/3")
    axis.set_xlabel("depolarizing probability p per qubit")
    axis.set_ylabel("logical error rate (mean over |0>, |+>, |+i>)")
    axis.set_title("Nine qubits against one")
    axis.legend(fontsize=8)
    figure.tight_layout()
    path = out_dir() / "24_shor_nine_qubit_code.png"
    figure.savefig(path, dpi=130)
    plt.close(figure)
    return path


def main() -> dict:
    heading("Step 1: every single-qubit Pauli (X, Y, Z on each of 9 qubits) on all 6 inputs")
    checks, syndromes = {}, {}
    for qubit in range(9):
        for pauli in "xyz":
            results = [one_shot(state, [(qubit, pauli)]) for state in INPUT_STATES]
            checks[(qubit, pauli)] = all(ok for ok, _ in results)
            syndromes[(qubit, pauli)] = results[0][1]
    no_error = all(one_shot(state, [])[0] for state in INPUT_STATES)
    passed = sum(checks.values())
    print(f"corrected: {passed} of {len(checks)} single errors x 6 inputs, and no-error on all inputs: {no_error}")
    for key in ((4, "x"), (4, "z"), (4, "y"), (8, "x")):
        print(f"  {key[1].upper()} on qubit {key[0]}: syndromes (phase, block2, block1, block0) = {syndromes[key]}")
    print("X errors light up one block's parity checks; Z errors light up the block-to-block checks;")
    print("Y lights up both. That is the bit-flip code inside each block, and the phase-flip code across them.")

    heading(f"Step 2: a non-stabilizer input RY({RY_ANGLE})|0> (exact, statevector)")
    ry = {}
    for errors in RY_ERRORS:
        label = " + ".join(f"{p.upper()}{q}" for q, p in errors) or "no error"
        ry[label] = ry_fidelity(errors)
        print(f"{label:<9}: fidelity of the decoded qubit with the input = {ry[label]:.12f}")
    ry["Y0 without correction"] = ry_fidelity([(0, "y")], correct=False)
    print(f"Y0 without the correction round: fidelity = {ry['Y0 without correction']:.12f}  (the error gets through)")

    heading("Step 3: two errors")
    two = {}
    for label, errors in TWO_ERRORS.items():
        two[label] = all(one_shot(state, errors)[0] for state in INPUT_STATES)
        print(f"{label:<38}: {'corrected' if two[label] else 'LOGICAL ERROR'}")
    print("One bit flip per block and one phase flip overall can be fixed; more of either cannot.")

    heading(f"Step 4: random depolarizing errors on all 9 qubits ({SHOTS} seeded shots per input)")
    sweep = {}
    for index, p in enumerate(RATES):
        noise = depolarizing_channel_noise(p)
        encoded = np.mean([logical_error_rate(shor9_code(s), s, shots=SHOTS, seed=SEED + index, noise=noise) for s in SWEEP_STATES])
        sweep[p] = {"encoded": float(encoded), "bare": 2 * p / 3}
        print(f"p = {p:<5}: encoded {encoded:.4f}   bare qubit {2 * p / 3:.4f}   "
              f"{'better' if encoded < 2 * p / 3 else 'WORSE'}")
    path = plot(sweep)
    print(f"\nSaved {path}")
    return {"checks": checks, "no_error": no_error, "syndromes": syndromes, "ry": ry,
            "two": two, "sweep": sweep}


if __name__ == "__main__":
    main()
