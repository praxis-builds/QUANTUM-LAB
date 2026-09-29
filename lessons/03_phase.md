# Lesson 03: phase, the invisible sign

## The idea
Amplitudes can be negative. The two states |+> (amplitudes +0.707, +0.707) and |−> (amplitudes +0.707, −0.707) differ only by a minus sign. That sign is the **phase** (the "direction" of an amplitude, here just plus or minus; in general an angle). Since probabilities are amplitudes squared, the sign disappears: measured directly, both states give 50/50, and no measurement of that kind can tell them apart.

The sign is still real. Interference (Lesson 02) is what turns it into something visible: apply H before measuring and |+> becomes a certain 0 while |−> becomes a certain 1. For a general angle φ, the outcome probability follows cos²(φ/2). So "invisible" phases carry information, and quantum algorithms work by arranging phases so interference reveals the answer.

## Predict first
1. Measure |+> and |−> directly, with no other gates. What do you see for each?
2. Now apply H to each before measuring. What do you expect?
3. If the hidden phase is a quarter turn (φ = π/2), what probability of 0 do you expect after the final H?

## How to run

    .venv/bin/python lessons/03_phase.py

It prints four labelled steps and saves `lessons/out/03_phase_sweep.png`.

## What you should see, and why
Answers are below.

## Spoiler
1. Both give about 50/50, and the two results are identical here (991 zeros and 1,009 ones each, because the same seed and the same probabilities were used).
2. |+> then H gives 0 every time (2,000 of 2,000); |−> then H gives 1 every time. The same H that gave "always 0" in Lesson 02 now gives "always 1" when the sign of the second amplitude is flipped: the two paths to outcome 0 now cancel instead of the two paths to outcome 1.
3. 0.50. The formula cos²(π/4) is exactly 0.5, and the measured value was 0.495. The sweep in step 4 traces the whole curve: 1.0 at φ = 0, 0.5 at a quarter turn, 0 at a half turn (that half turn is the |−> case), then back up.

What to notice: nothing you can measure right now distinguishes |+> from |−>, but a later gate can. This is why in this repo's kernel experiments the choice of gates that rotate the qubits (RZ, RY) matters even though RZ alone never changes a measured 0 or 1 probability.
