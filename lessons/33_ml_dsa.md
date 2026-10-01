# Lesson 33: ML-DSA signatures

## The idea
Key exchange (Lessons 31–32) keeps traffic secret. **Signatures** prove who sent something and that it was not changed: software updates, certificates, contracts, the TLS handshake itself. RSA and ECDSA signatures fall to Shor just as their key exchanges do (Lesson 30). Once forgery is possible, anything that still trusts an old key is exposed.

**ML-DSA** (FIPS 204, formerly Dilithium) is the lattice-based replacement: keygen, **sign** with the private key, **verify** with the public key. Any change to the message or the signature makes verification fail. **SLH-DSA** (FIPS 205, formerly SPHINCS+) is the conservative alternative. It rests only on hash functions, at the price of large signatures and slow signing.

## Predict first
1. Change "100 EUR" to "900 EUR" in a signed message. Does the signature still verify? What about one flipped bit in the signature?
2. How big is an ML-DSA-65 signature compared with ECDSA P-256 (about 71 bytes)?
3. Is ML-DSA slower than ECDSA?

## How to run

    .venv/bin/python lessons/33_ml_dsa.py

It prints three labelled steps in a few seconds (needs the `[pqc]` extra; otherwise it prints the reason and stops).

## What you should see, and why
Answers are below.

## Spoiler
1. **No and no.** For ML-DSA-44, -65 and -87, the original verifies (True), and the altered message, a flipped signature bit, and someone else's public key all fail (False). ECDSA and Ed25519 reject the altered message too.
2. **3,309 bytes**, with a 1,952-byte public key, against 71 and 65 bytes for ECDSA P-256 (DER signature, uncompressed point) and 64 and 32 for Ed25519. ML-DSA-44 is 2,420 / 1,312 and ML-DSA-87 is 4,627 / 2,592: the FIPS 204 sizes exactly. SLH-DSA-SHA2-128s has a tiny 32-byte public key but a **7,856-byte** signature (the "f" variant: 17,088). In certificate chains with several signatures and keys, these sizes add up.
3. Not much. Medians on this machine: ML-DSA-65 signs in about 126 µs and verifies in about 48 µs; ECDSA P-256 takes about 29 µs and 82 µs. ML-DSA verifies faster than ECDSA here. SLH-DSA-128s needs about 0.65 seconds to sign. Timings are indicative (liboqs built without OpenSSL, single runs on one machine).

**Sources.** NIST FIPS 204 (*Module-Lattice-Based Digital Signature Standard*) and FIPS 205 (*Stateless Hash-Based Digital Signature Standard*), both published on 13 August 2024 together with FIPS 203 (Lesson 30). The sizes above are measured from liboqs 0.16.0 and match the parameter tables of those standards.

**Classical baseline.** ECDSA and Ed25519 are small and fast, and they are broken by Shor. Moving to ML-DSA mostly costs bytes, not time.

**What this does NOT show.** Certificates and PKI migration (new certificate formats, hybrid or composite certificates), or which ML-DSA parameter set to choose for a given system. Those are deployment questions, and the scanner in `tools/pq_inventory` is about finding where they arise.
