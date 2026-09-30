"""Lesson 15: Shor's algorithm for N = 21, with generic permutation unitaries."""

from __future__ import annotations

import math

import numpy as np

from _common import SEED, heading
from _shor import (
    factor_with_shor,
    factors_from_order,
    order,
    period_from_measurement,
    readout_distribution,
    run_gives_order,
    sample_runs,
    shor_circuit,
    work_qubits,
)

N = 21
T = 2 * work_qubits(N)  # 10 counting qubits
SHOTS = 2000
REPEATS = 500
UNITS = [a for a in range(2, N) if math.gcd(a, N) == 1]


def main() -> dict:
    heading("Step 1: how the circuit grew from N = 15")
    growth = {}
    for n_value in (15, 21):
        n = work_qubits(n_value)
        growth[n_value] = {"work": n, "counting": 2 * n, "total": 3 * n, "matrix_size": 2 ** (n + 1)}
        print(f"N = {n_value}: {n} work + {2 * n} counting = {3 * n} qubits; each controlled multiplier acts on "
              f"{n + 1} qubits ({2 ** (n + 1)} x {2 ** (n + 1)} as a matrix)")
    circuit = shor_circuit(2, N)
    print(f"a = 2: a^(2^k) mod 21 for k = 0..{T - 1}: {[pow(2, 2**k, N) for k in range(T)]}")
    print(f"built circuit: {circuit.num_qubits} qubits, {dict(circuit.count_ops())}")

    heading("Step 2: exact readout for a = 2 (r = 6 is not a power of 2, so peaks spread)")
    probabilities = readout_distribution(2, N)
    top = sorted(range(2**T), key=lambda m: -probabilities[m])[:8]
    readout = []
    for m in sorted(top):
        candidate = period_from_measurement(m, T, N)
        readout.append({"m": m, "p": float(probabilities[m]), "candidate": candidate})
        print(f"m = {m:>4} ({m / 2**T:.4f}): P = {probabilities[m]:.3f} -> candidate r = {candidate}"
              f"{'  (r found)' if pow(2, candidate, N) == 1 else ''}")
    print("Peaks sit near s/6 x 1024 = 0, 170.7, 341.3, 512, 682.7, 853.3. Only s = 1 and 5")
    print("(s shares no factor with 6) give r = 6; s = 2, 4 give 3 and s = 3 gives 2.")

    heading(f"Step 3: all {len(UNITS)} values of a, {SHOTS} seeded Aer shots each")
    per_a, runs_for = {}, {}
    for a in UNITS:
        runs_for[a] = sample_runs(a, N, SHOTS, SEED + a)
        r = order(a, N)
        exact = float(sum(p for m, p in enumerate(readout_distribution(a, N)) if run_gives_order(a, N, m, T)))
        sampled = sum(run_gives_order(a, N, m, T) for m in runs_for[a]) / SHOTS
        factors, reason = factors_from_order(a, N, r)
        per_a[a] = {"r": r, "exact": exact, "sampled": sampled, "factors": factors, "reason": reason}
        result = f"{factors[0]} x {factors[1]}" if factors else f"no factors ({reason})"
        print(f"a = {a:>2}: r = {r}; P(run gives r) exact {exact:.3f}, Aer {sampled:.3f}; then {result}")

    heading(f"Step 4: the whole algorithm, {REPEATS} seeded repeats (random a, retry on failure)")
    rng = np.random.default_rng(SEED)
    repeats = [factor_with_shor(N, rng, runs_for) for _ in range(REPEATS)]
    found = sum(r["factors"] == (3, 7) for r in repeats)
    lucky = sum(r["quantum_runs"] == 0 for r in repeats)
    quantum = [r["quantum_runs"] for r in repeats if r["quantum_runs"] > 0]
    summary = {"found": found, "lucky": lucky, "mean_quantum_runs": float(np.mean([r["quantum_runs"] for r in repeats])),
               "mean_runs_when_quantum": float(np.mean(quantum)), "max_quantum_runs": max(quantum)}
    print(f"factors 3 x 7 found in {found}/{REPEATS} repeats; {lucky} by a lucky gcd(a, 21) > 1")
    print(f"quantum runs per repeat: mean {summary['mean_quantum_runs']:.2f}; "
          f"when a quantum run was needed: mean {summary['mean_runs_when_quantum']:.2f}, max {summary['max_quantum_runs']}")
    print("Honesty: each multiplier here is a full 64 x 64 permutation matrix handed to the simulator.")
    print("That is compiled Shor at its most extreme: no gate-level circuit for it exists in this lab.")
    return {"growth": growth, "readout": readout, "per_a": per_a, "summary": summary, "qubits": circuit.num_qubits}


if __name__ == "__main__":
    main()
