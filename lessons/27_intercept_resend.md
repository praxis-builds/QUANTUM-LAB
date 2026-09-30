# Lesson 27: the intercept-resend attack

## The idea
Eve sits on the channel. For every qubit she picks a random basis, measures, and sends Bob a fresh qubit in the state she saw. When she happens to pick Alice's basis, nothing changes and she learns the bit. When she picks the other basis, her measurement randomises the qubit. If Bob then measures in Alice's basis (the only positions kept after sifting), he gets the wrong bit half the time.

So Eve cannot learn anything without leaving errors behind. Alice and Bob catch her by publicly comparing a random **sample** of their sifted bits. Any disagreement is evidence, and they throw the sample away afterwards because it is now public.

## Predict first
1. What error rate (QBER) does Eve cause on the sifted key if she attacks every qubit?
2. If Alice and Bob compare k sample bits, what is the chance they see no error at all and miss her?
3. If Eve attacks only a fraction f of the qubits, what QBER does she cause, and how much of the key does she learn for certain?

## How to run

    .venv/bin/python lessons/27_intercept_resend.py

It prints three labelled steps and saves `lessons/out/27_detection.png` (a few seconds). Eve is a mid-circuit measurement on Aer in her randomly chosen basis. 20,000 qubits per run.

## What you should see, and why
Answers are below.

## Spoiler
1. **About 25%:** measured 0.2524. The breakdown shows why. On the 49.9% of sifted bits where Eve guessed Alice's basis, the error rate is 0.0000. Where she guessed wrong it is 0.5034. And ½ × ½ = ¼.
2. **(3/4)^k**, because each sampled bit is clean with probability 3/4. Simulated over 20,000 trials per k: 0.7469, 0.2318 and 0.0540 for k = 1, 5 and 10 (formula 0.75, 0.2373, 0.0563), and 0.0040 at k = 20 (formula 0.0032, within sampling error). Comparing 49 bits pushes P(miss) below one in a million.
3. QBER ≈ f/4, and Eve knows ≈ f/2 of the sifted key for certain (the bits where she used Alice's basis). Measured: f = 0.1 → 0.0295 and 0.0509; 0.25 → 0.0682 and 0.1227; 0.5 → 0.1218 and 0.2493; 1 → 0.2524 and 0.4986. The f = 0.1 QBER sits 2.9σ above f/4, but not because anything is off: Eve happened to intercept 10.6% of the sifted positions, not 10%. Errors occur **only** where she measured in the wrong basis (0 elsewhere in every run), at a rate of 0.537, 0.509, 0.506 and 0.503 there. Counting guesses too, Eve is right on 75% of the sifted bits under the full attack, but that knowledge costs her 25% errors.

**The principle.** Information gain and disturbance come together. Eve cannot copy the qubit (no-cloning), and any measurement that learns something disturbs states from the other basis.

**Classical baseline.** Tapping a classical line and re-sending the bits is undetectable: the copy is perfect. That is the whole difference.

**What this does NOT show.** Smarter attacks (entangling probes, collective attacks) or attacks on real hardware (Lesson 28). Intercept-resend is the simplest and the noisiest attack; security proofs handle every attack allowed by quantum mechanics, but only for idealised devices.
