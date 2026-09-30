# Lesson 08: Deutsch–Jozsa, constant or balanced

## The idea
You are given an oracle for f on n bits and a **promise**: f is either **constant** (the same answer for every input) or **balanced** (0 for exactly half the inputs, 1 for the other half). Which is it?

Deutsch–Jozsa puts all 2ⁿ inputs in superposition with H gates, makes **one** oracle call with the output qubit in |−⟩ (phase kickback, Lesson 07), then applies H to the inputs again. The final amplitude of |0…0⟩ is the average of all the signs (−1)^f(x). For a constant f every sign is the same, so the average is ±1 and you measure 0…0 every time. For a balanced f the signs are half +, half −, so the average is exactly 0 and you never measure 0…0. Interference does the counting.

## Predict first
1. For n = 2 there are 2 constant and 6 balanced functions. For each kind, what is the probability of measuring 00?
2. Does anything change for n = 3 or n = 4?
3. How many classical queries does it take to be **certain**, for n = 4? And if you accept being wrong sometimes, how often is a random classical tester with 3 queries wrong?

## How to run

    .venv/bin/python lessons/08_deutsch_jozsa.py

It prints three labelled steps (no plot), in about five seconds. A function is written as its values for x = 0, 1, 2, …, left to right, so "1100" means f(0) = f(1) = 1 and f(2) = f(3) = 0. Measured bit strings use Qiskit's order (qubit 0 on the right).

## What you should see, and why
Answers are below.

## Spoiler
1. Constant: P(00) = 1.000000 and 1000 of 1000 shots give "00". Balanced: P(00) = 0 (below 10⁻³⁰, which is rounding), and no shot gives "00". The other outcomes differ per function: "1100" (f = NOT x₁) gives "10", and "0110" (f = x₀ XOR x₁) gives "11". For n = 2 every balanced function is s·x mod 2 or its complement, and the measured string is exactly s. That is Lesson 09.
2. No. P(0…0) is 1.000000 for both constant functions at every n, and at most 4 × 10⁻³¹ for every balanced function checked: all of them for n ≤ 3 (2, 6 and 70) and a seeded sample of 50 of the 12,870 for n = 4.
3. Up to 2^(n−1) + 1 = 9 for n = 4. After 8 equal answers f could still be balanced; the 9th settles it. The script's deterministic tester hits exactly this worst case (2, 3, 5, 9 for n = 1–4), always on a constant f. A random tester that says "constant" when all its answers agree is wrong on a balanced f with probability 0.2000 at 3 queries (simulated 0.1961 over 20,000 trials), 0.0769 at 4 queries, falling by more than half with each extra query.

**Classical baseline.** Certain answer: 2^(n−1) + 1 queries in the worst case, against 1 quantum query. With a small allowed error, a classical tester needs only a handful of queries whatever n is.

**What this does NOT show.** The gap is only for a *certain* answer and only under the promise; drop the promise and the question is different. The oracle is given for free. For n = 4 the "exponential" gap is 9 queries against 1, and a probabilistic classical method closes most of it. This is a toy problem that teaches interference, not a practical speed-up.
