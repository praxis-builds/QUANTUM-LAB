"""Shor helpers (lessons/_shor.py): orders, factor recovery, and (below) the quantum pieces."""

from __future__ import annotations

import math
import sys

import pytest

from _lessons import LESSONS

if str(LESSONS) not in sys.path:
    sys.path.insert(0, str(LESSONS))

import _shor as shor  # noqa: E402

UNITS = {N: [a for a in range(2, N) if math.gcd(a, N) == 1] for N in (15, 21)}
EXPECTED_ORDERS = {
    15: {2: 4, 4: 2, 7: 4, 8: 4, 11: 2, 13: 4, 14: 2},
    21: {2: 6, 4: 3, 5: 6, 8: 2, 10: 6, 11: 6, 13: 2, 16: 3, 17: 6, 19: 6, 20: 2},
}


@pytest.mark.parametrize("N", [15, 21])
def test_order_is_the_smallest_period_for_every_a_used(N):
    for a in UNITS[N]:
        r = shor.order(a, N)
        assert r == EXPECTED_ORDERS[N][a]
        assert pow(a, r, N) == 1
        assert all(pow(a, d, N) != 1 for d in range(1, r))
        assert all(pow(a, x + r, N) == pow(a, x, N) for x in range(3 * r))  # a genuine period of a^x mod N


def test_order_rejects_a_sharing_a_factor():
    with pytest.raises(ValueError):
        shor.order(6, 15)


@pytest.mark.parametrize("N,working,failing", [
    (15, {2, 4, 7, 8, 11, 13}, {14: "a^(r/2) = -1 (mod N)"}),
    (21, {2, 8, 10, 11, 13, 19}, {4: "r is odd", 16: "r is odd", 5: "a^(r/2) = -1 (mod N)",
                                  17: "a^(r/2) = -1 (mod N)", 20: "a^(r/2) = -1 (mod N)"}),
])
def test_factor_recovery_and_failure_reasons(N, working, failing):
    for a in UNITS[N]:
        factors, reason = shor.factors_from_order(a, N, shor.order(a, N))
        if a in working:
            assert reason == "ok" and factors[0] * factors[1] == N and 1 < factors[0] < N
        else:
            assert factors is None and reason == failing[a]
    assert set(UNITS[N]) == working | set(failing)


def test_trial_division_baseline():
    assert shor.trial_division(15) == (3, 5, 2)
    assert shor.trial_division(21) == (3, 7, 2)
    with pytest.raises(ValueError):
        shor.trial_division(13)


# ---------------------------------------------------------------- quantum pieces

import numpy as np  # noqa: E402
from qiskit.quantum_info import Operator  # noqa: E402

MULTIPLIERS = {N: sorted({pow(a, 2**k, N) for a in UNITS[N] for k in range(2 * N.bit_length())}) for N in (15, 21)}


@pytest.mark.parametrize("N", [15, 21])
def test_modmul_permutations_are_permutations_and_multiply_correctly(N):
    n = N.bit_length()
    for m in MULTIPLIERS[N]:
        permutation = shor.modmul_permutation(m, N, n)
        assert sorted(permutation) == list(range(2**n))
        assert all(permutation[y] == m * y % N for y in range(N))
        assert all(permutation[y] == y for y in range(N, 2**n))
    with pytest.raises(ValueError):
        shor.modmul_permutation(3, 15, 4)


@pytest.mark.parametrize("N", [15, 21])
def test_controlled_permutation_gates_are_permutation_matrices_acting_correctly(N):
    n = N.bit_length()
    for m in MULTIPLIERS[N]:
        matrix = shor.controlled_permutation_gate(m, N, n).to_matrix()
        assert np.allclose(np.abs(matrix).sum(axis=0), 1) and np.allclose(np.abs(matrix).sum(axis=1), 1)
        assert set(np.round(matrix.real, 12).ravel()) <= {0.0, 1.0}
        np.testing.assert_allclose(matrix @ matrix.conj().T, np.eye(2 ** (n + 1)), atol=1e-12)
        for y in range(2**n):
            for control in (0, 1):
                expected = (m * y % N if (control and y < N) else y) << 1 | control
                assert matrix[expected, (y << 1) | control] == 1.0, (m, y, control)


def test_gate_level_mod15_multipliers_match_on_every_reachable_input():
    for m in MULTIPLIERS[15]:
        unitary = Operator(shor.controlled_mod15_multiplier(m)).data
        assert np.allclose(np.abs(unitary) @ np.ones(32), 1)  # a permutation
        for y in range(16):
            for control in (0, 1):
                column = unitary[:, (y << 1) | control]
                out = int(np.argmax(np.abs(column)))
                assert abs(column[out]) == pytest.approx(1.0)
                if control == 0:
                    assert out == (y << 1)
                elif 1 <= y <= 14:
                    assert out == ((m * y % 15) << 1 | 1), (m, y)
                else:  # 0 and 15 are never reached; rotations fix them, NOT variants swap them
                    assert out >> 1 in (0, 15)


@pytest.mark.parametrize("N,t", [(15, 8), (21, 10)])
def test_continued_fractions_recover_r_from_ideal_outcomes(N, t):
    """For m = s * 2^t / r exactly (rounded to the nearest integer when r is not a power of 2),
    the continued fraction returns r whenever gcd(s, r) = 1."""
    for a in UNITS[N]:
        r = shor.order(a, N)
        for s in range(r):
            m = round(s * 2**t / r) % 2**t
            candidate = shor.period_from_measurement(m, t, N)
            assert r % candidate == 0  # always a divisor of r at these ideal points
            if math.gcd(s, r) == 1:
                assert candidate == r, (a, s)


def test_factors_from_order_rejects_multiples_of_the_period():
    assert shor.factors_from_order(2, 21, 12) == (None, "a^(r/2) = 1 (mod N): r is a multiple of the period, not the period")


@pytest.mark.parametrize("N,a", [(15, 7), (15, 11), (21, 2), (21, 8)])
def test_readout_distribution_peaks_near_s_over_r(N, a):
    t = 2 * N.bit_length()
    r = shor.order(a, N)
    probabilities = shor.readout_distribution(a, N)
    assert probabilities.sum() == pytest.approx(1.0)
    near = sum(probabilities[m] for m in range(2**t) if min(abs(m / 2**t - s / r) for s in range(r + 1)) <= 1 / 2**t)
    assert near > 0.8  # most weight within one step of some s/r
