# Lesson 01: one qubit, amplitudes and shots

## The idea
A qubit's state is two numbers called **amplitudes** (a number that can be positive, negative or complex; one for outcome 0, one for outcome 1). You never see amplitudes directly. When you **measure** (read the qubit out as a plain 0 or 1), you get a single bit. The chance of each outcome is the amplitude squared. This is the **Born rule** (probability = amplitude², after taking the absolute value). Here the amplitudes are 0.837 and 0.548, so the chances are 0.70 and 0.30.

One measurement gives one bit, so it tells you almost nothing. To estimate the probabilities you prepare the same state again and again and count. Each repetition is a **shot**. That is why every quantum result in this repo states its shot count: the answer is an estimate, and it gets better only slowly as you add shots.

## Predict first
1. If P(1) is 0.30, what will a single shot show? Will 10 shots show exactly 3 ones?
2. How many shots do you need to be within about 0.01 of the true value? Guess: 100, 1,000 or 10,000?
3. If you want the error to be 10 times smaller, how many times more shots do you need?

## How to run
From the repo root:

    .venv/bin/python lessons/01_one_qubit.py

It prints three labelled steps and saves `lessons/out/01_one_qubit_convergence.png`.

## What you should see, and why
- Step 1: amplitudes 0.837 and 0.548, probabilities 0.70 and 0.30, adding to 1.
- Step 2: the estimate wanders at few shots and settles near 0.30 at many.
- Step 3: the typical error shrinks like 0.4 divided by the square root of the shots.

Answers are below. Try to answer the questions first.

## Spoiler
1. A single shot shows just one bit, 0 or 1 (in this run it showed 1, even though 1 is the less likely outcome). Ten shots gave 5 ones here (estimate 0.50), not 3. With few shots the count is random.
2. About 1,000 shots: the typical error was 0.011 at 1,000 shots and 0.032 at 100.
3. 100 times more. The error falls with the square root of the shots, so 10 times smaller costs 100 times the shots (0.032 at 100 shots vs 0.0036 at 10,000). This is exactly why the kernel experiments in this repo need so many shots to resolve small differences.

The plot's dashed line is the reference curve 0.4/√shots. The measured errors follow it closely, sitting a little below it.
