"""Lesson 09: Bernstein-Vazirani. Read a hidden bit string s out in one oracle call."""

from __future__ import annotations

from qiskit.quantum_info import Statevector

from _common import SEED, heading
from _oracles import bernstein_vazirani_circuit, bv_table
from praxis_quantum_lab.qiskit_experiments import ideal_counts

SHOTS = 1000
SECRETS = ("101", "011", "0110", "1111", "1001")


def p_secret(s: str) -> float:
    probabilities = Statevector(bernstein_vazirani_circuit(s)).probabilities_dict(list(range(len(s))))
    return float(probabilities.get(s, 0.0))


def classical_recover(s: str) -> tuple[str, int]:
    """Query x = 000..1, 000..10, ...: f(2^k) = s . 2^k = bit k of s. One query per bit."""
    table = bv_table(s)
    n = len(s)
    queries = 0
    bits = []
    for k in range(n):
        bits.append(table[1 << k])
        queries += 1
    return "".join(str(b) for b in reversed(bits)), queries


def main() -> dict:
    heading("Step 1: f(x) = s . x mod 2 for a hidden s; one quantum query")
    runs = {}
    for s in SECRETS:
        counts = ideal_counts(bernstein_vazirani_circuit(s, measure=True), shots=SHOTS, seed=SEED)
        runs[s] = {"p_secret": p_secret(s), "counts": counts}
        print(f"hidden s = {s}:  P(measure s) = {runs[s]['p_secret']:.6f}   counts over {SHOTS} shots = {counts}")
    print("Every shot returns s itself: one oracle call, the whole string.")

    heading("Step 2: why it works")
    print("After the oracle the input amplitudes are (-1)^(s.x) / sqrt(2^n). That is exactly")
    print("H applied to |s>, so the final H gates map it back to |s> with probability 1.")

    heading("Step 3: the classical baseline")
    classical = {}
    for s in SECRETS:
        found, queries = classical_recover(s)
        classical[s] = {"found": found, "queries": queries}
        print(f"hidden s = {s}: classical recovered {found} with {queries} queries (one per bit); quantum: 1")
    print("No classical method can do better: each answer f(x) is ONE bit, and s has n bits,")
    print("so n queries are needed. The gap is n against 1, not exponential.")
    return {"runs": runs, "classical": classical}


if __name__ == "__main__":
    main()
