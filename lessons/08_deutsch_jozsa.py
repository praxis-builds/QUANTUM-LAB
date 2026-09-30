"""Lesson 08: Deutsch-Jozsa. Constant or balanced, in one oracle call."""

from __future__ import annotations

from math import comb

import numpy as np
from qiskit.quantum_info import Statevector

from _common import SEED, heading
from _oracles import balanced_tables, constant_tables, describe, deutsch_jozsa_circuit
from praxis_quantum_lab.qiskit_experiments import ideal_counts

SHOTS = 1000
SIZES = (1, 2, 3, 4)
N4_SAMPLE = 50  # n = 4 has comb(16, 8) = 12870 balanced functions: test a seeded sample
RANDOM_TRIALS = 20_000


def tables_for(n: int) -> tuple[list, list]:
    limit = N4_SAMPLE if n == 4 else None
    return constant_tables(n), balanced_tables(n, limit=limit, seed=SEED)


def p_all_zeros(table) -> float:
    n = int(np.log2(len(table)))
    return float(Statevector(deutsch_jozsa_circuit(table)).probabilities(list(range(n)))[0])


def deterministic_queries(table) -> int:
    """Query x = 0, 1, 2, ... and stop at the first disagreement (balanced) or after
    2^(n-1) + 1 equal answers (then f must be constant: a balanced f has only 2^(n-1) of each)."""
    half = len(table) // 2
    for count, x in enumerate(range(len(table)), start=1):
        if table[x] != table[0]:
            return count
        if count == half + 1:
            return count
    raise AssertionError("unreachable")


def random_tester_error(n: int, k: int) -> float:
    """Exact chance that k distinct random queries of a balanced f all agree (so a
    'say constant if all agree' tester is wrong): 2 * C(N/2, k) / C(N, k)."""
    size = 2**n
    return 2 * comb(size // 2, k) / comb(size, k)


def simulated_tester_error(n: int, k: int, rng: np.random.Generator, tables: list) -> float:
    wrong = 0
    for trial in range(RANDOM_TRIALS):
        table = tables[trial % len(tables)]
        picks = rng.choice(len(table), size=k, replace=False)
        wrong += len({table[x] for x in picks}) == 1
    return wrong / RANDOM_TRIALS


def main() -> dict:
    heading("Step 1: every constant and balanced oracle for n = 2, one query each")
    constant, balanced = tables_for(2)
    n2 = {}
    for table in constant + balanced:
        kind = "constant" if table in constant else "balanced"
        counts = ideal_counts(deutsch_jozsa_circuit(table, measure=True), shots=SHOTS, seed=SEED)
        n2[describe(table)] = {"kind": kind, "p_00": p_all_zeros(table), "counts": counts}
        print(f"f = {describe(table)} ({kind}):  P(00) = {n2[describe(table)]['p_00']:.6f}   counts = {counts}")
    print("(f is listed for x = 0, 1, 2, 3.) Constant -> always 00. Balanced -> never 00.")

    heading("Step 2: n = 1 to 4, P(all zeros) after ONE query")
    sizes = {}
    for n in SIZES:
        constant, balanced = tables_for(n)
        p_constant = [p_all_zeros(t) for t in constant]
        p_balanced = [p_all_zeros(t) for t in balanced]
        sizes[n] = {
            "constant_checked": len(constant), "balanced_checked": len(balanced),
            "min_p_constant": min(p_constant), "max_p_balanced": max(p_balanced),
            "classical_worst_case": max(deterministic_queries(t) for t in constant + balanced),
        }
        note = f" (seeded sample of {comb(2**n, 2**(n - 1))})" if n == 4 else " (all of them)"
        print(f"n = {n}: {len(constant)} constant, {len(balanced)} balanced{note}. "
              f"min P(0..0) constant = {sizes[n]['min_p_constant']:.6f}, "
              f"max P(0..0) balanced = {sizes[n]['max_p_balanced']:.2e}")

    heading("Step 3: the classical baseline, counted honestly")
    for n in SIZES:
        print(f"n = {n}: a certain classical answer needs up to 2^(n-1) + 1 = {2 ** (n - 1) + 1} queries "
              f"(worst case found above: {sizes[n]['classical_worst_case']}); quantum: 1")
    print("The worst case is a constant f: after 2^(n-1) equal answers it could still be balanced.")
    rng = np.random.default_rng(SEED)
    _, balanced4 = tables_for(4)
    random_tester = {}
    for k in (2, 3, 4):
        exact = random_tester_error(4, k)
        simulated = simulated_tester_error(4, k, rng, balanced4)
        random_tester[k] = {"exact": exact, "simulated": simulated}
        print(f"n = 4, random classical tester with {k} queries: wrong on a balanced f with probability "
              f"{exact:.4f} (simulated {simulated:.4f})")
    print("A classical tester that accepts a small error rate needs only a few queries.")
    print("The quantum gap is for a CERTAIN answer, and only under the constant-or-balanced promise.")
    return {"n2": n2, "sizes": sizes, "random_tester": random_tester}


if __name__ == "__main__":
    main()
