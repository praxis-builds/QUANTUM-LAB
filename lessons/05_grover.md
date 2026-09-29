# Lesson 05: Grover search on 2 qubits

## The idea
Suppose four boxes hide one prize and you may ask an **oracle** (a black box that says "yes" only for the prize box; here it flips the sign of the prize's amplitude). A classical searcher opens boxes one at a time. **Grover's algorithm** uses interference (Lesson 02) instead.

Start with all four boxes equally likely (amplitude +0.5 each). The oracle flips the prize's amplitude to −0.5. That sign is invisible to measurement (Lesson 03), but the next step, the **diffusion** step (reflect every amplitude about the average), makes the prize's amplitude add up to 1 while the others cancel to 0. For four items, one oracle call finds the prize with certainty.

This is a toy: it counts oracle calls for 4 items. It is not evidence of a practical speed-up.

## Predict first
1. After the H gates, what is the probability of each of the four items?
2. After the oracle (before diffusion), does the probability of the marked item change? Does its amplitude?
3. A classical search opens boxes in random order and stops when it finds the prize. On average, how many boxes does it open (a search never needs a 4th guess: after 3 misses the last box is known)?

## How to run

    .venv/bin/python lessons/05_grover.py

It prints four labelled steps (no plot). The marked item is |10> (qubit 1 = 1, qubit 0 = 0).

## What you should see, and why
Answers are below.

## Spoiler
1. 0.25 each (amplitude +0.50, and 0.50² = 0.25).
2. The probability stays 0.25; the amplitude changes sign from +0.50 to −0.50. Measurement cannot see this.
3. 2.25 boxes: the prize is in position 1, 2, 3 or 4 with equal chance, costing 1, 2, 3 and 3 guesses, so (1 + 2 + 3 + 3) / 4 = 2.25. The simulation over 200,000 random orders gave 2.247.

After the diffusion step the amplitudes are 0, 0, −1, 0. The −1 is a global sign, which cannot be measured, and the probability is 1.00. Aer confirms it: 2,000 of 2,000 shots gave "10". Step 3 repeats the search for all four possible marked items, and each reaches probability 1.000000.

What to notice: the oracle did nothing measurable on its own. The algorithm worked because a later interference step converted a sign into a probability. Grover used one oracle call against 2.25 for the classical search. With only four items this says nothing about speed: for a fair comparison you would need many items and a classical baseline that can exploit the structure of the problem.
