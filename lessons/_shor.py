"""Shor's algorithm on toy numbers (shared by lessons 13-16).

The quantum part of Shor only finds the period (order) r of f(x) = a^x mod N.
Everything else here is ordinary classical number theory.
"""

from __future__ import annotations

import math
from fractions import Fraction

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import UnitaryGate
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

from _qft import qft_circuit


def order(a: int, N: int) -> int:
    """Smallest r >= 1 with a^r = 1 (mod N), by brute force: up to about N steps.

    This loop is the part a quantum computer replaces; it is exponential in the number of bits of N.
    """
    if math.gcd(a, N) != 1:
        raise ValueError(f"a = {a} shares a factor with N = {N}; there is no period.")
    r, value = 1, a % N
    while value != 1:
        value = value * a % N
        r += 1
    return r


def factors_from_order(a: int, N: int, r: int) -> tuple[tuple[int, int] | None, str]:
    """a^r - 1 = (a^(r/2) - 1)(a^(r/2) + 1) is a multiple of N. If neither bracket is itself a
    multiple of N, each shares a proper factor with N. Returns ((p, q), "ok") or (None, reason)."""
    if r % 2:
        return None, "r is odd"
    half = pow(a, r // 2, N)
    if half == N - 1:
        return None, "a^(r/2) = -1 (mod N)"
    if half == 1:
        return None, "a^(r/2) = 1 (mod N): r is a multiple of the period, not the period"
    p, q = math.gcd(half - 1, N), math.gcd(half + 1, N)
    return (min(p, q), max(p, q)), "ok"


def trial_division(N: int) -> tuple[int, int, int]:
    """Classical baseline: try divisors 2, 3, ... Returns (p, N // p, divisions tried)."""
    for tried, candidate in enumerate(range(2, math.isqrt(N) + 1), start=1):
        if N % candidate == 0:
            return candidate, N // candidate, tried
    raise ValueError(f"{N} is prime.")


# ------------------------------------------------------------------ quantum part
#
# Register layout (Qiskit order): counting qubits 0..t-1, then the n-qubit work register
# t..t+n-1, which starts in |1>. Counting qubit k controls "multiply by a^(2^k) mod N".
# The powers a^(2^k) mod N are computed classically beforehand (repeated squaring), and each
# multiplier is built from its known permutation: the "compiled Shor" shortcut.

def work_qubits(N: int) -> int:
    return N.bit_length()


def modmul_permutation(m: int, N: int, n: int) -> list[int]:
    """y -> m*y mod N for y < N, and y -> y for N <= y < 2^n. A permutation when gcd(m, N) = 1."""
    if math.gcd(m, N) != 1:
        raise ValueError("m must be a unit mod N to be reversible.")
    return [(m * y) % N if y < N else y for y in range(2**n)]


def controlled_permutation_gate(m: int, N: int, n: int | None = None) -> UnitaryGate:
    """Generic construction: the full 2^(n+1) x 2^(n+1) permutation matrix of controlled
    "multiply by m mod N". Gate qubit 0 is the control, qubits 1..n the work register."""
    n = n or work_qubits(N)
    permutation = modmul_permutation(m, N, n)
    size = 2 ** (n + 1)
    matrix = np.zeros((size, size))
    for index in range(size):
        control, y = index & 1, index >> 1
        matrix[((permutation[y] if control else y) << 1) | control, index] = 1.0
    return UnitaryGate(matrix, label=f"x{m} mod {N}")


def _mod15_shape(m: int) -> tuple[int, bool]:
    """Every unit mod 15 is +-2^j: returns (j, negative)."""
    for j in range(4):
        if pow(2, j, 15) == m % 15:
            return j, False
        if (15 - pow(2, j, 15)) == m % 15:
            return j, True
    raise ValueError(f"{m} is not a unit mod 15.")


def controlled_mod15_multiplier(m: int) -> QuantumCircuit:
    """Gate-level controlled "multiply by m mod 15" on 5 qubits (qubit 0 = control, 1..4 = y).

    Multiplying by 2 mod 15 rotates the 4 bits of y left (for 1 <= y <= 14); by 2^j, j times.
    Multiplying by -2^j is that rotation followed by NOT on every bit (15 - y). Correct on
    y = 1..14, every state Shor reaches from |1>. States 0 and 15 are not needed: the rotations
    fix them, and the NOT variants swap them.
    """
    j, negative = _mod15_shape(m)
    circuit = QuantumCircuit(5, name=f"c-x{m} mod 15")
    for _ in range(j):
        circuit.cswap(0, 3, 4)
        circuit.cswap(0, 2, 3)
        circuit.cswap(0, 1, 2)
    if negative:
        for qubit in range(1, 5):
            circuit.cx(0, qubit)
    return circuit


def shor_circuit(a: int, N: int, *, gate_level: bool = False, counting: int | None = None,
                 measure: bool = False) -> QuantumCircuit:
    """Phase estimation of "multiply by a mod N" (Lesson 12) with t = 2n counting qubits by default."""
    n = work_qubits(N)
    t = counting or 2 * n
    circuit = QuantumCircuit(t + n, t if measure else 0)
    circuit.h(range(t))
    circuit.x(t)  # work register = |1>
    for k in range(t):
        multiplier = pow(a, 2**k, N)  # precomputed classically by repeated squaring
        if multiplier == 1:
            continue  # multiplying by 1 is the identity
        gate = controlled_mod15_multiplier(multiplier) if gate_level else controlled_permutation_gate(multiplier, N, n)
        circuit.append(gate.to_gate() if gate_level else gate, [k, *range(t, t + n)])
    circuit.compose(qft_circuit(t).inverse(), qubits=range(t), inplace=True)
    if measure:
        circuit.measure(range(t), range(t))
    return circuit


def readout_distribution(a: int, N: int, *, gate_level: bool = False) -> np.ndarray:
    """Exact probability of each counting-register outcome m."""
    t = 2 * work_qubits(N)
    return Statevector(shor_circuit(a, N, gate_level=gate_level)).probabilities(list(range(t)))


def sample_runs(a: int, N: int, shots: int, seed: int, *, gate_level: bool = False) -> list[int]:
    """One Aer shot = one run of Shor's circuit. Returns each run's measured m, in order."""
    simulator = AerSimulator(method="statevector")
    compiled = transpile(shor_circuit(a, N, gate_level=gate_level, measure=True), simulator, seed_transpiler=seed)
    memory = simulator.run(compiled, shots=shots, seed_simulator=seed, memory=True).result().get_memory()
    return [int(bits, 2) for bits in memory]


def period_from_measurement(m: int, t: int, N: int) -> int:
    """m / 2^t is close to s/r. The continued-fraction expansion finds the nearest fraction with a
    denominator of at most N. Its denominator is r when gcd(s, r) = 1 and m is a good estimate;
    otherwise a divisor of r, or (for a poor m) an unrelated number."""
    return Fraction(m, 2**t).limit_denominator(N).denominator


def run_gives_order(a: int, N: int, m: int, t: int) -> bool:
    """Reporting metric: did this run's continued fraction return exactly r? (Uses the true r,
    which the algorithm itself never needs; see factor_with_shor.)"""
    return period_from_measurement(m, t, N) == order(a, N)


def factor_with_shor(N: int, rng: np.random.Generator, runs_for: dict[int, list[int]]) -> dict:
    """The full algorithm: random a; gcd shortcut; else one quantum run per attempt (taken in order
    from runs_for[a]); classical checks only (a^c = 1 mod N, then the gcds); retry with a new a
    on any failure. It never uses the true period."""
    t = 2 * work_qubits(N)
    cursor = {a: 0 for a in runs_for}
    picks = quantum_runs = 0
    while True:
        picks += 1
        a = int(rng.integers(2, N))
        shared = math.gcd(a, N)
        if shared > 1:
            return {"factors": (min(shared, N // shared), max(shared, N // shared)), "picks": picks,
                    "quantum_runs": quantum_runs, "a": a}
        m = runs_for[a][cursor[a]]
        cursor[a] += 1
        quantum_runs += 1
        candidate = period_from_measurement(m, t, N)
        if pow(a, candidate, N) == 1:
            factors, _ = factors_from_order(a, N, candidate)
            if factors:
                return {"factors": factors, "picks": picks, "quantum_runs": quantum_runs, "a": a}
