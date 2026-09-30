"""Lesson 17: Grover on n qubits. Each step rotates toward the answer; too many steps overshoot."""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
import numpy as np
from qiskit.quantum_info import Statevector

from _common import SEED, heading, out_dir
from _grover_n import bbht_calls, flip_if_equal, grover_circuit, marked_item_oracle, optimal_iterations, success_probability
from praxis_quantum_lab.qiskit_experiments import ideal_counts

SIZES = range(2, 9)
MARKED = 5  # the marked item for every n (any value works)
UNKNOWN_N = 6
UNKNOWN_M = (1, 2, 4, 8)
BBHT_TRIALS = 5000
SHOTS = 1000


def success_curve(n: int, marked: set[int], iterations: int) -> list[float]:
    """P(marked) after k = 0, 1, ..., iterations Grover steps, from the simulated state vector
    (one iteration circuit applied repeatedly), not from the formula."""
    def oracle(circuit):
        for item in sorted(marked):
            flip_if_equal(circuit, list(range(n)), item)
    step = grover_circuit(n, oracle, 1)
    step.data = step.data[n:]  # drop the initial H layer: one oracle + diffusion
    state = Statevector(grover_circuit(n, oracle, 0))
    curve = []
    for _ in range(iterations + 1):
        probabilities = state.probabilities()
        curve.append(float(sum(probabilities[m] for m in marked)))
        state = state.evolve(step)
    return curve


def plot(curves: dict, unknown: dict):
    figure, (left, right) = plt.subplots(1, 2, figsize=(12, 4.2))
    for n, points in curves.items():
        left.plot(range(len(points)), points, "o-", markersize=3, label=f"n = {n}")
    left.set_xlabel("Grover iterations k")
    left.set_ylabel("P(marked item)")
    left.set_title("One marked item out of 2^n")
    left.legend(fontsize=8, ncol=2)
    for M, points in unknown["curves"].items():
        right.plot(range(len(points)), points, "o-", markersize=3, label=f"M = {M}")
    right.axvline(unknown["k_for_M1"], color="black", linestyle="--", linewidth=1, label="k tuned for M = 1")
    right.set_xlabel("Grover iterations k")
    right.set_title(f"n = {UNKNOWN_N}: the best k depends on M")
    right.legend(fontsize=8)
    figure.tight_layout()
    path = out_dir() / "17_grover_iterations.png"
    figure.savefig(path, dpi=130)
    plt.close(figure)
    return path


def main() -> dict:
    heading("Step 1: optimal iterations and success for n = 2..8 (one marked item)")
    optimum, curves = {}, {}
    for n in SIZES:
        N = 2**n
        k = optimal_iterations(N)
        curves[n] = success_curve(n, {MARKED % N}, 2 * k + 2)
        optimum[n] = {"k": k, "estimate": math.pi / 4 * math.sqrt(N), "p": curves[n][k],
                      "formula": success_probability(k, N), "p_double": curves[n][2 * k]}
        print(f"n = {n}: N = {N:>3}, (pi/4) sqrt(N) = {optimum[n]['estimate']:5.2f} -> k = {k:>2};  "
              f"P(success) = {optimum[n]['p']:.4f} (formula {optimum[n]['formula']:.4f})")
    counts = ideal_counts(grover_circuit(4, marked_item_oracle(4, MARKED), optimum[4]["k"], measure=True), shots=SHOTS, seed=SEED)
    print(f"Aer check, n = 4, k = {optimum[4]['k']}: {counts.get(format(MARKED, '04b'), 0)}/{SHOTS} shots gave the marked item")

    heading("Step 2: too many iterations (over-rotation)")
    for n in SIZES:
        row = optimum[n]
        print(f"n = {n}: P at k = {row['k']:>2}: {row['p']:.4f};  at k = {2 * row['k']:>2}: {row['p_double']:.4f}")
    print("Each iteration turns the state by the same angle. Past the marked direction it keeps")
    print("turning, and the success probability falls again (it comes back later, periodically).")

    heading(f"Step 3: unknown number of answers M (n = {UNKNOWN_N}, N = {2 ** UNKNOWN_N})")
    N = 2**UNKNOWN_N
    k1 = optimal_iterations(N, 1)
    rng = np.random.default_rng(SEED)
    unknown = {"k_for_M1": k1, "curves": {}, "rows": {}}
    for M in UNKNOWN_M:
        marked = set(range(3, 3 + M))
        unknown["curves"][M] = success_curve(UNKNOWN_N, marked, 2 * k1)
        best = optimal_iterations(N, M)
        mean_bbht = float(np.mean([bbht_calls(N, M, rng) for _ in range(BBHT_TRIALS)]))
        unknown["rows"][M] = {"k_opt": best, "p_opt": unknown["curves"][M][best], "p_at_k1": unknown["curves"][M][k1],
                              "bbht": mean_bbht, "sqrt": math.pi / 4 * math.sqrt(N / M), "classical": (N + 1) / (M + 1)}
        row = unknown["rows"][M]
        print(f"M = {M}: best k = {best} (P = {row['p_opt']:.3f});  using k = {k1} (tuned for M = 1): P = {row['p_at_k1']:.3f};  "
              f"BBHT mean calls {mean_bbht:.1f};  classical mean {row['classical']:.1f}")
    print("With k fixed for M = 1, M = 4 collapses but M = 8 happens to land near 1 again: the")
    print("rotation is periodic, so a wrong k gives an unpredictable result, not a reliable one.")
    print("BBHT picks k at random below a growing bound, so it never needs to know M; its cost")
    print("still grows like sqrt(N/M). Quantum counting (phase estimation on the Grover step,")
    print("Lesson 12) can estimate M first instead.")
    path = plot(curves, unknown)
    print(f"\nSaved {path}")
    return {"optimum": optimum, "curves": curves, "counts": counts, "unknown": unknown}


if __name__ == "__main__":
    main()
