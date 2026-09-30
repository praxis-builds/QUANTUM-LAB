# Lesson 29: quantum randomness

## The idea
Measure H|0⟩ and quantum mechanics says the outcome is 0 or 1 with probability ½ each, with no hidden cause that could have predicted it. That is the promise of a **quantum random number generator (QRNG)**: bits that are unpredictable in principle, not just hard to predict.

This lab runs on a **simulator**, though. Aer computes the probabilities exactly and then draws outcomes with a pseudo-random generator started from a **seed**. Same seed, same bits, every time. That is useful for reproducible experiments and useless as a secret.

Can statistics tell the difference? Tests such as NIST's **monobit** test (roughly as many ones as zeros?) and **runs** test (does it switch between 0 and 1 as often as chance?) catch bad sources. And a **von Neumann extractor** turns a biased coin into a fair one: read pairs, output 0 for 01 and 1 for 10, and drop 00 and 11.

## Predict first
1. Run the H|0⟩ circuit twice with the same seed. Do you get the same bits?
2. Which of these pass the monobit and runs tests: Aer's H|0⟩ bits, a biased coin with P(1) = 0.8, the sequence 0101…, NumPy's seeded generator?
3. From 80,000 bits of the biased coin, how many fair bits does the von Neumann extractor produce?

## How to run

    .venv/bin/python lessons/29_quantum_randomness.py

It prints three labelled steps (no plot) in about a second.

## What you should see, and why
Answers are below.

## Spoiler
1. **Yes, identical,** all 20,000 of them. A different seed gives different bits (agreement 0.506, as chance predicts). In this simple circuit even seed + 1 gives unrelated bits (agreement 0.498). But add a mid-circuit measurement, which makes Aer simulate shot by shot, and seed + 1 reproduces seed's bits shifted by one shot, **100% of them**. That is the behaviour recorded in CLAUDE.md, and why this lab spaces its seeds. Either way the bits are **pseudo-random**: fully determined by the seed.
2. Aer's bits pass (monobit p = 0.44, runs p = 0.70), and so does NumPy's generator (0.61, 0.60). The biased coin fails both (p ≈ 0). The sequence 0101… passes monobit perfectly (p = 1.0, exactly half ones) and fails runs (p ≈ 0): it switches every time, far too regularly. **The lesson:** the tests reject some bad sources, but a deterministic program passes them. Passing statistical tests never proves unpredictability.
3. 12,703 bits (ones 0.5045, both tests pass). A pair gives an output when it is 01 or 10, with probability 2p(1 − p) = 0.32; measured 0.3176 per pair. On the correlated sequence 0101… the extractor outputs 10,000 zeros: it only removes bias from **independent** bits.

**What real QRNG hardware adds.** A physical entropy source (for example photons at a beam splitter or vacuum noise) instead of a seed. Continuous health tests. An estimate of the entropy the source really delivers, which is what NIST SP 800-90B (2018) is about for entropy sources in general. And an extractor sized to that estimate. The strongest form is **device-independent** randomness: S. Pironio et al., "Random numbers certified by Bell's theorem", *Nature* 464, 1021 (2010), certified randomness from a measured Bell-inequality violation without trusting the devices' internals, 42 new random bits at 99% confidence in their proof-of-concept. That is certification by physics, which no statistical test can give.

**A sober note.** The UK NCSC's "Quantum security technologies" (24 March 2020) states that "classical RNGs will continue to meet our needs for government and military applications for the foreseeable future". Well-designed classical entropy sources plus cryptographic generators are the standard answer. A QRNG is one possible entropy source, not a requirement. (Test definitions: NIST SP 800-22 Rev. 1a, 2010.)

**Classical baseline.** NumPy's PCG64 passes the same tests as the "quantum" bits, and on a simulator both are just as deterministic.

**What this does NOT show.** Real quantum randomness: nothing in this repository is a random number generator you should use for keys. For that, use your operating system's cryptographic generator.
