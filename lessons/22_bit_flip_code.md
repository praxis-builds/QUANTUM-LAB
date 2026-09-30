# Lesson 22: the 3-qubit bit-flip code

## The idea
Classically, you protect a bit by sending three copies and taking a majority vote. A qubit cannot be copied (the no-cloning theorem), but it can be **encoded**: two CNOTs turn a|0⟩ + b|1⟩ into a|000⟩ + b|111⟩. That is one **logical qubit** stored in three **physical qubits**.

To find a flipped qubit without looking at (and destroying) a and b, we measure only **parities**: is qubit 0 equal to qubit 1, and is qubit 1 equal to qubit 2? Two **ancilla** qubits collect these parities. The two answers, the **syndrome**, point to the flipped qubit (or say "none") and reveal nothing about a or b. We flip that qubit back and undo the encoding.

With flips of probability p on each qubit, the code fails only when two or three qubits flip: probability 3p² − 2p³.

## Predict first
1. What syndrome does a flip on each of the three data qubits produce? Does the correction work for every input state, including superpositions?
2. What happens with two flips?
3. For which p does the code make things better than an unprotected qubit?

## How to run

    .venv/bin/python lessons/22_bit_flip_code.py

It prints four labelled steps and saves `lessons/out/22_bit_flip_code.png` (a few seconds). Data qubits 0–2, ancillas 3–4; Aer's stabilizer method with mid-circuit measurement and classically controlled corrections.

## What you should see, and why
Answers are below.

## Spoiler
1. Syndromes 01, 11 and 10 for a flip on qubit 0, 1 and 2 (bit 0 compares qubits 0 and 1, bit 1 compares qubits 1 and 2), and 00 for no flip. Every single flip is corrected on all six test inputs (|0⟩, |1⟩, |±⟩, |±i⟩). The superpositions survive because the syndrome is the same for a|000⟩ and b|111⟩, so measuring it does not disturb a or b.
2. The code fails. Two flips produce the syndrome of a single flip on the *third* qubit, so the "correction" completes a flip of all three: a logical error. Three flips give syndrome 00 and go unnoticed. The four failing patterns (011, 101, 110, 111) have total probability exactly 3p²(1 − p) + p³ = 3p² − 2p³ (enumeration agrees with the formula to 2 × 10⁻¹⁶).
3. Whenever p < 1/2. Over 4,000 seeded shots on each of |0⟩ and |1⟩, the measured rate matches 3p² − 2p³ within 1.8 standard deviations at every p. For example, 0.0290 against 0.0280 at p = 0.1: a 3.4× improvement over the unprotected 0.1. The curves meet at p = 1/2 (break-even) and the code hurts above it. **That break-even is optimistic.** Here the encoding, the ancillas and the parity measurements are perfect; only the data qubits get errors. In real hardware those steps fail too, which moves the break-even far lower (Lesson 25).

**Classical baseline.** This is the classical repetition code with majority voting, and its error formula is the same. The quantum part is doing it without reading the data qubits, which preserves superpositions.

**What this does NOT show.** Protection against phase errors (Z). A Z on any one qubit turns a|000⟩ + b|111⟩ into a|000⟩ − b|111⟩, and this code cannot see it (Lesson 23). Nor does it show noisy syndrome measurement or repeated rounds.
