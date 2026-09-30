"""Lesson 29: quantum randomness, and why a simulator's 'quantum' bits are pseudo-random."""

from __future__ import annotations

import math

import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

from _common import heading
from _qec import run_seed
from _qkd import monobit_test, runs_test, von_neumann

N = 20_000
ALPHA = 0.01  # SP 800-22 convention: a p-value below 0.01 fails the test
BIAS = 0.8


def coin_circuit(p_one: float = 0.5) -> QuantumCircuit:
    """|0>, rotate so that P(1) = p_one (H for 1/2), measure."""
    circuit = QuantumCircuit(1, 1)
    if p_one == 0.5:
        circuit.h(0)
    else:
        circuit.ry(2 * math.asin(math.sqrt(p_one)), 0)
    circuit.measure(0, 0)
    return circuit


def aer_bits(circuit: QuantumCircuit, seed: int, shots: int = N) -> np.ndarray:
    memory = AerSimulator().run(circuit, shots=shots, seed_simulator=seed, memory=True).result().get_memory()
    return np.array([int(bits[-1]) for bits in memory])


def mid_circuit_bits(seed: int, shots: int = 2000) -> np.ndarray:
    """H, measure (mid-circuit), H, measure: the final bit is again a fair coin, but Aer now simulates
    shot by shot, seeding shot i with seed + i."""
    circuit = QuantumCircuit(1, 2)
    circuit.h(0)
    circuit.measure(0, 0)
    circuit.h(0)
    circuit.measure(0, 1)
    memory = AerSimulator().run(circuit, shots=shots, seed_simulator=seed, memory=True).result().get_memory()
    return np.array([int(bits[0]) for bits in memory])


def check(name: str, bits: np.ndarray) -> dict:
    mono, runs = monobit_test(bits), runs_test(bits)
    verdict = "pass" if mono >= ALPHA and runs >= ALPHA else "FAIL"
    print(f"{name:<34}: ones {bits.mean():.4f}   monobit p = {mono:.4f}   runs p = {runs:.4f}   -> {verdict}")
    return {"ones": float(bits.mean()), "monobit": mono, "runs": runs, "pass": verdict == "pass"}


def main() -> dict:
    heading("Step 1: H|0>, then measure: a quantum coin")
    seed = run_seed(1)
    bits = aer_bits(coin_circuit(), seed)
    again = aer_bits(coin_circuit(), seed)
    other = aer_bits(coin_circuit(), run_seed(2))
    neighbour = aer_bits(coin_circuit(), seed + 1)
    print("first 40 bits:", "".join(map(str, bits[:40])))
    print(f"same seed again: identical = {np.array_equal(bits, again)}")
    print(f"another seed: identical = {np.array_equal(bits, other)}, agreement {np.mean(bits == other):.4f} (chance: 0.5)")
    print(f"seed + 1: agreement {np.mean(bits == neighbour):.4f}, shifted by one {np.mean(bits[1:] == neighbour[:-1]):.4f}")
    mid, mid_next = mid_circuit_bits(seed), mid_circuit_bits(seed + 1)
    shifted_mid = float(np.mean(mid[1:] == mid_next[:-1]))
    print(f"with a mid-circuit measurement, seed + 1 is seed shifted by one shot: {shifted_mid:.4f} of bits match")
    print("A simulator's 'quantum' bits come from a seeded pseudo-random generator: same seed, same bits.")

    heading(f"Step 2: statistical tests (NIST SP 800-22 monobit and runs, {N} bits, fail if p < {ALPHA})")
    results = {
        "Aer H|0> bits": check("Aer H|0> bits", bits),
        f"Aer biased coin, P(1) = {BIAS}": check(f"Aer biased coin, P(1) = {BIAS}", aer_bits(coin_circuit(BIAS), run_seed(3))),
        "alternating 0101...": check("alternating 0101...", np.arange(N) % 2),
        "NumPy PCG64 (seed 1)": check("NumPy PCG64 (seed 1)", np.random.default_rng(1).integers(0, 2, N)),
    }
    print("The tests catch bias and too-regular switching. They pass the seeded simulator and NumPy:")
    print("a test can reject bad randomness, but passing it never proves the bits are unpredictable.")

    heading(f"Step 3: a von Neumann extractor on the biased coin (P(1) = {BIAS})")
    biased = aer_bits(coin_circuit(BIAS), run_seed(4), shots=4 * N)
    extracted = von_neumann(biased)
    expected_yield = 2 * BIAS * (1 - BIAS)  # output bits per input pair: P(01) + P(10)
    vn = {"input_ones": float(biased.mean()), "output_ones": float(extracted.mean()), "output_bits": int(len(extracted)),
          "yield_per_pair": len(extracted) / (len(biased) // 2), "expected_yield": expected_yield,
          "tests": check("von Neumann output", extracted)}
    print(f"input: {len(biased)} bits, ones {vn['input_ones']:.4f};  output: {vn['output_bits']} bits, ones {vn['output_ones']:.4f}")
    print(f"yield {vn['yield_per_pair']:.4f} output bits per input pair (expected 2p(1-p) = {expected_yield:.2f})")
    correlated = von_neumann(np.arange(N) % 2)
    print(f"on the correlated 0101... input it outputs {len(correlated)} bits, all equal to {set(correlated.tolist())}: "
          f"it only fixes bias in INDEPENDENT bits")
    return {"identical_same_seed": bool(np.array_equal(bits, again)), "identical_other_seed": bool(np.array_equal(bits, other)),
            "agreement_other_seed": float(np.mean(bits == other)), "agreement_neighbour": float(np.mean(bits == neighbour)),
            "shifted_neighbour": float(np.mean(bits[1:] == neighbour[:-1])), "shifted_mid_circuit": shifted_mid,
            "tests": results, "von_neumann": vn, "correlated_output": sorted(set(correlated.tolist()))}


if __name__ == "__main__":
    main()
