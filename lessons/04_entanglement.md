# Lesson 04: entanglement, and the CZ that cancels

## The idea
Two qubits can be in a **product state** (each qubit has its own definite description, like two separate coins) or an **entangled** state (the pair has a description that cannot be split into one for each qubit). The **Bell state** (the simplest entangled pair, made with H then a CNOT gate) is the standard example.

Measure one qubit of either state on its own and you see 50/50. The difference shows only when you compare the two results: the product state's qubits agree half the time, like two independent coins; the Bell state's qubits agree every time.

Connection to this lab: our kernel feature map ends with a **CZ gate** (a gate that flips the sign of the |11> amplitude). It entangles each encoded sample. But it is the last gate and is identical for every sample. Kernel values are overlaps between two states, and applying the same reversible operation to both leaves their overlap unchanged. So the CZ cancels. See `docs/kernel-concentration.md`.

## Predict first
1. Product state: how often do the two qubits show the same value?
2. Bell state: what single-qubit statistics do you expect for qubit 0 alone? How often do the two agree?
3. If the feature map's last gate is removed, does the kernel value between two samples change?

## How to run

    .venv/bin/python lessons/04_entanglement.py

It prints four labelled steps (no plot).

## What you should see, and why
Answers are below.

## Spoiler
1. About half the time (0.505 in this run). Each qubit is independent.
2. Qubit 0 alone: about 50/50 (0.500), exactly like a product state. The two agree every time (1.000; the counts were only "00" and "11"). The **purity** of one qubit alone (1 means fully definite, 0.5 means maximally mixed) is 0.5 for the Bell state and 1.0 for the product state, which is the numerical mark of entanglement.
3. No. For the sample x = (0.689, −1.034) the qubit is entangled (purity 0.650 with the CZ, 1.000 without), yet the kernel value between two samples is 0.131215152848 both ways, with a difference of exactly 0. This is a real result for our kernel, not an approximation. It holds only for a single layer, where the CZ is last. If data-dependent gates come after a CZ (repeated layers), the cancellation no longer holds.

What to notice: entanglement is real (purity 0.65), but it does not by itself make this kernel more powerful. That is the lesson from the lab: a feature that looks quantum can be irrelevant to the quantity you actually compute.
