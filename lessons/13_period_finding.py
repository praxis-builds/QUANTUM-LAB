"""Lesson 13: period finding, classically. Given the period r of a^x mod N, factoring is easy."""

from __future__ import annotations

import math

import numpy as np

from _common import SEED, heading
from _shor import factors_from_order, order

RETRY_TRIALS = 20_000


def analyse(N: int) -> dict[int, dict]:
    """For every a in 2..N-1: a lucky shared factor, or the period and what it gives."""
    rows = {}
    for a in range(2, N):
        shared = math.gcd(a, N)
        if shared > 1:
            rows[a] = {"kind": "lucky", "factors": (shared, N // shared)}
            continue
        r = order(a, N)
        factors, reason = factors_from_order(a, N, r)
        rows[a] = {"kind": "ok" if factors else "fail", "r": r, "factors": factors, "reason": reason,
                   "powers": [pow(a, x, N) for x in range(r + 1)]}
    return rows


def show(N: int, rows: dict[int, dict]) -> None:
    for a, row in rows.items():
        if row["kind"] == "lucky":
            print(f"a = {a:>2}: gcd(a, {N}) = {row['factors'][0]} already divides N (a lucky pick, no period needed)")
            continue
        powers = " ".join(map(str, row["powers"]))
        r = row["r"]
        if row["kind"] == "ok":
            half = pow(a, r // 2, N)
            print(f"a = {a:>2}: {a}^x mod {N} = {powers:<22} r = {r};  a^(r/2) = {half}:  "
                  f"gcd({half}-1, {N}) = {math.gcd(half - 1, N)}, gcd({half}+1, {N}) = {math.gcd(half + 1, N)}  ->  "
                  f"{row['factors'][0]} x {row['factors'][1]}")
        else:
            print(f"a = {a:>2}: {a}^x mod {N} = {powers:<22} r = {r};  FAILS: {row['reason']}")


def retry_statistics(N: int, rows: dict[int, dict], rng: np.random.Generator) -> dict:
    """Pick a uniformly from 2..N-1 until one works (lucky or a usable period)."""
    good = [a for a, row in rows.items() if row["kind"] != "fail"]
    tries = []
    for _ in range(RETRY_TRIALS):
        count = 1
        while int(rng.integers(2, N)) not in good:
            count += 1
        tries.append(count)
    return {"p_success": len(good) / len(rows), "mean_tries": float(np.mean(tries)), "max_tries": max(tries)}


def main() -> dict:
    heading("Step 1: N = 15, every a from 2 to 14")
    rows15 = analyse(15)
    show(15, rows15)

    heading("Step 2: N = 21, where odd periods also appear")
    rows21 = analyse(21)
    show(21, rows21)
    print("Two ways to fail: r odd (no a^(r/2)), or a^(r/2) = -1 mod N (then a^(r/2) + 1 is")
    print("a multiple of N and the gcds give only 1 and N). Either way: pick another a.")

    heading(f"Step 3: just retry ({RETRY_TRIALS} seeded trials each)")
    rng = np.random.default_rng(SEED)
    retry = {}
    for N, rows in ((15, rows15), (21, rows21)):
        retry[N] = retry_statistics(N, rows, rng)
        print(f"N = {N}: a random a works with probability {retry[N]['p_success']:.3f}; "
              f"mean tries {retry[N]['mean_tries']:.3f}, max {retry[N]['max_tries']}")

    heading("Step 4: the classical cost of finding r")
    for N, rows in ((15, rows15), (21, rows21)):
        periods = [row["r"] for row in rows.values() if "r" in row]
        print(f"N = {N}: brute force needs r multiplications, at most {max(periods)} here")
    print("For an RSA modulus N = p*q the period divides lcm(p-1, q-1), which can be close to N/2:")
    print("for 2048-bit N, a number with over 600 digits. This loop is hopeless there. Finding r is")
    print("the only step Shor's quantum part does; lessons 14-15 do it.")
    return {"rows15": rows15, "rows21": rows21, "retry": retry}


if __name__ == "__main__":
    main()
