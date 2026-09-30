# Lesson 18: toy key search with Grover

## The idea
A **known-plaintext attack**: the attacker has a plaintext P and its ciphertext C and wants the key k with Enc_k(P) = C. Classically you try keys one by one. Grover searches all keys in superposition.

The oracle must answer "does this key encrypt P to C?", so it has to **run the cipher inside the quantum circuit**. It computes Enc_k(P) into spare qubits, flips the sign if the result equals C, then runs the cipher again to **uncompute** (erase) the spare qubits. Otherwise they would stay entangled with the key and spoil the interference.

Our toy cipher has a 4-bit key: Enc_k(P) = S(P ⊕ k) ⊕ k, where S is PRESENT's 4-bit S-box, a fixed public table. One pair can fit more than one key. The extra keys are **false positives**, and a second pair removes them.

## Predict first
1. The brief suggested Enc_k(P) = S(P ⊕ k). Can a single pair ever fit two keys for that cipher?
2. With one pair that fits 2 keys, what does Grover return, and how often is it the real key?
3. With both pairs, how many oracle calls does Grover need, compared with classical brute force (average 2⁴/2)?

## How to run

    .venv/bin/python lessons/18_toy_key_search.py

It prints five labelled steps (no plot) in about five seconds. The key is on qubits 0–3; each known pair needs 4 more qubits for the cipher output (8 or 12 qubits in total).

## What you should see, and why
Answers are below.

## Spoiler
1. **No.** For fixed P, the map k → S(P ⊕ k) is a bijection, because XOR with P and the S-box are both permutations. So each C fits exactly one key, and that cipher can never show a false positive. Adding the key again after the S-box breaks that. Now, over all 16 plaintexts, one pair leaves 1 or 2 candidate keys.
2. The pair P = 0001, C = 0100 fits keys 0100 and 1011 (the secret). The oracle's truth table flips exactly those two signs and returns every work qubit to 0. Grover with M = 2 needs 2 iterations. It returns a matching key 0.954 of the time (theory 0.945), but split almost evenly: 978 × 1011 and 929 × 0100 out of 2,000. So the real key is only 0.489 likely: half the successes are the false positive.
3. The second pair (0000 → 0011) fits only 1011. With both, the oracle marks one key, Grover needs 3 iterations, and 1,932 of 2,000 shots give 1011 (0.966, theory 0.961). Counting one classical check per attempt, that is about 4.1 expected oracle calls, against 8.43 trials for classical brute force (theory (16 + 1)/2 = 8.5).

**Honesty note: the oracle is where the real cost lives.** Each Grover call runs the whole cipher reversibly, twice per known pair (compute, then uncompute), so 4 cipher runs per call here. Our 4-bit toy already needs 390 multi-controlled gates in the full circuit. For AES the oracle is a complete reversible AES circuit with thousands of logical qubits (Lesson 20), and Grover must call it about 2^64 times one after another for a 128-bit key. The oracle here uses only public parts of the cipher (the S-box table, XORs), never a table of keys, so it does not smuggle in the answer.

**Classical baseline.** Random-order brute force, checking both pairs: 8.43 trials on average (20,000 seeded trials). Each classical trial is one cheap cipher evaluation, while each quantum call is 4 reversible cipher evaluations on a fault-tolerant machine.

**What this does NOT show.** A practical attack: 4 against 8.5 calls on a 16-key toy says nothing about real ciphers, where Grover only halves the key length in bits (Lesson 20).
