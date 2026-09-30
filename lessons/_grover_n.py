"""Grover search on n qubits (shared by lessons 17-19).

Search space N = 2**n, M marked items. With sin(theta) = sqrt(M/N), after k Grover
iterations the probability of measuring a marked item is sin^2((2k + 1) theta):
each iteration rotates the state by 2 theta toward the marked items.
"""

from __future__ import annotations

import math

import numpy as np
from qiskit import QuantumCircuit


def angle(N: int, M: int) -> float:
    if not 0 < M <= N:
        raise ValueError("need 0 < M <= N.")
    return math.asin(math.sqrt(M / N))


def optimal_iterations(N: int, M: int = 1) -> int:
    """floor(pi / (4 theta)): the last k before the rotation passes the marked direction.
    For M << N this is about (pi/4) sqrt(N/M)."""
    return math.floor(math.pi / (4 * angle(N, M)))


def success_probability(k: int, N: int, M: int = 1) -> float:
    return math.sin((2 * k + 1) * angle(N, M)) ** 2


def mcz(circuit: QuantumCircuit, qubits: list[int]) -> None:
    """Flip the sign of the state where every listed qubit is 1 (H, multi-controlled X, H)."""
    if len(qubits) == 1:
        circuit.z(qubits[0])
        return
    circuit.h(qubits[-1])
    circuit.mcx(qubits[:-1], qubits[-1])
    circuit.h(qubits[-1])


def flip_if_equal(circuit: QuantumCircuit, qubits: list[int], value: int) -> None:
    """Phase-flip the basis state where the register `qubits` (lowest bit first) holds `value`."""
    zeros = [q for bit, q in enumerate(qubits) if not (value >> bit) & 1]
    if zeros:
        circuit.x(zeros)
    mcz(circuit, qubits)
    if zeros:
        circuit.x(zeros)


def diffusion(circuit: QuantumCircuit, qubits: list[int]) -> None:
    """Reflect about the uniform superposition: H, flip |0...0>, H (up to a global sign)."""
    circuit.h(qubits)
    flip_if_equal(circuit, qubits, 0)
    circuit.h(qubits)


def grover_circuit(n: int, oracle, iterations: int, *, extra_qubits: int = 0, measure: bool = False) -> QuantumCircuit:
    """H on the n search qubits, then `iterations` rounds of oracle + diffusion.

    `oracle(circuit)` must phase-flip the marked states; it may use `extra_qubits` work qubits
    (numbered n, n+1, ...) and must return them to |0>.
    """
    circuit = QuantumCircuit(n + extra_qubits, n if measure else 0)
    search = list(range(n))
    circuit.h(search)
    for _ in range(iterations):
        oracle(circuit)
        diffusion(circuit, search)
    if measure:
        circuit.measure(search, search)
    return circuit


def marked_item_oracle(n: int, marked: int):
    """The abstract oracle of Lesson 17: flip the sign of one basis state, given for free."""
    return lambda circuit: flip_if_equal(circuit, list(range(n)), marked)


def bbht_calls(N: int, M: int, rng: np.random.Generator) -> int:
    """Boyer, Brassard, Hoyer, Tapp (1998) for unknown M: pick k at random below a bound m,
    run k iterations, measure, check the answer (1 more call); on failure grow m by 6/5
    (capped at sqrt(N)). Returns the total oracle calls, checks included. Measurement outcomes
    are drawn from the exact success probability."""
    bound, calls = 1.0, 0
    while True:
        k = int(rng.integers(0, max(1, math.ceil(bound))))
        calls += k + 1
        if rng.random() < success_probability(k, N, M):
            return calls
        bound = min(6 / 5 * bound, math.sqrt(N))
