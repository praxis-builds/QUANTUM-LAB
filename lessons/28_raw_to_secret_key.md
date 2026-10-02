# Lesson 28: from raw key to secret key

## The idea
After sifting, Alice's and Bob's keys still differ in a few places (the QBER), and Eve may know part of them. Three classical steps fix that:

1. **Estimate the error rate.** Reveal a random sample, count disagreements, discard the sample.
2. **Error correction.** Compare parities of blocks over the public channel and fix Bob's bits until the keys match. Every parity announced is one bit Eve also learns.
3. **Privacy amplification.** Both apply the same random **Toeplitz hash** (a public, random, linear map to fewer bits). Eve's partial knowledge of the long key becomes almost no knowledge of the short one.

Shor and Preskill (2000) proved that, for BB84 with bit and phase error rates Q, the secret fraction can approach 1 − 2h(Q). Here h is the binary entropy: one h(Q) for error correction, one for Eve's possible knowledge. It reaches zero at **Q ≈ 11%**. Above that, abort.

## Predict first
1. With Q = 3%, roughly what fraction of the sifted key can become secret?
2. What happens at Q = 12%? With Eve intercepting every qubit (Q ≈ 25%)?
3. Why must the key length use a *worst-case* Q rather than the measured one?

## How to run

    .venv/bin/python lessons/28_raw_to_secret_key.py

It prints two labelled steps and saves `lessons/out/28_key_rate.png` (a few seconds). Seven scenarios of 20,000 qubits each (channel noise 1–12%, and a full intercept-resend attack). Each reveals a 1,000-bit sample, runs a toy parity-based error correction, checks with a 32-bit hash, and amplifies privacy.

## What you should see, and why
Answers are below.

## Spoiler
1. The limit is 1 − 2h(0.032) = 0.59. The toy gets 0.45: error correction revealed 2,275 bits against a Shannon minimum of 1,824 (no Cascade-style backtracking), and the length uses a worst-case Q (question 3) plus 100 spare bits. At 1% noise the toy keeps 0.76 (limit 0.87); at 5%, 0.30 (limit 0.52). In every run Alice's and Bob's final keys are identical, with 0 errors left.
2. **Abort.** Measured 11.8% (bound 14.9%) is past 11%, and Eve's attack shows up as 28.1% (bound 32.4%). The 8% and 10% channels abort too: their measured rates (8.9%, 9.7%) are below 11%, but their bounds (11.6%, 12.5%) are not.
3. A 1,000-bit sample only estimates Q. At 5% noise it read 4.0% while the rest of the key was really at 4.7%. Using the estimate would under-count Eve's possible knowledge. So the lesson uses Q + 3 standard deviations. A real system does a proper **finite-key analysis**; the 3σ bound and the 100 spare bits are stand-ins, and the page says so.

**Sources (checked on 2026-09-30).** P. W. Shor and J. Preskill, "Simple proof of security of the BB84 quantum key distribution protocol", *Phys. Rev. Lett.* 85, 441 (2000), [arXiv:quant-ph/0003004](https://arxiv.org/abs/quant-ph/0003004): the protocol is secure while "the measured bit and phase error rates are less than 11%, the point at which the Shannon rate 1−2H(δ) hits 0" (from the paper's closing section; compared word for word with arXiv v2 on 2026-10-01).

## Honesty: what QKD does not give you
- **It needs an authenticated classical channel.** Sifting, sampling, error correction and hashing all run over a public channel. If Eve can impersonate Bob there, she runs BB84 with each side separately and is never caught. Authentication needs a pre-shared secret key (for example with universal-hash message authentication) or digital signatures. So QKD *grows* a shared key; it doesn't create one from nothing. The UK NCSC notes that "QKD protocols do not provide authentication" and so "are vulnerable to physical man-in-the-middle attacks".
- **Real devices leak.** L. Lydersen et al., "Hacking commercial quantum cryptography systems by tailored bright illumination", *Nature Photonics* 4, 686 (2010), showed that the detectors of two commercial systems could be fully remote-controlled with bright light, so Eve could obtain the full key without being detected. Security proofs cover idealised devices; implementations must close such side channels one by one.
- **Photons come in bunches.** Practical sources send weak laser pulses that sometimes contain two or more photons. Eve can split off one and wait: the **photon-number-splitting** attack (G. Brassard, N. Lütkenhaus, T. Mor, B. C. Sanders, "Limitations on practical quantum cryptography", *Phys. Rev. Lett.* 85, 1330 (2000)). **Decoy-state** protocols were later developed against it. I have not checked their performance figures, so none are given here.
- **Security agencies prefer post-quantum cryptography.** UK NCSC, "Quantum security technologies" (white paper, 24 March 2020): the NCSC "does not endorse the use of QKD for any government or military applications". US NSA, "Quantum Key Distribution (QKD) and Quantum Cryptography (QC)" (26 October 2020): NSA "does not recommend the usage of quantum key distribution and quantum cryptography for securing the transmission of data in National Security Systems (NSS) unless the limitations below are overcome", and it considers post-quantum cryptography more cost-effective and easier to maintain. (The NCSC wording here and above was compared word for word with the paper at ncsc.gov.uk/paper/quantum-security-technologies on 2026-10-01. nsa.gov refuses automated access, so the NSA sentence was compared word for word with the Internet Archive's copy of the nsa.gov page from 28 December 2023; its conclusion reads "a more cost effective and easily maintained solution than quantum key distribution". The 26 October 2020 date comes from secondary sources and is not verified.)

**Conclusion.** QKD complements post-quantum cryptography; it doesn't replace it. It offers security based on physics for keys between two specially equipped endpoints, but it still needs authentication (so a classical or post-quantum mechanism), special hardware and careful engineering. For almost everything else, the practical defence against Shor is post-quantum cryptography.

**Classical baseline.** With a classical channel there is no disturbance to measure: Eve can copy everything, so no amount of classical post-processing creates secrecy from nothing.

**What this does NOT show.** A real finite-key security proof, Cascade's full algorithm, loss, or any hardware. The key rates here are per sifted bit; real systems also lose most photons in the fibre.
