"""Oracles and oracle algorithms (shared by lessons 07-10).

An oracle for f: {0,1}^n -> {0,1} is the reversible gate |x>|y> -> |x>|y XOR f(x)>.
Input qubits are 0..n-1 and the output (ancilla) qubit is n. A function is a truth
table: ``table[x]`` is f(x), with x the integer whose bit k is qubit k. Bit-string
labels follow Qiskit: "101" means qubit 2 = 1, qubit 1 = 0, qubit 0 = 1.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np
from qiskit import QuantumCircuit

Table = tuple[int, ...]


def _check_bits(text: str) -> None:
    if not text or set(text) - {"0", "1"}:
        raise ValueError("expected a non-empty bit string such as '101'.")


def dot(a: int, b: int) -> int:
    """a . b mod 2 (bitwise AND, then parity)."""
    return bin(a & b).count("1") % 2


# ------------------------------------------------------------------ functions

def constant_tables(n: int) -> list[Table]:
    return [(0,) * 2**n, (1,) * 2**n]


def balanced_tables(n: int, *, limit: int | None = None, seed: int = 0) -> list[Table]:
    """Every balanced function (half the inputs give 1), or a seeded sample of `limit`."""
    size = 2**n
    if limit is None:
        return [tuple(1 if x in ones else 0 for x in range(size)) for ones in map(set, combinations(range(size), size // 2))]
    rng = np.random.default_rng([seed, n])
    tables = set()
    while len(tables) < limit:
        tables.add(tuple(int(bit) for bit in rng.permutation([0] * (size // 2) + [1] * (size // 2))))
    return sorted(tables)


def describe(table: Table) -> str:
    """f(x) listed for x = 0, 1, 2, ... e.g. '0110'."""
    return "".join(map(str, table))


# -------------------------------------------------------------------- oracles

def truth_table_oracle(table: Table) -> QuantumCircuit:
    """|x>|y> -> |x>|y XOR f(x)>: one multi-controlled X for every x with f(x) = 1.

    X gates around the control turn "control on bit = 0" into "control on bit = 1".
    """
    n = int(np.log2(len(table)))
    if len(table) != 2**n or set(table) - {0, 1}:
        raise ValueError("table must list 0/1 values for all 2**n inputs.")
    circuit = QuantumCircuit(n + 1, name="oracle")
    for x, value in enumerate(table):
        if not value:
            continue
        zeros = [k for k in range(n) if not (x >> k) & 1]
        if zeros:
            circuit.x(zeros)
        circuit.mcx(list(range(n)), n)
        if zeros:
            circuit.x(zeros)
    return circuit


def bv_table(s: str) -> Table:
    _check_bits(s)
    return tuple(dot(int(s, 2), x) for x in range(2 ** len(s)))


def bv_oracle(s: str) -> QuantumCircuit:
    """f(x) = s . x mod 2: a CNOT from every input qubit whose bit of s is 1 into the output."""
    _check_bits(s)
    n = len(s)
    circuit = QuantumCircuit(n + 1, name="oracle")
    for k in range(n):
        if s[::-1][k] == "1":
            circuit.cx(k, n)
    return circuit


def simon_function(s: str) -> list[int]:
    """f(x) = x if bit j of x is 0, else x XOR s, where j is the lowest set bit of s.

    Then f(x) = f(x XOR s) and no other pair collides: f is 2-to-1 with period s.
    """
    _check_bits(s)
    period = int(s, 2)
    if period == 0:
        raise ValueError("s must be non-zero (Simon's promise: f is 2-to-1).")
    low = (period & -period).bit_length() - 1
    return [x ^ period if (x >> low) & 1 else x for x in range(2 ** len(s))]


def simon_oracle(s: str) -> QuantumCircuit:
    """|x>|y> -> |x>|y XOR f(x)> on n input qubits (0..n-1) and n output qubits (n..2n-1)."""
    simon_function(s)  # validates s
    n = len(s)
    period = int(s, 2)
    low = (period & -period).bit_length() - 1
    circuit = QuantumCircuit(2 * n, name="oracle")
    for k in range(n):
        circuit.cx(k, n + k)  # copy x into the output register
    for k in range(n):
        if (period >> k) & 1:
            circuit.cx(low, n + k)  # XOR s in when bit `low` of x is 1
    return circuit


# ----------------------------------------------------------------- algorithms

def _phase_query(n: int, oracle: QuantumCircuit, *, measure: bool) -> QuantumCircuit:
    """H on the inputs, output qubit in |->, one oracle call, H on the inputs again."""
    circuit = QuantumCircuit(n + 1, n if measure else 0)
    circuit.x(n)
    circuit.h(n)
    circuit.h(range(n))
    circuit.compose(oracle, inplace=True)
    circuit.h(range(n))
    if measure:
        circuit.measure(range(n), range(n))
    return circuit


def deutsch_jozsa_circuit(table: Table, *, measure: bool = False) -> QuantumCircuit:
    return _phase_query(int(np.log2(len(table))), truth_table_oracle(table), measure=measure)


def bernstein_vazirani_circuit(s: str, *, measure: bool = False) -> QuantumCircuit:
    return _phase_query(len(s), bv_oracle(s), measure=measure)


def simon_circuit(s: str, *, measure: bool = True) -> QuantumCircuit:
    """H on the inputs, one oracle call, H on the inputs; only the inputs are measured."""
    n = len(s)
    circuit = QuantumCircuit(2 * n, n if measure else 0)
    circuit.h(range(n))
    circuit.compose(simon_oracle(s), inplace=True)
    circuit.h(range(n))
    if measure:
        circuit.measure(range(n), range(n))
    return circuit


# ------------------------------------------------------------ GF(2) algebra

def _rref(rows: list[int]) -> dict[int, int]:
    """Reduced row echelon form over GF(2) (XOR is addition); rows are bit vectors as ints.

    Returns {pivot bit: row}; every row has a 0 in every other row's pivot bit.
    """
    pivots: dict[int, int] = {}
    for row in rows:
        for bit, pivot_row in pivots.items():
            if (row >> bit) & 1:
                row ^= pivot_row
        if not row:
            continue  # linearly dependent on the rows already kept
        bit = row.bit_length() - 1
        for other in pivots:
            if (pivots[other] >> bit) & 1:
                pivots[other] ^= row
        pivots[bit] = row
    return pivots


def gf2_rank(rows: list[int]) -> int:
    return len(_rref(rows))


def gf2_nullspace(rows: list[int], n: int) -> list[int]:
    """A basis of {s in {0,1}^n : y . s = 0 mod 2 for every row y}, by Gaussian elimination.

    One basis vector per free (non-pivot) bit; polynomial in n, no search over 2**n.
    """
    pivots = _rref(rows)
    basis = []
    for free in (bit for bit in range(n) if bit not in pivots):
        vector = 1 << free
        for bit, row in pivots.items():
            if (row >> free) & 1:
                vector |= 1 << bit
        basis.append(vector)
    return basis
