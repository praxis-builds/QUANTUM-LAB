# Lesson 25: thresholds and overhead

## The idea
A repetition code with **distance** d (d copies, majority vote) fails only when more than half the copies flip. If each flip is unlikely, needing many of them at once is very unlikely, so a bigger d gives a smaller **logical error**. But if flips are likely, a majority of flips is likely too, and a bigger d makes things worse.

The boundary is the **threshold**. Below it, adding physical qubits suppresses errors, and quickly. Above it, error correction is hopeless whatever you spend. Every practical quantum computer plan rests on one condition: get the physical error rate below the threshold of a real code. Then spend many physical qubits per **logical qubit** to push the logical error as low as the algorithm needs.

## Predict first
1. At p = 0.1, how do d = 3, 5 and 7 compare? At p = 0.6?
2. Where is the threshold for this toy?
3. Why do real devices need far more than 3 or 7 physical qubits per logical qubit?

## How to run

    .venv/bin/python lessons/25_threshold_reality_check.py

It prints three labelled steps and saves `lessons/out/25_threshold.png` (about 15 seconds). Each point uses 20,000 shots each of logical 0 and logical 1, on Aer's stabilizer method, and every run has its own seed (see "A note on seeds" below).

## What you should see, and why
Answers are below.

## Spoiler
1. At p = 0.1: 0.0274, 0.0082 and 0.0022 for d = 3, 5 and 7 (formula 0.0280, 0.0086, 0.0027), so each step d → d + 2 divides the error by about 3. At p = 0.01 each step divides it by about 30. At p = 0.6 the order flips: 0.649, 0.684 and 0.710, all worse than an unprotected 0.60. Every measured point sits within normal sampling spread of the exact binomial formula.
2. p = 1/2, where the majority is as likely wrong as right. That is the threshold only for this toy, where encoding, parity checks and measurement are all perfect.
3. Three reasons the toy hides:
   - **The checks themselves fail.** In hardware the CNOTs and ancilla measurements that extract the syndrome make errors too, and the syndrome must be measured over and over. Codes that tolerate this (**fault-tolerant** syndrome extraction) have thresholds around 1% for the surface code instead of 50%.
   - **Two error types.** A repetition code handles one error type (Lesson 23); the **surface code** handles X and Z on a 2D grid of nearest neighbours.
   - **Tiny margins.** Real error rates sit only a few times below threshold, so the suppression per step of d is modest (about 2 for Google's device, below) and large distances are needed.

**Published results (sources checked on 2026-09-30).**
- Google Quantum AI, "Quantum error correction below the surface code threshold", *Nature* 638, 920–926 (2025), [arXiv:2408.13687](https://arxiv.org/abs/2408.13687). A 101-qubit distance-7 surface code with 0.143% ± 0.003% logical error per cycle. Each step d → d + 2 (3 → 5 → 7) suppressed the logical error by Λ = 2.14 ± 0.02, and the logical qubit outlived its best physical qubit by 2.4 ± 0.3×. Note what this is: **one** logical qubit storing data, at an error per cycle far above what Shor needs.
- A. G. Fowler, M. Mariantoni, J. M. Martinis, A. N. Cleland, "Surface codes: Towards practical large-scale quantum computation", *Phys. Rev. A* 86, 032324 (2012), [arXiv:1208.0928](https://arxiv.org/abs/1208.0928): the standard introduction, including how many physical qubits a logical qubit needs. The surface-code threshold is commonly quoted as about 1%. **I did not verify the exact figure or the overhead estimates from the paper body here** (its abstract gives no numbers), so none are quoted.
- Back to Lesson 16. Gidney's 2025 RSA-2048 estimate ([arXiv:2505.15917](https://arxiv.org/abs/2505.15917)) assumes a physical gate error rate of **0.1%**, a 1 µs surface-code cycle and a 10 µs reaction time (from its abstract). That is roughly ten times below the ~1% threshold, and it still needs under a million noisy qubits. Most of those qubits are error-correction overhead, building a modest number of very reliable logical qubits. (The abstract gives no logical-qubit count, so none is quoted.)

**A note on seeds (measured in this lab).** With noise or mid-circuit measurement, Aer 0.17.2 seeds shot i of a run as `seed_simulator + i`: shot i with seed s is exactly shot i − 1 with seed s + 1. Two runs with nearby seeds therefore reuse almost all their random numbers. An earlier version of Lessons 21–25 used seeds 1 apart for runs it then pooled, and 40 "different" seeds gave the same answer to within 0.00002. Every run now gets its own seed, 10⁷ apart (`_qec.run_seed`), and the published numbers come from those runs.

**Classical baseline.** Classical memory uses exactly this repetition idea and similar codes, far below threshold, which is why ordinary bits almost never flip in practice. The quantum difficulty is doing it for two error types, without looking at the data, with noisy checks.

**What this does NOT show.** A fault-tolerant code, repeated syndrome rounds, decoding in time, or logical gates. The threshold of 1/2 here is a property of perfect checks, not of hardware.
