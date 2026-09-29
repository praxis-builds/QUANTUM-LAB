# Lesson 02: interference (the key lesson)

## The idea
The **Hadamard gate** (H, a basic operation that turns a definite 0 into an equal mix of 0 and 1) puts a qubit into **superposition**: amplitudes of 0.707 for both outcomes, so measuring gives 50/50. Now apply H a second time. You might expect another 50/50 shuffle, like flipping a coin twice. Instead the qubit returns to 0 every time.

The reason is **interference**: amplitudes, unlike probabilities, can be negative, so paths to the same outcome can add up (constructive) or cancel (destructive). The second H sends two paths to outcome 1 with amplitudes +0.5 and −0.5, which cancel to zero. A classical coin only has probabilities, which are never negative, so nothing can cancel. Interference is the one ingredient quantum algorithms use that classical randomness lacks.

## Predict first
1. One H then measure: what fractions of 0 and 1 do you expect?
2. Two H gates then measure: what do you expect? Guess before you look.
3. Flip a classical fair coin twice (the second flip ignores the first result). What fraction of heads?

## How to run

    .venv/bin/python lessons/02_interference.py

It prints four labelled steps (no plot).

## What you should see, and why
Step 1 lists the amplitudes at each stage. Step 2 breaks the second H into its two paths. Step 3 runs both circuits on local Aer (2,000 shots). Step 4 does the classical coin. Answers are below.

## Spoiler
1. About half and half: this run gave 991 zeros and 1,009 ones.
2. All zeros: 2,000 out of 2,000. The amplitudes after the first H are (+0.707, +0.707). The second H gives the outcome-1 amplitude as 0.707 × 0.707 + 0.707 × (−0.707) = +0.5 − 0.5 = 0, and the outcome-0 amplitude as 0.5 + 0.5 = 1.
3. Still 50/50 after two flips (0.50 and 0.50). The coin's probabilities are never negative, so a second flip can only blur things further; it can never undo the first.

What to notice: the two-H circuit is not "randomising twice". It is a deterministic operation that undoes itself. Nothing was measured between the gates, which is what lets the paths interfere. Measuring in the middle would destroy this.
