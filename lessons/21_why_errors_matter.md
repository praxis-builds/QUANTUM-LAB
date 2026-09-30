# Lesson 21: why errors matter

## The idea
Real quantum gates are imperfect. A simple model is **depolarizing noise**: after each gate, with probability p, the qubits it touched are hit by a random Pauli error. Lesson 06 showed one Grover step fading toward random guessing. Here we run bigger circuits, Shor for N = 15 (Lesson 14) and Grover on 3, 4 and 5 qubits (Lesson 17), compiled to basic gates, with noise of strength p after **every** gate.

The rough rule: a circuit with G gates runs error-free with probability about (1 − p)^G. So bigger circuits need smaller p. A Shor that threatens RSA is enormous, which is why error correction (Lessons 22–25) exists.

## Predict first
1. Shor-15 compiles to 399 gates and Grover n = 5 to 629. Which breaks down sooner as p grows? What about Grover n = 3 (63 gates) against Shor-15?
2. In Shor, does an error on the work register hurt as much as one on the counting register?
3. Shor for N = 21 compiles to about 27,000 gates. At p = 10⁻³, a typical error rate for today's best two-qubit gates, what is the chance that no error happens at all?

## How to run

    .venv/bin/python lessons/21_why_errors_matter.py

It prints four labelled steps and saves `lessons/out/21_why_errors_matter.png` (about 20 seconds). Every point uses 1,000 shots and its own seed (see the note on seeds in Lesson 25). The success measures are: for Shor, the run gives r = 4 (noiseless 0.5, random guessing 0.039); for Grover, the marked item is measured (random guessing 1/2ⁿ). "Normalised" rescales each to 1 = noiseless and 0 = random guessing.

## What you should see, and why
Answers are below.

## Spoiler
1. **Grover n = 5 breaks first:** normalised 0.64 at p = 10⁻³ and 0.01 at p = 10⁻², against 0.92 and 0.51 for Shor-15. Within Grover, size predicts the order exactly (n = 3, 4, 5 have 63, 178 and 629 gates). **But size is not the whole story:** Shor-15 with 399 gates holds up about as well as Grover n = 3 with 63 (0.51 and 0.60 at p = 10⁻²). I expected Shor, the bigger algorithm, to break sooner; for this compiled N = 15 it doesn't.
2. No, and that explains question 1. With noise at p = 10⁻² only on the 166 gates that act purely on the work register, success stays at 0.454 (noiseless 0.498). With noise only on the 233 gates that touch the counting register, it drops to 0.292. Many work-register errors never change which period the counting register reads out. Different circuits have different *sensitive* sizes.
3. (1 − 10⁻³)^27,015 ≈ 1.8 × 10⁻¹². This is an estimate, not a simulation: a noisy N = 21 run did not finish within 10 minutes here. Some errors are harmless (question 2), so the true success is higher, but still hopeless. At p = 10⁻⁴ it is 0.067.

**The point.** A Shor for RSA-2048 runs for hours to days (Lesson 16's estimates), so its error per operation must be far below anything a bare physical qubit achieves. The answer is **error correction**: many noisy physical qubits encode one reliable logical qubit. Lessons 22–25 build the simplest versions.

**Classical baseline.** Random guessing (0.039 for the Shor metric, 1/2ⁿ for Grover) is the floor that noise drags every curve down to. A classical computer runs both tasks without error.

**What this does NOT show.** Real hardware noise. Our model is uniform depolarizing noise after each compiled gate, with perfect measurement and no crosstalk or leakage. The gate counts depend on Qiskit's compiler at optimisation level 1.
