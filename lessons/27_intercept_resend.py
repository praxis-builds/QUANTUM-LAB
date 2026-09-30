"""Lesson 27: an intercept-resend eavesdropper, and how Alice and Bob catch her."""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
import numpy as np

from _common import SEED, heading, out_dir
from _qkd import bb84_round, qber, sift

N = 20_000
SAMPLE_SIZES = range(1, 21)
TRIALS = 20_000
FRACTIONS = (0.1, 0.25, 0.5, 1.0)


def miss_probability(errors: np.ndarray, k: int, rng: np.random.Generator) -> float:
    """Reveal k random sifted bits (without replacement); Eve is missed if none of them disagree."""
    misses = 0
    for _ in range(TRIALS):
        misses += not errors[rng.choice(len(errors), size=k, replace=False)].any()
    return misses / TRIALS


def plot(detection: dict):
    ks = list(detection)
    figure, axis = plt.subplots(figsize=(7, 4.5))
    axis.semilogy(ks, [detection[k]["formula"] for k in ks], "-", label="(3/4)^k")
    axis.semilogy(ks, [detection[k]["simulated"] for k in ks], "o", label=f"simulated ({TRIALS} trials per k)")
    axis.set_xlabel("sample bits compared publicly, k")
    axis.set_ylabel("P(Eve goes unnoticed)")
    axis.set_title("Intercept-resend on every qubit")
    axis.legend()
    figure.tight_layout()
    path = out_dir() / "27_detection.png"
    figure.savefig(path, dpi=130)
    plt.close(figure)
    return path


def main() -> dict:
    heading(f"Step 1: Eve measures every qubit in a random basis and resends ({N} qubits)")
    full = bb84_round(N, np.random.default_rng(SEED), base_run=1000, eve_fraction=1.0)
    keep = sift(full)
    errors = full["alice_bits"][keep] != full["bob_bits"][keep]
    eve_right_basis = full["eve_bases"][keep] == full["alice_bases"][keep]
    full_qber = float(errors.mean())
    by_eve_basis = {"right": float(errors[eve_right_basis].mean()), "wrong": float(errors[~eve_right_basis].mean())}
    print(f"QBER on the sifted key = {full_qber:.4f}  (expected 1/4)")
    print(f"  where Eve guessed Alice's basis ({eve_right_basis.mean():.3f} of bits): error rate {by_eve_basis['right']:.4f}")
    print(f"  where she guessed wrong: error rate {by_eve_basis['wrong']:.4f}  -> 1/2 x 1/2 = 1/4 overall")

    heading("Step 2: catching her by comparing k sample bits in public")
    rng = np.random.default_rng(SEED + 1)
    detection = {}
    for k in SAMPLE_SIZES:
        detection[k] = {"formula": 0.75**k, "simulated": miss_probability(errors, k, rng)}
    for k in (1, 2, 5, 10, 20):
        print(f"k = {k:>2}: P(miss) simulated {detection[k]['simulated']:.4f}, formula (3/4)^k = {detection[k]['formula']:.4f}")
    k_needed = math.ceil(math.log(1e-6) / math.log(0.75))
    print(f"For P(miss) below one in a million, compare k = {k_needed} bits (then throw them away: they are public).")

    heading("Step 3: a partial attack on a fraction f of the qubits")
    partial = {}
    for index, f in enumerate(FRACTIONS):
        round_ = full if f == 1.0 else bb84_round(N, np.random.default_rng(SEED + 2 + index), base_run=2000 + 100 * index, eve_fraction=f)
        kept = sift(round_)
        knows = round_["intercepted"][kept] & (round_["eve_bases"][kept] == round_["alice_bases"][kept])
        right = np.where(round_["intercepted"][kept], round_["eve_bits"][kept] == round_["alice_bits"][kept], False)
        wrong = round_["intercepted"][kept] & (round_["eve_bases"][kept] != round_["alice_bases"][kept])
        errs = round_["alice_bits"][kept] != round_["bob_bits"][kept]
        partial[f] = {"qber": qber(round_), "knows": float(knows.mean()),
                      "intercepted": float(round_["intercepted"][kept].mean()),
                      "errors_elsewhere": int(errs[~wrong].sum()), "error_rate_wrong_basis": float(errs[wrong].mean()),
                      "wrong_basis_count": int(wrong.sum()),
                      "right_when_measured": float(right.sum() / max(round_["intercepted"][kept].sum(), 1))}
        print(f"f = {f:<4}: QBER {partial[f]['qber']:.4f} (f/4 = {f / 4:.4f});  Eve knows {partial[f]['knows']:.4f} of the sifted key "
              f"for certain (f/2 = {f / 2:.4f})")
    print("Errors appear only where Eve measured in the wrong basis: " +
          ", ".join(f"f = {f}: {partial[f]['errors_elsewhere']} elsewhere, {partial[f]['error_rate_wrong_basis']:.3f} there" for f in FRACTIONS))
    print("Eve learns a bit for certain exactly when she happened to use Alice's basis. Every bit she")
    print("learns costs her a 1/2 chance of disturbing another. Information and disturbance come together.")
    path = plot(detection)
    print(f"\nSaved {path}")
    return {"qber": full_qber, "by_eve_basis": by_eve_basis, "sifted": int(keep.sum()), "detection": detection,
            "k_needed": k_needed, "partial": partial,
            "eve_right_overall": float(np.mean(full["eve_bits"][keep] == full["alice_bits"][keep]))}


if __name__ == "__main__":
    main()
