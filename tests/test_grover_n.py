"""n-qubit Grover helpers (lessons/_grover_n.py)."""

from __future__ import annotations

import math
import sys

import numpy as np
import pytest
from qiskit.quantum_info import Statevector

from _lessons import LESSONS

if str(LESSONS) not in sys.path:
    sys.path.insert(0, str(LESSONS))

import _grover_n as grover  # noqa: E402


@pytest.mark.parametrize("N,M,k", [(4, 1, 1), (8, 1, 2), (16, 1, 3), (64, 1, 6), (256, 1, 12), (64, 4, 3), (512, 2, 12), (1024, 2, 17)])
def test_optimal_iteration_count(N, M, k):
    assert grover.optimal_iterations(N, M) == k
    assert abs(k - math.pi / 4 * math.sqrt(N / M)) < 1.0  # ~ (pi/4) sqrt(N/M)


@pytest.mark.parametrize("n", range(2, 9))
def test_success_above_0_9_at_the_optimum_and_statevector_matches_formula(n):
    N = 2**n
    k = grover.optimal_iterations(N)
    for marked in (0, N - 1, 5 % N):
        state = Statevector(grover.grover_circuit(n, grover.marked_item_oracle(n, marked), k))
        p = state.probabilities()[marked]
        assert p == pytest.approx(grover.success_probability(k, N), abs=1e-9)
        assert p > 0.9


@pytest.mark.parametrize("n", range(2, 9))
def test_over_rotation_lowers_success(n):
    N = 2**n
    k = grover.optimal_iterations(N)
    assert grover.success_probability(2 * k, N) < grover.success_probability(k, N) - 0.5
    assert grover.success_probability(k + 1, N) < grover.success_probability(k, N) or n == 2


def test_bbht_mean_cost_scales_like_sqrt_n_over_m():
    rng = np.random.default_rng(1)
    means = {M: np.mean([grover.bbht_calls(256, M, rng) for _ in range(3000)]) for M in (1, 4, 16)}
    assert means[1] > means[4] > means[16]
    for M, mean in means.items():
        assert mean < 4 * math.sqrt(256 / M)  # O(sqrt(N/M)) with a modest constant


def test_angle_rejects_bad_counts():
    with pytest.raises(ValueError):
        grover.angle(8, 0)
