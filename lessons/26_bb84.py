"""Lesson 26: BB84 quantum key distribution without an eavesdropper."""

from __future__ import annotations

import math

import numpy as np

from _common import SEED, heading
from _qkd import X, bb84_round, qber, sift

N = 20_000
NOISE = (0.01, 0.03, 0.05, 0.1)
SHOWN = 12


def basis_name(b: int) -> str:
    return "X" if b == X else "Z"


def main() -> dict:
    heading(f"Step 1: the first {SHOWN} qubits, one by one")
    ideal = bb84_round(N, np.random.default_rng(SEED), base_run=100)
    keep = sift(ideal)
    print("qubit  Alice bit  Alice basis  Bob basis  Bob result  kept?  agree?")
    for i in range(SHOWN):
        agree = "yes" if ideal["alice_bits"][i] == ideal["bob_bits"][i] else "no"
        print(f"{i:>5}  {ideal['alice_bits'][i]:>9}  {basis_name(ideal['alice_bases'][i]):>11}  {basis_name(ideal['bob_bases'][i]):>9}  "
              f"{ideal['bob_bits'][i]:>10}  {'yes' if keep[i] else 'no':>5}  {agree if keep[i] else '(random)':>6}")
    print("When the bases differ, Bob's result is a coin flip, so those positions are thrown away.")

    heading(f"Step 2: {N} qubits on a perfect channel")
    sift_rate = float(keep.mean())
    ideal_qber = qber(ideal)
    print(f"bases matched on {keep.sum()} of {N} qubits: sifting rate {sift_rate:.4f} (expected 0.5)")
    print(f"error rate on the sifted key (QBER) = {ideal_qber:.4f}")

    heading("Step 3: a noisy channel (each qubit flipped with probability p, in either basis)")
    noisy = {}
    for index, p in enumerate(NOISE):
        round_ = bb84_round(N, np.random.default_rng(SEED + 1 + index), base_run=200 + 100 * index, noise_p=p)
        n_kept = int(sift(round_).sum())
        noisy[p] = {"qber": qber(round_), "kept": n_kept, "sigma": math.sqrt(p * (1 - p) / n_kept)}
        print(f"p = {p:<4}: QBER = {noisy[p]['qber']:.4f} on {n_kept} sifted bits "
              f"({(noisy[p]['qber'] - p) / noisy[p]['sigma']:+.1f} sigma from p)")
    print("Noise and eavesdropping both show up as errors; Alice and Bob cannot tell them apart,")
    print("so every error must be treated as if Eve caused it (Lesson 28).")
    return {"first": {k: ideal[k][:SHOWN].tolist() for k in ("alice_bits", "alice_bases", "bob_bases", "bob_bits")},
            "sift_rate": sift_rate, "ideal_qber": ideal_qber, "kept": int(keep.sum()), "noisy": noisy}


if __name__ == "__main__":
    main()
