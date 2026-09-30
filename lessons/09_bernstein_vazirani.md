# Lesson 09: Bernstein–Vazirani, a hidden string in one query

## The idea
The oracle hides an n-bit string s. Asked about an input x, it answers one bit: f(x) = s·x mod 2, the parity of the positions where both s and x have a 1. Your job is to find s.

The circuit is the same as Deutsch–Jozsa (Lesson 08): H on every input, one oracle call with the output qubit in |−⟩, H again. Phase kickback (Lesson 07) leaves each |x⟩ with the sign (−1)^(s·x). That exact pattern of signs is what H gates make from the single state |s⟩, and H undone is H again. So the final H gates turn the signs back into |s⟩, and one measurement reads out all n bits of s at once.

## Predict first
1. For s = 101, what fraction of shots do you expect to return 101?
2. A classical program asks f(x) for chosen x. Which inputs would you ask to learn s, and how many do you need?
3. Could any classical method use fewer queries than that?

## How to run

    .venv/bin/python lessons/09_bernstein_vazirani.py

It prints three labelled steps (no plot) for five hidden strings: 101, 011, 0110, 1111, 1001. Bit strings use Qiskit's order (qubit 0 on the right).

## What you should see, and why
Answers are below.

## Spoiler
1. All of them: P(101) = 1.000000 and 1000 of 1000 shots give "101". The same holds for every s in the list, at n = 3 and n = 4.
2. Ask x = 0…01, 0…10, …, 10…0. Then s·x picks out one bit of s per query, so n queries (3 for 101, 4 for 0110). The script does this and recovers every s.
3. No. Each answer is one bit and s has n unknown bits, so any classical method, even a randomised one, needs n queries.

**Classical baseline.** n queries, and that is optimal. Quantum: 1 query. The gap grows linearly (n against 1), not exponentially.

**What this does NOT show.** The oracle is given for free, and it is only a few CNOT gates that contain s in plain sight: whoever built it already knew s. Real problems do not arrive as a parity oracle. This is a toy that shows phase kickback and interference reading out a whole string. It is not a practical speed-up.
