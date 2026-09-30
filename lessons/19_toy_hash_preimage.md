# Lesson 19: toy hash preimages and the square-root speed-up

## The idea
A **hash function** maps any input to a short output. A **preimage attack** is given an output (the target) and looks for an input that hashes to it. With no structure to exploit, the classical attacker tries inputs at random, and the cost doubles with every extra input bit. Grover's cost should grow only by √2 per bit: the famous square-root speed-up.

This lesson **measures** that growth instead of assuming it. The toy hash maps n bits to n − 1: out_i = x_i ⊕ (x_{i+1} AND x_{i+2}) ⊕ x_{i+3}. It is nonlinear because of the AND, similar in spirit to one step of SHA-3's permutation, and it is built from CNOT and Toffoli gates. For each n from 4 to 10 we pick a target with exactly 2 preimages, run Grover on Aer, and count oracle calls. Then we fit the slope of log₂(calls) against n.

## Predict first
1. If the classical cost doubles per bit, what slope do you expect for log₂(classical calls) against n? And for Grover?
2. Does counting one extra hash evaluation per attempt (to check the answer) change the slope?
3. At n = 10 (1,024 inputs), roughly how many calls does each method need?

## How to run

    .venv/bin/python lessons/19_toy_hash_preimage.py

It prints three labelled steps and saves `lessons/out/19_hash_scaling.png` (a few seconds). Circuits grow from 7 to 19 qubits: n input qubits plus n − 1 for the hash output.

## What you should see, and why
Answers are below.

## Spoiler
1. Classical about 1, Grover about 0.5. Measured over n = 4..10: **Grover 0.498, classical 0.985**. Grover succeeds with probability 0.946–1.000 at the optimal k, matching theory within 0.01. The classical random search matches (N + 1)/3 within 4%. This test passes if the Grover slope lies in [0.4, 0.6] and the classical one in [0.9, 1.1].
2. Yes, at these tiny sizes: with the check it is 0.417. A constant +1 matters when k is only 2–17, and it flattens the small-n end. As n grows, the +1 becomes negligible and the slope tends to 0.5. Both fits are shown, so the choice of counting cannot hide in the headline number.
3. Grover: 17 iterations (18 with the check), succeeding 0.999 of the time. Classical: 336 hashes on average (theory 341.7). About 20× fewer calls, from a √N against N/3 law.

**Honesty notes.** Each Grover oracle call evaluates the hash **twice**, reversibly (compute, then uncompute), and on a fault-tolerant machine each reversible evaluation is far slower than a classical one. A constant factor like that does not change the slope, but it does move where the lines cross for real hashes (Lesson 20). The targets were chosen classically, by listing all inputs, so that M = 2 at every size. That is experiment design to isolate the dependence on N; a real attacker cannot choose. The Grover runs themselves never used that list.

**Classical baseline.** Random unseen inputs until a hit: measured 5.6 to 336 calls for n = 4 to 10 (2,000 seeded trials each).

**What this does NOT show.** A speed-up in wall-clock time: the "quantum" runs are classical simulations, and the classical search over 1,024 inputs is instant. The slope is a statement about oracle calls, which is exactly what Lesson 20 extrapolates.
