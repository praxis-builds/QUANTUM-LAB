# Lesson 23: the phase-flip code

## The idea
Qubits suffer a second kind of error with no classical counterpart: the **phase flip** Z, which turns |+⟩ into |−⟩ and leaves |0⟩ and |1⟩ alone (Lesson 03). The bit-flip code of Lesson 22 cannot see it. A Z on any one qubit turns a|000⟩ + b|111⟩ into a|000⟩ − b|111⟩, and every parity check still says "all fine".

The fix is to rotate the whole code into the Hadamard basis. Encode as before, then apply H to all three qubits: the logical qubit becomes a|+++⟩ + b|−−−⟩. In this basis a Z error behaves exactly like an X error did before (H turns Z into X). So the same parity checks, done between H layers, find and fix it. The price: this code is now blind to X errors.

## Predict first
1. What syndromes does the phase-flip code give for a Z on each qubit?
2. Which input states survive a single X error in the phase-flip code? A single Z in the bit-flip code?
3. With p = 0.1 on each qubit, is a code facing the "wrong" error type better or worse than no code at all?

## How to run

    .venv/bin/python lessons/23_phase_flip_code.py

It prints three labelled steps (no plot) in a couple of seconds. The six test inputs are |0⟩, |1⟩, |+⟩, |−⟩, |+i⟩ and |−i⟩, and together they reveal any logical error.

## What you should see, and why
Answers are below.

## Spoiler
1. 01, 11 and 10 for qubits 0, 1 and 2, the same as the bit-flip code with X. Every single Z is corrected on all six inputs.
2. Only |0⟩ and |1⟩, in both cases, whichever qubit is hit. The uncorrectable error passes straight through as a **logical Z**, which leaves the logical basis states alone and flips every superposition. A single Y (= X and Z together) does the same to both codes: the half the code understands is fixed, the other half gets through.

   | | single X | single Z | single Y |
   |---|---|---|---|
   | bit-flip code | all 6 survive | only \|0⟩, \|1⟩ | only \|0⟩, \|1⟩ |
   | phase-flip code | only \|0⟩, \|1⟩ | all 6 survive | only \|0⟩, \|1⟩ |

3. **Worse.** Facing its own error type, the logical error rates are 0.0280 and 0.0297 (formula 3p² − 2p³ = 0.0280). Facing the other type, the logical qubit flips whenever an **odd** number of the three qubits is hit: 0.2387 and 0.2520 measured, (1 − (1 − 2p)³)/2 = 0.2440 in theory, against 0.1 for a bare qubit. Three qubits give the error three targets instead of one.

**Classical baseline.** Classical bits have no phase, so the classical repetition code only ever meets the Lesson 22 problem. Needing to guard two independent error types at once is what makes quantum codes harder. Lesson 24 combines both codes to do it.

**What this does NOT show.** Noisy syndrome extraction: the H layers, CNOTs and ancilla measurements here are perfect.
