# Lesson 13: period finding, classically

## The idea
Pick a number a that shares no factor with N and look at a⁰, a¹, a², … mod N. The list repeats: after r steps it returns to 1. That r is the **period** (or **order**) of a mod N.

Knowing r, factoring N is easy. If r is even, a^r − 1 = (a^(r/2) − 1)(a^(r/2) + 1) is a multiple of N. Unless one bracket is itself a multiple of N, each bracket shares a proper factor with N, and a **gcd** (greatest common divisor, fast even for huge numbers) pulls it out. For N = 15 and a = 7: 7ˣ mod 15 runs 1, 7, 4, 13, 1, so r = 4 and 7² mod 15 = 4, giving gcd(3, 15) = 3 and gcd(5, 15) = 5.

**Shor's quantum part does only one thing: find r.** Everything else here is classical maths.

## Predict first
1. For N = 15, which values of a from 2 to 14 fail to give the factors, and why?
2. For N = 21, what two different ways can a fail?
3. If you pick a at random and retry after a failure, how many tries do you expect for N = 21?

## How to run

    .venv/bin/python lessons/13_period_finding.py

It prints four labelled steps (no plot, no quantum circuit: this lesson is purely classical).

## What you should see, and why
Answers are below.

## Spoiler
1. Only a = 14: its period is 2, and 14¹ ≡ −1 mod 15, so a^(r/2) + 1 = 15 and the gcds are just 15 and 1. Six values (3, 5, 6, 9, 10, 12) share a factor with 15, so gcd(a, 15) is already a factor: a lucky pick with no period needed. The other six units give 3 × 5.
2. **r odd** (a = 4 and 16 have r = 3, so a^(r/2) does not exist), and **a^(r/2) ≡ −1 mod N** (a = 5, 17 and 20). Six units work (2, 8, 10, 11, 13, 19), and eight a are lucky.
3. A random a from 2 to 20 works with probability 14/19 = 0.737; the seeded simulation needed 1.362 tries on average (theory 19/14 = 1.357), with at most 9. For N = 15 it is 12/13 = 0.923 and 1.082 tries. It is a theorem that for N with at least two distinct odd prime factors, at least half of the units work, so retrying is cheap.

**Classical baseline.** Here brute force finds r in at most 4 (N = 15) or 6 (N = 21) multiplications. For an RSA modulus N = p·q, r divides lcm(p − 1, q − 1), which can be close to N/2: for 2048-bit N, a number with over 600 digits. So this loop is hopeless there. The best known classical factoring method, the general number field sieve, does not search for r at all. It is far faster than this loop, but it is still infeasible for 2048-bit RSA with today's computers.

**What this does NOT show.** No quantum computer is involved yet. It shows why a fast period finder would break RSA, not that one exists at a useful size.
