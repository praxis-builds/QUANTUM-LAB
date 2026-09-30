# Lesson 07: oracles and phase kickback

## The idea
An **oracle** is a black box that computes a function f for you. On a quantum computer it must be reversible, so it is built as a gate that keeps the input x and XORs the answer into an extra **output qubit**: |x⟩|y⟩ → |x⟩|y ⊕ f(x)⟩. With y = 0 it simply writes f(x), like a classical function call.

Now put the output qubit in |−⟩ = (|0⟩ − |1⟩)/√2 instead. XOR-ing 1 into |−⟩ gives −|−⟩: the output qubit does not change, only a minus sign appears. That sign attaches to the input's |x⟩ amplitude, so the state becomes (−1)^f(x)|x⟩|−⟩. This is **phase kickback**: the function's answer is written into a phase of the input. A phase is invisible (Lesson 03) until interference reveals it, and every algorithm in lessons 08–10 does exactly that.

## Predict first
1. With the output qubit in |0⟩, what does it hold after the oracle for f = NOT and input x = 0?
2. With the output qubit in |−⟩ and the input in |+⟩, does the output qubit change? What happens to the input's two amplitudes for f = identity?
3. After adding H on the input, what do you measure for each of the four one-bit functions? How many oracle calls did that take, and how many would a classical program need to tell whether f(0) = f(1)?

## How to run

    .venv/bin/python lessons/07_oracles_kickback.py

It prints four labelled steps (no plot). The input is qubit 0 and the output qubit is qubit 1.

## What you should see, and why
Answers are below.

## Spoiler
1. y = 1. NOT gives f(0) = 1, and 0 ⊕ 1 = 1. Step 1 lists all four functions; each output qubit holds f(x), as a classical call would.
2. The output qubit stays |−⟩: its Bloch vector is (−1, 0, 0) for all four functions. The input's signs become (+1, −1) for identity, (−1, +1) for NOT, (+1, +1) for constant 0 and (−1, −1) for constant 1. The last one is a global sign, so it is physically the same state as constant 0.
3. Constant functions give "0" in 1000 of 1000 shots; balanced functions (identity, NOT) give "1" in 1000 of 1000. That took **one** oracle call. This is Deutsch's algorithm, the n = 1 case of Lesson 08.

**Classical baseline.** A classical program must evaluate f(0) and f(1): 2 calls. One call reveals one value and says nothing about the other.

**What this does NOT show.** The quantum circuit learned one bit (equal or not), not the function itself: it cannot tell identity from NOT. The oracle was handed to us for free; building it for a real function costs gates we did not count. Two calls against one is not a speed-up anyone could use.
