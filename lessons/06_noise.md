# Lesson 06: noise kills interference

## The idea
Real qubits are disturbed by their surroundings. **Depolarizing noise** (the repo's `depolarizing_channel`) is the simplest model: with probability p a qubit is replaced by a completely random one, otherwise it is left alone. Here it is applied to both qubits after every gate layer of Lesson 05's Grover circuit (9 layers).

Grover works because amplitudes with the right signs cancel and add (interference). That needs a definite relationship between the amplitudes, which lives in the off-diagonal entries of the **density matrix** (a table describing the qubits' state that also covers mixed, partly random states). Random replacement shrinks those entries, so cancellation becomes incomplete. The 100% success falls toward 25%, which is what one random guess achieves.

## Predict first
1. With 1% noise per layer per qubit, do you expect success near 99%, 90% or 60%?
2. At what noise level does Grover become no better than one random classical guess (25%)? Guess: 5%, 20% or 100%?
3. Which one matters more for the final answer: the probabilities right after the oracle (still 25% each) or the interference left at that point?

## How to run

    .venv/bin/python lessons/06_noise.py

It prints two labelled steps and saves `lessons/out/06_noise_success.png`.

## What you should see, and why
Step 1 sweeps the noise strength from 0 to 1. Step 2 checks the density-matrix calculation against a local Aer run that uses the identical noise operators. Answers are below.

## Spoiler
1. About 90% (0.897). One percent of noise per layer sounds tiny, but there are 9 layers on each of 2 qubits, so the errors accumulate: 0.808 at 2%, 0.606 at 5%, 0.415 at 10%.
2. Around 20 to 30%. At p = 0.20 the success is 0.282 and at p = 0.30 it is 0.255; from p = 0.5 upward it is 0.250 to three decimals. Mind the scale: p is per layer per qubit, so this is a heavy dose. A single-guess baseline is the fair comparison here, since the noisy circuit still makes only one oracle call.
3. The interference left. Right after the oracle, the probabilities are 0.25 each with or without noise, so measuring would show nothing. What differs is the size of the off-diagonal entries. Relative to the ideal, that "interference left" was 0.935 at 1% noise, 0.498 at 10%, and about 0 at 50%. When it is gone, the diffusion step has nothing to amplify.

Step 2 gives 0.414616950 from both routes at p = 0.1, a difference of about 5e-17, so the plain matrix code and Aer agree.

What to notice: noise does not "flip the answer". It erases the phase relationships that interference needs. This is the central obstacle for real quantum devices, and it is why the repo studies how shots and noise limit what a kernel can distinguish.
