"""Oracle correctness for every function used in lessons 07-10, plus the GF(2) solver."""

from __future__ import annotations

import sys
from itertools import product

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from _lessons import LESSONS

if str(LESSONS) not in sys.path:
    sys.path.insert(0, str(LESSONS))

import _oracles as oracles  # noqa: E402

SEED = 20260928


def assert_bit_flip_oracle(oracle: QuantumCircuit, f, n: int, output_bits: int) -> None:
    """The oracle's unitary is exactly the permutation |x>|y> -> |x>|y XOR f(x)>, for every x and y
    (y occupies the qubits above n). Checks every column at once, including phases."""
    size = 2 ** (n + output_bits)
    expected = np.zeros((size, size))
    for x, y in product(range(2**n), range(2**output_bits)):
        expected[x | ((y ^ f(x)) << n), x | (y << n)] = 1.0
    np.testing.assert_allclose(Operator(oracle).data, expected, atol=1e-10)


TABLES = (
    [table for n in (1, 2, 3) for table in oracles.constant_tables(n) + oracles.balanced_tables(n)]
    + oracles.constant_tables(4) + oracles.balanced_tables(4, limit=50, seed=SEED)
)


@pytest.mark.parametrize("table", TABLES, ids=oracles.describe)
def test_truth_table_oracle_is_correct_for_every_function_used(table):
    n = int(np.log2(len(table)))
    assert_bit_flip_oracle(oracles.truth_table_oracle(table), lambda x: table[x], n, 1)


def test_function_families_are_what_they_claim():
    for n in (1, 2, 3):
        balanced = oracles.balanced_tables(n)
        assert len(balanced) == len(set(balanced)) == {1: 2, 2: 6, 3: 70}[n]
        assert all(sum(t) == 2 ** (n - 1) for t in balanced)
        assert oracles.constant_tables(n) == [(0,) * 2**n, (1,) * 2**n]
    sample = oracles.balanced_tables(4, limit=50, seed=SEED)
    assert sample == oracles.balanced_tables(4, limit=50, seed=SEED)  # seeded, reproducible
    assert len(set(sample)) == 50 and all(sum(t) == 8 for t in sample)


@pytest.mark.parametrize("s", ["1", "101", "011", "0110", "1111", "1001"])
def test_bernstein_vazirani_oracle_computes_s_dot_x(s):
    n = len(s)
    table = oracles.bv_table(s)
    assert all(table[x] == bin(int(s, 2) & x).count("1") % 2 for x in range(2**n))
    assert_bit_flip_oracle(oracles.bv_oracle(s), lambda x: table[x], n, 1)


@pytest.mark.parametrize("s", ["1", "11", "01", "10", "110", "101", "1010", "1111"])
def test_simon_function_is_two_to_one_with_period_s(s):
    n, period = len(s), int(s, 2)
    f = oracles.simon_function(s)
    for x in range(2**n):
        assert f[x] == f[x ^ period]
        for other in range(2**n):
            if f[other] == f[x]:
                assert other in (x, x ^ period)
    assert len(set(f)) == 2 ** (n - 1)
    assert_bit_flip_oracle(oracles.simon_oracle(s), lambda x: f[x], n, n)


@pytest.mark.parametrize("bad", ["", "12", "0", "000"])
def test_simon_rejects_zero_or_malformed_period(bad):
    with pytest.raises(ValueError):
        oracles.simon_function(bad)


def test_gf2_nullspace_and_rank():
    assert oracles.gf2_nullspace([0b11], 2) == [0b11]
    assert oracles.gf2_nullspace([0b001, 0b111], 3) == [0b110]
    assert oracles.gf2_rank([0b11, 0b11, 0]) == 1
    assert sorted(oracles.gf2_nullspace([], 2)) == [0b01, 0b10]
    rng = np.random.default_rng(SEED)
    for _ in range(200):
        n = int(rng.integers(2, 8))
        rows = [int(r) for r in rng.integers(0, 2**n, size=int(rng.integers(0, n + 2)))]
        basis = oracles.gf2_nullspace(rows, n)
        assert len(basis) == n - oracles.gf2_rank(rows)
        assert oracles.gf2_rank(basis) == len(basis)  # independent
        assert all(oracles.dot(y, v) == 0 for y in rows for v in basis)
