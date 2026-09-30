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
