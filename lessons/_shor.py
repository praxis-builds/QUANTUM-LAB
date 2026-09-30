"""Shor's algorithm on toy numbers (shared by lessons 13-16).

The quantum part of Shor only finds the period (order) r of f(x) = a^x mod N.
Everything else here is ordinary classical number theory.
"""

from __future__ import annotations

import math


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
    p, q = math.gcd(half - 1, N), math.gcd(half + 1, N)
    return (min(p, q), max(p, q)), "ok"


def trial_division(N: int) -> tuple[int, int, int]:
    """Classical baseline: try divisors 2, 3, ... Returns (p, N // p, divisions tried)."""
    for tried, candidate in enumerate(range(2, math.isqrt(N) + 1), start=1):
        if N % candidate == 0:
            return candidate, N // candidate, tried
    raise ValueError(f"{N} is prime.")
