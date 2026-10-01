# Lesson 30: why RSA and elliptic-curve cryptography must go

## The idea
Lesson 16 broke a toy RSA key: from the public key alone, Shor's period finding gave the factors, then the private key, then the plaintext. Nothing in that pipeline depends on the number being small, only the size of the quantum computer. Elliptic-curve cryptography (ECDH, ECDSA) falls to a variant of the same algorithm. Lesson 25 showed why that computer does not exist yet: error correction needs many physical qubits per reliable logical one.

So why act now? **Harvest now, decrypt later.** An attacker can record encrypted traffic today and decrypt it once a large enough machine exists. Mosca's inequality makes the deadline concrete. If data must stay secret for **x** years, migrating takes **y** years, and a cryptographically relevant quantum computer arrives in **z** years, the data is at risk whenever **x + y > z**.

## Predict first
1. Which systems are already at risk if z = 15 years: session keys (x ≈ 0), customer records (x = 10), archives (x = 30)?
2. Does choosing elliptic curves instead of RSA buy time against Shor?
3. Which NIST standards replace RSA and ECC, and since when?

## How to run

    .venv/bin/python lessons/30_why_rsa_and_ecc_must_go.py

It prints four labelled steps (no plot) in a few seconds. Step 1 reruns Lesson 16's attack on Aer. The rest is arithmetic with cited estimates.

## What you should see, and why
Answers are below.

## Spoiler
1. With the lesson's assumed migration times: at z = 15, records with x = 10 and y = 5 are just safe (15 is not greater than 15), while archives (x = 30) and a firmware root key (x = 15, y = 8) are at risk at every z tried (10, 15, 20). Session keys are fine. Every x, y and z here is an **assumption** for illustration; z in particular is unknown, so the lesson shows three scenarios rather than a forecast. For signatures the logic differs slightly. Old signatures cannot be "decrypted", but once forgery is possible, anything that still trusts the key (firmware roots, certificates) is exposed, so x is how long the key must be trusted.
2. No. Shor's algorithm solves the elliptic-curve discrete logarithm too. Roetteler, Naehrig, Svore and Lauter (ASIACRYPT 2017) bound it at 9n + 2⌈log₂ n⌉ + 10 logical qubits for an n-bit curve: at most 2,330 for P-256, 3,484 for P-384 and 4,719 for P-521.
3. **FIPS 203 (ML-KEM)** for key establishment, **FIPS 204 (ML-DSA)** and **FIPS 205 (SLH-DSA)** for signatures, all published on 13 August 2024. NIST's draft transition plan, NIST IR 8547 (initial public draft, 12 November 2024), proposes deprecating 112-bit RSA and ECC after 2030 and disallowing quantum-vulnerable public-key algorithms after 2035.

**Sources (checked on 2026-09-30).**
- NIST, FIPS 203, *Module-Lattice-Based Key-Encapsulation Mechanism Standard*, 13 August 2024 ([csrc.nist.gov](https://csrc.nist.gov/pubs/fips/203/final)). FIPS 204 and 205 were released the same day as the first three post-quantum standards.
- M. Mosca, "Cybersecurity in an era with quantum computers: will we be ready?", *IEEE Security & Privacy* 16(5), 38–41 (2018).
- M. Roetteler, M. Naehrig, K. M. Svore, K. Lauter, "Quantum resource estimates for computing elliptic curve discrete logarithms", ASIACRYPT 2017, [ePrint 2017/598](https://eprint.iacr.org/2017/598).
- RSA-2048: Gidney 2025 and Gidney & Ekerå 2021 (Lesson 16).
- NIST IR 8547 ipd ([csrc.nist.gov](https://csrc.nist.gov/pubs/ir/8547/ipd)), 12 November 2024. **I could not read the PDF in this environment.** The 2030/2035 dates are taken from several consistent published summaries, and the draft may change.

**Classical baseline.** No known classical algorithm breaks RSA-2048 or P-256. The threat is entirely about a future quantum computer, which is why its arrival date z is the uncertain part of the inequality.

**What this does NOT show.** When such a computer will exist. Nothing here predicts z, and the lesson does not claim any machine can break real keys today.
