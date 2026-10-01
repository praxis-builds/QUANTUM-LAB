"""Lesson 28: from a raw BB84 key to a secret key (error correction + privacy amplification)."""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
import numpy as np

from _common import SEED, heading, out_dir
from _qkd import bb84_round, binary_entropy, parity_error_correction, sift, toeplitz_hash

N = 20_000
SAMPLE = 1000  # sifted bits revealed to estimate the error rate (then discarded)
CHECK_BITS = 32  # length of the hash Alice and Bob compare after error correction
SAFETY = 100  # extra bits removed in privacy amplification (a stand-in, NOT a finite-key analysis)
SCENARIOS = {"noise 0.01": {"noise_p": 0.01}, "noise 0.03": {"noise_p": 0.03}, "noise 0.05": {"noise_p": 0.05},
             "noise 0.08": {"noise_p": 0.08}, "noise 0.10": {"noise_p": 0.10}, "noise 0.12": {"noise_p": 0.12},
             "Eve, every qubit": {"eve_fraction": 1.0}}
THRESHOLD = 0.11


def shor_preskill_rate(q: float) -> float:
    """Asymptotic secret-key fraction for BB84 with equal bit and phase error rates q: 1 - 2h(q)."""
    return max(0.0, 1 - 2 * binary_entropy(q))


def distill(round_: dict, rng: np.random.Generator, sample_size: int = SAMPLE) -> dict:
    """Sample -> estimate Q -> error correction -> privacy amplification (also used by the dashboard)."""
    keep = sift(round_)
    alice, bob = round_["alice_bits"][keep], round_["bob_bits"][keep]
    sample = rng.choice(len(alice), size=sample_size, replace=False)
    q_est = float(np.mean(alice[sample] != bob[sample]))
    # The sample only estimates Q. Privacy amplification must assume the worst plausible value:
    # a 3-sigma upper bound (a simple stand-in for a proper finite-key analysis).
    q_bound = q_est + 3 * math.sqrt(max(q_est * (1 - q_est), 1 / sample_size) / sample_size)
    rest = np.setdiff1d(np.arange(len(alice)), sample)
    alice, bob = alice[rest], bob[rest]
    n = len(alice)
    row = {"sifted": int(keep.sum()), "n": n, "q_est": q_est, "q_bound": q_bound, "q_true": float(np.mean(alice != bob)),
           "sample_errors": int(np.sum(round_["alice_bits"][keep][sample] != round_["bob_bits"][keep][sample])),
           "asymptotic_fraction": shor_preskill_rate(q_est)}
    if q_bound >= THRESHOLD:
        return {**row, "status": f"ABORT: QBER could be up to {q_bound:.3f} >= {THRESHOLD}", "m": 0}
    corrected, leaked = parity_error_correction(alice, bob, rng, estimated_q=q_est)
    check_seed = rng.integers(0, 2, n + CHECK_BITS - 1)
    same_hash = bool(np.array_equal(toeplitz_hash(alice, CHECK_BITS, check_seed), toeplitz_hash(corrected, CHECK_BITS, check_seed)))
    leaked += CHECK_BITS
    m = n - leaked - math.ceil(n * binary_entropy(q_bound)) - SAFETY
    row.update({"leaked": leaked, "residual_errors": int(np.sum(alice != corrected)), "hash_match": same_hash,
                "shannon_minimum": n * binary_entropy(q_est), "m": max(m, 0)})
    if not same_hash:
        return {**row, "status": "ABORT: keys still differ after error correction", "m": 0}
    if m <= 0:
        return {**row, "status": "ABORT: nothing left after privacy amplification", "m": 0}
    pa_seed = rng.integers(0, 2, n + m - 1)  # public: announced after error correction
    key_alice, key_bob = toeplitz_hash(alice, m, pa_seed), toeplitz_hash(corrected, m, pa_seed)
    row.update({"status": "key", "keys_equal": bool(np.array_equal(key_alice, key_bob)), "fraction": m / n,
                "key_ones": float(key_alice.mean())})
    return row


def plot(rows: dict):
    fine = np.linspace(0.001, 0.13, 300)
    figure, axis = plt.subplots(figsize=(7, 4.5))
    axis.plot(fine, [shor_preskill_rate(q) for q in fine], "-", label="Shor–Preskill limit 1 − 2h(Q)")
    points = [(r["q_est"], r["fraction"]) for r in rows.values() if r["status"] == "key"]
    axis.plot([q for q, _ in points], [f for _, f in points], "o", label="this toy pipeline (measured)")
    axis.axvline(THRESHOLD, color="grey", linestyle="--", linewidth=1, label="Q = 11%")
    axis.set_xlabel("estimated error rate Q")
    axis.set_ylabel("secret key bits per sifted bit")
    axis.set_ylim(0, 1)
    axis.legend(fontsize=8)
    axis.set_title("How much secret key survives")
    figure.tight_layout()
    path = out_dir() / "28_key_rate.png"
    figure.savefig(path, dpi=130)
    plt.close(figure)
    return path


def main() -> dict:
    heading("Step 1: the Toeplitz hash used for privacy amplification is linear")
    rng = np.random.default_rng(SEED)
    x, y, seed_bits = rng.integers(0, 2, 64), rng.integers(0, 2, 64), rng.integers(0, 2, 64 + 16 - 1)
    linear = bool(np.array_equal(toeplitz_hash(x ^ y, 16, seed_bits), toeplitz_hash(x, 16, seed_bits) ^ toeplitz_hash(y, 16, seed_bits)))
    print(f"T(x XOR y) = T(x) XOR T(y) for random 64-bit x, y and a 16 x 64 Toeplitz matrix: {linear}")

    heading(f"Step 2: {N} qubits per scenario -> sample {SAMPLE} bits -> correct errors -> amplify privacy")
    rows = {}
    for index, (name, options) in enumerate(SCENARIOS.items()):
        round_ = bb84_round(N, np.random.default_rng(SEED + 10 + index), base_run=3000 + 100 * index, **options)
        rows[name] = distill(round_, np.random.default_rng(SEED + 50 + index))
        r = rows[name]
        if r["status"] == "key":
            print(f"{name:<16}: Q est {r['q_est']:.3f} (bound {r['q_bound']:.3f}, true {r['q_true']:.3f}); n = {r['n']}; EC revealed "
                  f"{r['leaked']} bits (Shannon minimum {r['shannon_minimum']:.0f}), {r['residual_errors']} errors left; "
                  f"final key {r['m']} bits = {r['fraction']:.3f} n (limit {r['asymptotic_fraction']:.3f}); keys equal: {r['keys_equal']}")
        else:
            print(f"{name:<16}: Q est {r['q_est']:.3f} -> {r['status']}")
    print(f"Final key length m = n - (bits revealed in error correction) - n h(Q_bound) - {SAFETY}.")
    print("Error correction costs at least n h(Q) public bits; Eve's possible knowledge costs another n h(Q).")
    path = plot(rows)
    print(f"\nSaved {path}")
    return {"linear": linear, "rows": rows}


if __name__ == "__main__":
    main()
