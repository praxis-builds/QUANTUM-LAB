# Lesson 17: Grover on n qubits

## The idea
Lesson 05 found 1 marked item among 4 in one step. With N = 2ⁿ items and M marked, each **Grover iteration** (oracle sign flip, then diffusion) **rotates** the state by a fixed angle 2θ toward the marked items, where sin θ = √(M/N). After k iterations, P(success) = sin²((2k + 1)θ).

So the best number of iterations is about (π/4)·√(N/M): the rotation reaches the marked direction. The cost grows with the **square root** of N, where a classical search checking items one by one grows with N itself. The rotation does not stop by itself, though. Run too many iterations and it turns past the answer, and success falls again.

## Predict first
1. For n = 8 (N = 256, one marked item), how many iterations are best, and how close to certain is the answer?
2. What happens if you run twice that many?
3. With n = 6 and k tuned for M = 1, what happens when there are really M = 2, 4 or 8 marked items?

## How to run

    .venv/bin/python lessons/17_grover_n_qubits.py

It prints three labelled steps and saves `lessons/out/17_grover_iterations.png` (about 7 seconds). Success probabilities come from the simulated state vector after each iteration and are compared with the formula.

## What you should see, and why
Answers are below.

## Spoiler
1. k = 12, since (π/4)·√256 = 12.57, and P = 0.9999. Every n from 2 to 8 exceeds 0.94 at its optimum (n = 3 is the lowest, 0.9453, because k must be a whole number). The state vector matches sin²((2k + 1)θ) to four decimals, and Aer agrees (n = 4: 964 of 1,000 shots).
2. It collapses: n = 8 falls from 0.9999 to 0.0059 at k = 24, and n = 6 from 0.9966 to 0.0001. That is **over-rotation**: the state has turned as far past the answer as it had turned toward it. Keep going and it comes back, periodically (left plot).
3. It depends, unpredictably. With k = 6: M = 2 gives 0.546, M = 4 gives 0.020, and M = 8 happens to give 1.000, because 13θ lands near 3π/2 there (right plot). A wrong k gives a lottery ticket, not a reliable answer. **Fixes:** the BBHT method (Boyer, Brassard, Høyer and Tapp, 1998) picks k at random below a bound that grows by 6/5 after each failure. It needs no knowledge of M and still costs O(√(N/M)): 12.7, 8.7, 5.8 and 3.9 oracle calls on average for M = 1, 2, 4, 8 (5,000 seeded trials, checks included). **Quantum counting** estimates M first, by phase estimation (Lesson 12) on the Grover iteration, whose eigenphases encode θ. It is described here, not built.

**Classical baseline.** Checking random unseen items until a marked one turns up costs (N + 1)/(M + 1) queries on average: 32.5, 21.7, 13.0 and 7.2 for n = 6. That is N/2 against about √N for one marked item.

**What this does NOT show.** The oracle here was handed to us: a sign flip on a known item. For a real search the oracle must compute the property being searched for, and Lessons 18–20 show what that costs. At these sizes nothing is faster than a classical loop over 256 items.
