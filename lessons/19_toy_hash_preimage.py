"""Lesson 19: toy hash preimages. Measure how Grover's cost grows compared with classical search."""

from __future__ import annotations

from collections import Counter

import matplotlib.pyplot as plt
import numpy as np
from qiskit import QuantumCircuit

from _common import SEED, heading, out_dir
from _grover_n import flip_if_equal, grover_circuit, optimal_iterations, success_probability
from praxis_quantum_lab.qiskit_experiments import ideal_counts

SIZES = range(4, 11)  # input bits n; the hash outputs n - 1 bits
PREIMAGES = 2  # every target is chosen with exactly this many preimages, so only N changes
SHOTS = 1000
CLASSICAL_TRIALS = 2000


def toy_hash(x: int, n: int) -> int:
    """n bits -> n-1 bits: out_i = x_i XOR (x_{i+1} AND x_{i+2}) XOR x_{i+3}, indices mod n.
    Nonlinear (the AND), many-to-one (it compresses), in the spirit of Keccak's chi step."""
    bit = lambda i: (x >> (i % n)) & 1  # noqa: E731
    return sum((bit(i) ^ (bit(i + 1) & bit(i + 2)) ^ bit(i + 3)) << i for i in range(n - 1))


def compute_hash(circuit: QuantumCircuit, n: int) -> None:
    """out XOR= hash(x): x on qubits 0..n-1, out on n..2n-2. Two CNOTs and one Toffoli per output
    bit; every gate XORs into the output, so the same gates also uncompute it."""
    for i in range(n - 1):
        out = n + i
        circuit.cx(i % n, out)
        circuit.cx((i + 3) % n, out)
        circuit.ccx((i + 1) % n, (i + 2) % n, out)


def hash_oracle(n: int, target: int):
    outputs = list(range(n, 2 * n - 1))

    def oracle(circuit: QuantumCircuit) -> None:
        compute_hash(circuit, n)
        flip_if_equal(circuit, outputs, target)
        compute_hash(circuit, n)
    return oracle


def choose_target(n: int) -> int:
    """Experiment design (done classically, stated openly): the smallest output with exactly
    PREIMAGES preimages, so that M is the same at every size."""
    counts = Counter(toy_hash(x, n) for x in range(2**n))
    return min(t for t, c in counts.items() if c == PREIMAGES)


def classical_mean(n: int, target: int, rng: np.random.Generator) -> float:
    """Hash random unseen inputs until one hits the target (the hash table below is only a speed-up
    for the simulation: each trial still counts one evaluation per input tried)."""
    hits = np.array([toy_hash(x, n) == target for x in range(2**n)])
    tries = [int(np.argmax(hits[rng.permutation(2**n)])) + 1 for _ in range(CLASSICAL_TRIALS)]
    return float(np.mean(tries))


def slope(sizes: list[int], values: list[float]) -> float:
    """Least-squares slope of log2(value) against n: 1 means doubling per bit, 0.5 means x sqrt(2)."""
    return float(np.polyfit(sizes, np.log2(values), 1)[0])


def plot(rows: dict, fits: dict):
    sizes = list(rows)
    figure, axis = plt.subplots(figsize=(7, 4.5))
    axis.semilogy(sizes, [rows[n]["quantum_calls"] for n in sizes], "o-", base=2,
                  label=f"Grover oracle calls (slope {fits['quantum']:.2f})")
    axis.semilogy(sizes, [rows[n]["quantum_calls_checked"] for n in sizes], "s--", base=2,
                  label=f"Grover + 1 check per attempt (slope {fits['quantum_checked']:.2f})")
    axis.semilogy(sizes, [rows[n]["classical_measured"] for n in sizes], "^-", base=2,
                  label=f"classical random search (slope {fits['classical']:.2f})")
    axis.set_xlabel("input bits n (search space 2^n, 2 preimages)")
    axis.set_ylabel("expected oracle calls (log2 scale)")
    axis.set_title("Toy hash preimage search: measured cost")
    axis.legend(fontsize=8)
    figure.tight_layout()
    path = out_dir() / "19_hash_scaling.png"
    figure.savefig(path, dpi=130)
    plt.close(figure)
    return path


def main() -> dict:
    heading("Step 1: the toy hash has several preimages per output")
    for n in (4, 6):
        counts = Counter(toy_hash(x, n) for x in range(2**n))
        print(f"n = {n}: {2 ** n} inputs -> {len(counts)} of {2 ** (n - 1)} outputs used; "
              f"preimages per output: {dict(sorted(Counter(counts.values()).items()))}")

    heading(f"Step 2: Grover for a preimage, n = {SIZES.start}..{SIZES.stop - 1} ({SHOTS} seeded Aer shots each)")
    rng = np.random.default_rng(SEED)
    rows = {}
    for n in SIZES:
        target = choose_target(n)
        k = optimal_iterations(2**n, PREIMAGES)
        circuit = grover_circuit(n, hash_oracle(n, target), k, extra_qubits=n - 1, measure=True)
        counts = ideal_counts(circuit, shots=SHOTS, seed=SEED + n)
        hits = sum(v for key, v in counts.items() if toy_hash(int(key, 2), n) == target)
        p = hits / SHOTS
        rows[n] = {"target": target, "iterations": k, "qubits": circuit.num_qubits, "p": p,
                   "theory": success_probability(k, 2**n, PREIMAGES),
                   "quantum_calls": k / p, "quantum_calls_checked": (k + 1) / p,
                   "classical_theory": (2**n + 1) / (PREIMAGES + 1), "classical_measured": classical_mean(n, target, rng)}
        row = rows[n]
        print(f"n = {n:>2}: {row['qubits']:>2} qubits, k = {k:>2}, P(preimage) = {p:.3f} (theory {row['theory']:.3f});  "
              f"expected calls: Grover {row['quantum_calls']:6.2f} (+check {row['quantum_calls_checked']:6.2f}), "
              f"classical {row['classical_measured']:7.2f} (theory {row['classical_theory']:7.2f})")

    heading("Step 3: the measured scaling (least-squares slope of log2(calls) against n)")
    sizes = list(rows)
    fits = {
        "quantum": slope(sizes, [rows[n]["quantum_calls"] for n in sizes]),
        "quantum_checked": slope(sizes, [rows[n]["quantum_calls_checked"] for n in sizes]),
        "classical": slope(sizes, [rows[n]["classical_measured"] for n in sizes]),
    }
    print(f"Grover: slope {fits['quantum']:.3f}  (with the +1 check: {fits['quantum_checked']:.3f})")
    print(f"classical: slope {fits['classical']:.3f}")
    print("Slope 1 = the cost doubles with each extra bit; slope 0.5 = it grows by sqrt(2) per bit.")
    print("That is the square-root speed-up, measured in oracle calls on toy sizes.")
    path = plot(rows, fits)
    print(f"\nSaved {path}")
    return {"rows": rows, "fits": fits}


if __name__ == "__main__":
    main()
