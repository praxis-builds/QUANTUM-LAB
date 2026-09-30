"""BB84 key distribution, key post-processing and randomness checks (shared by lessons 26-29).

Classical choices (Alice's bits and bases, Bob's and Eve's bases, public shuffles) come from a
seeded NumPy generator. Every quantum measurement comes from local Aer. Qubits of the same
"type" (bit, bases, Eve or not) are simulated together as the shots of one run, and every run
gets its own seed from run_seed (CLAUDE.md: never pool runs whose seeds are close).
"""

from __future__ import annotations

import math
from itertools import product

import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, pauli_error

from _qec import run_seed

Z, X = 0, 1  # basis labels: Z = computational {|0>, |1>}, X = Hadamard {|+>, |->}


# ------------------------------------------------------------------ BB84 on Aer

def channel_noise(p: float) -> NoiseModel | None:
    """X, Y, Z each with probability p/2: a qubit is flipped with probability p in EITHER basis
    (X and Y flip Z-basis states; Z and Y flip X-basis states). A pure X channel would flip only
    Z-basis states, giving an error rate of p/2 instead."""
    if p == 0:
        return None
    if not 0 < p <= 2 / 3:
        raise ValueError("p must be in (0, 2/3].")
    model = NoiseModel()
    model.add_all_qubit_quantum_error(pauli_error([("X", p / 2), ("Y", p / 2), ("Z", p / 2), ("I", 1 - 1.5 * p)]), ["id"])
    return model


def qubit_circuit(bit: int, alice_basis: int, bob_basis: int, eve_basis: int | None) -> QuantumCircuit:
    """One photon: Alice prepares, (Eve measures in her basis and resends what she saw), the channel
    acts (id gate), Bob measures. Classical bit 0 = Bob's result, bit 1 = Eve's result."""
    circuit = QuantumCircuit(1, 2)
    if bit:
        circuit.x(0)
    if alice_basis == X:
        circuit.h(0)
    if eve_basis is not None:
        # Measuring in Eve's basis leaves the photon in the state she saw: measure and resend in one.
        if eve_basis == X:
            circuit.h(0)
        circuit.measure(0, 1)
        if eve_basis == X:
            circuit.h(0)
    circuit.id(0)
    if bob_basis == X:
        circuit.h(0)
    circuit.measure(0, 0)
    return circuit


def bb84_round(n: int, rng: np.random.Generator, *, base_run: int, noise_p: float = 0.0, eve_fraction: float = 0.0) -> dict:
    """Send n qubits. Returns Alice's bits/bases, Bob's bases/results, and Eve's choices/results."""
    alice_bits = rng.integers(0, 2, n)
    alice_bases = rng.integers(0, 2, n)
    bob_bases = rng.integers(0, 2, n)
    intercepted = rng.random(n) < eve_fraction
    eve_bases = rng.integers(0, 2, n)
    bob_bits = np.zeros(n, dtype=int)
    eve_bits = np.full(n, -1)
    simulator = AerSimulator(method="stabilizer", noise_model=channel_noise(noise_p))
    for k, (bit, ab, bb, eve, eb) in enumerate(product((0, 1), (Z, X), (Z, X), (False, True), (Z, X))):
        if not eve and eb == X:
            continue  # without Eve her basis does not matter
        mask = (alice_bits == bit) & (alice_bases == ab) & (bob_bases == bb) & (intercepted == eve)
        if eve:
            mask &= eve_bases == eb
        index = np.flatnonzero(mask)
        if index.size == 0:
            continue
        circuit = qubit_circuit(bit, ab, bb, eb if eve else None)
        memory = simulator.run(circuit, shots=int(index.size), seed_simulator=run_seed(base_run + k), memory=True).result().get_memory()
        bob_bits[index] = [int(bits[-1]) for bits in memory]
        if eve:
            eve_bits[index] = [int(bits[-2]) for bits in memory]
    return {"alice_bits": alice_bits, "alice_bases": alice_bases, "bob_bases": bob_bases, "bob_bits": bob_bits,
            "intercepted": intercepted, "eve_bases": eve_bases, "eve_bits": eve_bits}


def sift(round_: dict) -> np.ndarray:
    """Alice and Bob announce their bases (not their bits) and keep the positions where they match."""
    return round_["alice_bases"] == round_["bob_bases"]


def qber(round_: dict, mask: np.ndarray | None = None) -> float:
    """Quantum bit error rate on the kept positions."""
    keep = sift(round_) if mask is None else mask
    return float(np.mean(round_["alice_bits"][keep] != round_["bob_bits"][keep]))


# ------------------------------------------------------------ key post-processing

def binary_entropy(q: float) -> float:
    if q <= 0 or q >= 1:
        return 0.0
    return -q * math.log2(q) - (1 - q) * math.log2(1 - q)


def toeplitz_matrix(n: int, m: int, seed_bits: np.ndarray) -> np.ndarray:
    """m x n Toeplitz matrix over GF(2): entry (i, j) = seed_bits[i - j + n - 1]. It is fixed by
    n + m - 1 public random bits, and constant along every diagonal."""
    if len(seed_bits) != n + m - 1:
        raise ValueError("a Toeplitz matrix needs n + m - 1 seed bits.")
    i, j = np.meshgrid(np.arange(m), np.arange(n), indexing="ij")
    return np.asarray(seed_bits)[i - j + n - 1]


def toeplitz_hash(bits: np.ndarray, m: int, seed_bits: np.ndarray) -> np.ndarray:
    """Hash n bits to m bits: T x mod 2. Linear, and a universal hash family over random seeds.

    Computed as a correlation (y_i = sum_k seed[i + k] * x[n - 1 - k]) instead of building the
    m x n matrix, which for a 9,000-bit key would take hundreds of megabytes. Same result as
    toeplitz_matrix(n, m, seed_bits) @ bits % 2 (checked in the tests)."""
    bits = np.asarray(bits, dtype=np.int64)
    seed_bits = np.asarray(seed_bits, dtype=np.int64)
    if len(seed_bits) != len(bits) + m - 1:
        raise ValueError("a Toeplitz matrix needs n + m - 1 seed bits.")
    return np.correlate(seed_bits, bits[::-1], mode="valid") % 2


def _parity(bits: np.ndarray) -> int:
    return int(bits.sum() % 2)


def parity_error_correction(alice: np.ndarray, bob: np.ndarray, rng: np.random.Generator, *, estimated_q: float,
                            clean_passes: int = 3, max_passes: int = 60) -> tuple[np.ndarray, int]:
    """Toy error correction in the style of the BBBSS/Cascade family (much simplified).

    Each pass: publicly shuffle positions, cut into blocks, compare block parities (1 public bit
    each); for a mismatched block, halve it repeatedly comparing parities (1 public bit per step)
    to find one error, and Bob flips it. A block with an even number of errors looks clean, so
    passes repeat with new shuffles (blocks growing, capped at a quarter of the key) until
    `clean_passes` passes in a row find nothing. There is no Cascade-style backtracking, so it
    reveals more than the minimum. Returns Bob's corrected bits and the number of public bits.
    """
    bob = bob.copy()
    leaked, clean = 0, 0
    block = max(4, int(0.73 / max(estimated_q, 1e-3)))
    for _ in range(max_passes):
        order = rng.permutation(len(alice))
        fixed = 0
        for start in range(0, len(order), block):
            positions = order[start:start + block]
            leaked += 1
            if _parity(alice[positions]) == _parity(bob[positions]):
                continue
            while len(positions) > 1:
                half = positions[: len(positions) // 2]
                leaked += 1
                positions = half if _parity(alice[half]) != _parity(bob[half]) else positions[len(positions) // 2:]
            bob[positions[0]] ^= 1
            fixed += 1
        clean = clean + 1 if fixed == 0 else 0
        if clean >= clean_passes:
            break
        block = min(block * 2, max(4, len(alice) // 4))
    return bob, leaked


# --------------------------------------------------------------- randomness checks

def monobit_test(bits: np.ndarray) -> float:
    """NIST SP 800-22 frequency (monobit) test: p-value for 'as many ones as zeros'."""
    bits = np.asarray(bits, dtype=int)
    s_obs = abs(int(np.sum(2 * bits - 1))) / math.sqrt(len(bits))
    return math.erfc(s_obs / math.sqrt(2))


def runs_test(bits: np.ndarray) -> float:
    """NIST SP 800-22 runs test: p-value for 'switches between 0 and 1 as often as chance'.
    Its prerequisite is a passed frequency check; if that fails, the p-value is 0."""
    bits = np.asarray(bits, dtype=int)
    n = len(bits)
    pi = bits.mean()
    if abs(pi - 0.5) >= 2 / math.sqrt(n):
        return 0.0
    runs = 1 + int(np.sum(bits[1:] != bits[:-1]))
    return math.erfc(abs(runs - 2 * n * pi * (1 - pi)) / (2 * math.sqrt(2 * n) * pi * (1 - pi)))


def von_neumann(bits: np.ndarray) -> np.ndarray:
    """Read bits in pairs: 01 -> 0, 10 -> 1, 00 and 11 -> nothing. Removes the bias of independent,
    identically biased bits (P(01) = P(10) = p(1-p)); it cannot fix correlated bits."""
    bits = np.asarray(bits, dtype=int)
    pairs = bits[: len(bits) // 2 * 2].reshape(-1, 2)
    keep = pairs[:, 0] != pairs[:, 1]
    return pairs[keep, 1]
