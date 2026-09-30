# Lesson 10: Simon, a hidden period (the idea behind Shor)

## The idea
The oracle computes f on n bits with a hidden **period** s ≠ 0: f(x) = f(x ⊕ s) for every x, and no other inputs share an output. Find s.

One run: H on the inputs, one oracle call into an n-qubit output register, H on the inputs, measure the inputs. The output register ends up holding some value f(x₀), which leaves the inputs in (|x₀⟩ + |x₀ ⊕ s⟩)/√2. The final H gates make the two paths cancel for every y with y·s = 1 (mod 2). So each run returns a random y with **y·s = 0**: one linear equation about s. Collect about n of them and solve with ordinary linear algebra over GF(2) (arithmetic where 1 + 1 = 0, i.e. XOR).

**Shor's algorithm, which breaks RSA, uses exactly this hidden-period idea**, with a different kind of period (below).

## Predict first
1. For s = 110, which of the 8 possible outcomes y can appear?
2. How many runs does the quantum method need on average to pin down s for n = 2, 3, 4? (Each run is a random y from the 2^(n−1) strings orthogonal to s; you need n − 1 independent ones, and y = 0 tells you nothing.)
3. A classical program queries f at random inputs until two outputs collide, and then s = x ⊕ x′. How many queries does that take on average for n = 2, and at worst for n = 4? Which method is better at n = 4?

## How to run

    .venv/bin/python lessons/10_simon.py

It prints five labelled steps (no plot) for s = 11, 110 and 1010, in about two seconds. Each Aer shot is one run (one oracle call); step 3 feeds the runs to the solver one at a time, 200 independent repeats per s.

## What you should see, and why
Answers are below.

## Spoiler
1. 000, 001, 110 and 111: exactly the four strings with y·s = 0. Over 2,000 shots no other outcome appears, for all three s (n = 2 gives only 00 and 11; n = 4 gives 8 of 16).
2. Theory: the sum over k = 0 … n−2 of 2^(n−1) / (2^(n−1) − 2^k), which is 2, 3.33 and 4.48. Observed over 200 repeats: 1.89, 3.35 and 4.58, and s was recovered 200/200 times for each. The unluckiest repeats needed 8, 10 and 13 runs.
3. n = 2: 2.67 on average (observed 2.66). n = 4: at worst 2^(n−1) + 1 = 9 queries (mean 5.07). **At n = 4 neither method is clearly better:** the quantum mean is a bit lower (4.58 against 5.07), but its unlucky repeats (13) cost more than the classical worst case (9). The separation is in growth only: the classical collision search needs about 2^(n/2) queries, and the quantum method needs about n runs plus polynomial-time elimination.

**Classical baseline.** Random collision search: mean 2.66, 3.66 and 5.07 queries for n = 2, 3, 4, worst case 2^(n−1) + 1. That is shown by simulation (20,000 seeded trials), not assumed.

**Why this matters for RSA.** Simon finds an XOR period: f(x) = f(x ⊕ s). Shor's order finding finds an integer period: f(x) = aˣ mod N repeats every r steps, f(x) = f(x + r). The recipe is the same: superposition, one oracle call per run, interference to expose the period (the quantum Fourier transform instead of H gates, program step 3), then classical post-processing. From r, a greatest-common-divisor calculation usually gives a factor of N, and factoring N is what breaks RSA.

**What this does NOT show.** Nothing here breaks RSA or any real cryptography. The oracle is handed to us for free, and it contains s in plain sight. Our s has at most 4 bits, and at that size the classical method is just as good. Breaking real RSA would need a large, error-corrected quantum computer that does not exist yet. This is a toy that shows the hidden-period idea; it makes no practical speed-up claim.
