# Lesson 24: Shor's 9-qubit code

## The idea
The bit-flip code guards against X and the phase-flip code against Z (Lessons 22–23). Peter Shor's 1995 code **nests** them. First encode the qubit with the phase-flip code into three qubits. Then encode each of those with the bit-flip code into a **block** of three. That makes 9 physical qubits for 1 logical qubit.

Inside each block, two parity checks catch a bit flip, as in Lesson 22. Across blocks, two more checks compare the blocks' signs and catch a phase flip, as in Lesson 23. A Y error is an X and a Z at once, so both kinds of check fire and both get fixed. And because any single-qubit error can be written as a mix of I, X, Y and Z, and the syndrome measurement forces it to pick one, fixing those four fixes **every** single-qubit error.

## Predict first
1. How many different single-qubit Pauli errors are there on 9 qubits, and how many does the code correct?
2. Which two-error combinations can it still fix?
3. Under random depolarizing noise, is 9 qubits always better than 1?

## How to run

    .venv/bin/python lessons/24_shor_nine_qubit_code.py

It prints four labelled steps and saves `lessons/out/24_shor_nine_qubit_code.png` (under 10 seconds). The circuit has 9 data qubits and 8 ancillas (17 in total), on Aer's stabilizer method.

## What you should see, and why
Answers are below.

## Spoiler
1. 27 (X, Y and Z on each of 9 qubits), and all 27 are corrected on all six inputs (|0⟩, |1⟩, |±⟩, |±i⟩). That is enough to catch any leftover logical error, because each of X, Y and Z would flip at least two of those states. The syndromes show the structure: X on qubit 4 fires block 1's checks (11), Z on qubit 4 fires the between-block checks (11), and Y fires both. A non-stabilizer input, RY(0.7)|0⟩, also comes back with fidelity 1.000000000000 after X4, Y7, Z0 or Y8. Without the correction round, Y0 leaves fidelity 0.
2. One bit flip **per block** plus at most one phase flip overall. X on qubits 0 and 3 (different blocks) is corrected, and so are X2 with Z7, and Z0 with Z1 (in the same block, two Zs cancel as a block sign). But two Xs in one block, or Zs in two different blocks, cause a logical error.
3. No. With independent depolarizing noise of probability p on each of the 9 qubits, the logical error rate is 0.0012 against 0.0067 for a bare qubit at p = 0.01, and 0.0088 against 0.0200 at p = 0.03. It grows roughly like p², since failure needs two errors. At p = 0.001 and 0.003 no logical error appeared in 12,000 shots. But at p = 0.1 it is 0.0797 against 0.0667: nine qubits collect errors nine times as fast, and above a crossover (here between p = 0.05 and 0.1) the code hurts.

**Classical baseline.** Classical data never needs the phase half. The quantum price is 9 qubits and 8 syndrome measurements to protect one qubit against one error.

**What this does NOT show.** Noisy syndrome extraction and repeated rounds (the ancillas, CNOTs and measurements here are perfect), or computing on encoded qubits. Modern codes such as the surface code (Lesson 25) do better with nearest-neighbour hardware.
