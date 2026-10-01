# Lesson 31: ML-KEM hands-on

## The idea
**ML-KEM** (FIPS 203, formerly Kyber) is a **key-encapsulation mechanism**. Alice publishes a public key. Bob uses it to **encapsulate**: he produces a random shared secret plus a **ciphertext** that only Alice can open. Alice **decapsulates** the ciphertext and gets the same secret. Both then use that secret as a symmetric key (for example for AES-256).

Its security rests on a lattice problem (Module Learning With Errors) for which no efficient quantum algorithm is known, unlike factoring (Shor). The trade-off against RSA and elliptic curves is not speed but **size**: keys and ciphertexts are around a kilobyte.

ML-KEM also never says "this ciphertext was tampered with". It returns an unrelated secret instead (**implicit rejection**), so an attacker learns nothing from failures.

## Predict first
1. How large are ML-KEM-768's public key and ciphertext, compared with X25519 (32 bytes each way)?
2. Is ML-KEM slower than RSA-2048?
3. What does decapsulating a ciphertext with one flipped bit return?

## How to run

    pip install -e '.[pqc]'      # plus the liboqs C library: docs/DECISIONS.md, D1
    .venv/bin/python lessons/31_ml_kem.py

It prints three labelled steps in about a second. Without the extra it prints the reason and stops. A small C program calling liboqs directly is in [`lessons/c/`](c/README.md).

## What you should see, and why
Answers are below.

## Spoiler
1. ML-KEM-768: public key **1,184** bytes and ciphertext **1,088** bytes, against 32 and 32 for X25519. ML-KEM-512 uses 800 and 768, ML-KEM-1024 1,568 and 1,568. The shared secret is always 32 bytes. These are exactly the FIPS 203 sizes. RSA-2048 sits in between: a 294-byte public key (SubjectPublicKeyInfo DER) and a 256-byte ciphertext.
2. No: much faster. On this machine, medians of 200 runs for ML-KEM-768 were 21 µs for keygen, 16 µs to encapsulate and 18 µs to decapsulate. RSA-2048 took 41 ms for keygen (median of 9), 24 µs to encrypt and 568 µs to decrypt. X25519 took about 33 µs per operation. Timings vary by machine and library build (liboqs here was built without OpenSSL, see D1) and are only indicative.
3. A different 32-byte secret, with no error raised: implicit rejection. The tampering shows up later, when the two sides' keys don't decrypt each other's traffic.

**Classical baseline.** RSA-OAEP key transport and X25519 key agreement do the same job with smaller messages, but Shor breaks both (Lessons 16 and 30).

**What this does NOT show.** Side-channel resistance, correct use inside a protocol, or certification: this is a teaching run through liboqs, which its authors describe as a research and prototyping library. Production systems should use vetted, maintained implementations in their TLS stack or crypto library.
