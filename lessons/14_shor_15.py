"""Lesson 14: Shor's algorithm for N = 15 on local Aer."""

from __future__ import annotations

import math
from collections import Counter

import numpy as np
from qiskit.quantum_info import Operator

from _common import SEED, heading
from _shor import (
    controlled_mod15_multiplier,
    factor_with_shor,
    factors_from_order,
    order,
    period_from_measurement,
    readout_distribution,
    run_gives_order,
    sample_runs,
    shor_circuit,
)

N = 15
T = 8  # counting qubits = 2n, n = 4 work qubits
SHOTS = 2000
REPEATS = 500
UNITS = [a for a in range(2, N) if math.gcd(a, N) == 1]


def multiplier_table(m: int) -> dict[int, int]:
    """Where the controlled circuit (control = 1) sends each y = 0..15."""
    unitary = Operator(controlled_mod15_multiplier(m)).data
    return {y: int(np.argmax(np.abs(unitary[:, (y << 1) | 1]))) >> 1 for y in range(16)}


def main() -> dict:
    heading("Step 1: gate-level 'multiply by m mod 15' (SWAP rotations, then NOT if m = -2^j)")
    tables = {}
    for m in sorted({pow(a, 2**k, N) for a in UNITS for k in range(T)} - {1}):
        tables[m] = multiplier_table(m)
        correct = all(tables[m][y] == m * y % N for y in range(1, 15))
        print(f"m = {m:>2}: y -> m*y mod 15 correct for y = 1..14: {correct};  0 -> {tables[m][0]}, 15 -> {tables[m][15]}")
    print("Only y = 1..14 matter: the work register starts at 1 and only ever holds powers of a.")

    heading(f"Step 2: the circuit for a = 7 ({T} counting + 4 work qubits)")
    circuit = shor_circuit(7, N, gate_level=True)
    powers = [pow(7, 2**k, N) for k in range(T)]
    print(f"a^(2^k) mod 15 for k = 0..{T - 1}: {powers}  (precomputed classically; 1 = nothing to do)")
    ops = dict(circuit.decompose(["c-x7 mod 15", "c-x4 mod 15"]).count_ops())
    print(f"qubits = {circuit.num_qubits}; gates after unpacking the multipliers: {ops}")

    heading("Step 3: exact readout for a = 7, and what continued fractions make of it")
    probabilities = readout_distribution(7, N, gate_level=True)
    peaks = {m: float(p) for m, p in enumerate(probabilities) if p > 1e-9}
    for m, p in peaks.items():
        candidate = period_from_measurement(m, T, N)
        verdict = "r found" if pow(7, candidate, N) == 1 else "fails the check 7^c = 1 (mod 15)"
        print(f"m = {m:>3} ({m}/256 = {m / 256:.3f}): P = {p:.3f} -> candidate r = {candidate}: {verdict}")

    heading(f"Step 4: every a, {SHOTS} seeded Aer shots each (one shot = one run)")
    per_a, runs_for = {}, {}
    for a in UNITS:
        runs_for[a] = sample_runs(a, N, 4 * REPEATS, SEED + a, gate_level=True)
        shots = runs_for[a][:SHOTS]
        exact = float(sum(p for m, p in enumerate(readout_distribution(a, N, gate_level=True)) if run_gives_order(a, N, m, T)))
        sampled = sum(run_gives_order(a, N, m, T) for m in shots) / SHOTS
        r = order(a, N)
        factors, reason = factors_from_order(a, N, r)
        per_a[a] = {"r": r, "exact": exact, "sampled": sampled, "factors": factors, "reason": reason,
                    "outcomes": dict(sorted(Counter(shots).items()))}
        result = f"{factors[0]} x {factors[1]}" if factors else f"no factors ({reason})"
        print(f"a = {a:>2}: r = {r}; P(run gives r) exact {exact:.3f}, Aer {sampled:.3f}; then {result}")

    heading(f"Step 5: the whole algorithm, {REPEATS} seeded repeats (random a, retry on failure)")
    rng = np.random.default_rng(SEED)
    repeats = [factor_with_shor(N, rng, runs_for) for _ in range(REPEATS)]
    found = sum(r["factors"] == (3, 5) for r in repeats)
    lucky = sum(r["quantum_runs"] == 0 for r in repeats)
    quantum = [r["quantum_runs"] for r in repeats if r["quantum_runs"] > 0]
    summary = {"found": found, "lucky": lucky, "mean_quantum_runs": float(np.mean([r["quantum_runs"] for r in repeats])),
               "mean_runs_when_quantum": float(np.mean(quantum)), "max_quantum_runs": max(quantum)}
    print(f"factors 3 x 5 found in {found}/{REPEATS} repeats; {lucky} by a lucky gcd(a, 15) > 1 (no quantum run)")
    print(f"quantum runs per repeat: mean {summary['mean_quantum_runs']:.2f}; "
          f"when a quantum run was needed: mean {summary['mean_runs_when_quantum']:.2f}, max {summary['max_quantum_runs']}")
    print("Honesty: the multipliers were built from permutations we computed classically, and so were")
    print("the powers a^(2^k). This is 'compiled Shor'. A general circuit for N is much larger.")
    return {"tables": tables, "powers": powers, "peaks": peaks, "per_a": per_a, "summary": summary, "qubits": circuit.num_qubits}


if __name__ == "__main__":
    main()
