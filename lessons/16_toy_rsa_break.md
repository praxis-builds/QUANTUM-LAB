# Lesson 16: finale, break a toy RSA key

## The idea
**RSA**, the public-key system behind much of today's secure web traffic, works like this. Pick two secret primes p and q and publish N = p·q together with an exponent e. Anyone can encrypt a number m < N as c = mᵉ mod N. Only the owner can decrypt, as m = c^d mod N, because computing d needs φ = (p − 1)(q − 1), and φ needs the factors of N. RSA's security rests on one assumption: factoring a large N is infeasible.

Shor's algorithm factors N (Lessons 13–15). So an attacker who sees only the public key (N, e) can factor N, compute φ and d, and read every message. Here we do exactly that with N = 21, using Lesson 15's circuit on local Aer.

## Predict first
1. With N = 21 = 3 × 7 and e = 5, what is the private exponent d?
2. Encrypting "HIDE" letter by letter (A = 0, …, T = 19), do you expect every letter to change?
3. How many quantum runs does the attacker need for a = 2, and how long does a classical computer take to factor 21?

## How to run

    .venv/bin/python lessons/16_toy_rsa_break.py

It prints four labelled steps (no plot) in a few seconds. The attack uses Lesson 15's circuit (15 qubits).

## What you should see, and why
Answers are below.

## Spoiler
1. d = 5. φ = 2 × 6 = 12, and 5 × 5 = 25 = 2 × 12 + 1, so e = d. That is a quirk of tiny numbers, not of RSA: the valid exponents below 12 (5, 7, 11) are each their own inverse mod 12. Worse, e = 7 (like any e ≡ 1 mod lcm(2, 6) = 6) would encrypt nothing at all, since m⁷ ≡ m for every m.
2. No. "HIDE" = [7, 8, 3, 4] becomes [7, 8, 12, 16]: H and I encrypt to themselves. For e = 5, 9 of the 21 values are fixed points, (1 + gcd(e − 1, p − 1))·(1 + gcd(e − 1, q − 1)) = 3 × 3. Encrypting single letters with textbook RSA is also a simple substitution cipher: equal letters give equal ciphertexts. **Never use RSA like this.** Real RSA uses 2048-bit or larger N and randomised padding (e.g. OAEP), and then the fraction of fixed points is negligible. The round trip decrypt(encrypt(m)) = m holds for all 21 values.
3. One. The first seeded run gave m = 170, and 170/1024 has the continued-fraction approximation 1/6, so r = 6 and 2³ = 8 gives gcd(7, 21) = 7 and gcd(9, 21) = 3. Then φ = 12, d = 5, and the ciphertext decrypts to "HIDE". (A single run succeeds with probability 0.322, Lesson 15.) The full algorithm with a random a picked a = 6 on its second try, and gcd(6, 21) = 3 did the work without any quantum help: a real attacker would take that too. Trial division finds 3 after 2 divisions, instantly.

**Reality check: RSA-2048.** The scaling is what matters. For a 2048-bit N, no known classical method is practical, while Shor's cost grows polynomially with the number of bits. Two published estimates for a fault-tolerant machine:
- Craig Gidney and Martin Ekerå, "How to factor 2048 bit RSA integers in 8 hours using 20 million noisy qubits", *Quantum* 5, 433 (2021), [arXiv:1905.09749](https://arxiv.org/abs/1905.09749) (2019). About 20 million physical qubits and 8 hours. Assumptions: physical gate error rate 10⁻³, surface-code cycle time 1 µs, reaction time 10 µs.
- Craig Gidney, "How to factor 2048 bit RSA integers with less than a million noisy qubits", [arXiv:2505.15917](https://arxiv.org/abs/2505.15917) (May 2025). Under a million noisy qubits and under a week, under comparable hardware assumptions (see the paper for the exact list).

These are estimates from careful papers, not measurements: no machine of that size exists, and today's devices are far smaller and noisier. The estimates also keep falling (by about 20× between 2019 and 2025), which is why they are taken seriously.

**Why RSA is being replaced.** Encrypted traffic recorded today could be decrypted once such a machine exists ("harvest now, decrypt later"). So standards bodies are moving key exchange to **post-quantum** schemes built on problems Shor does not solve, such as NIST's ML-KEM (FIPS 203, 2024, derived from Kyber). That is program step 7. Grover's algorithm (step 5) threatens symmetric ciphers far less: it roughly halves their key strength, so AES-256 remains fine.

**What this does NOT show.** A quantum computer breaking real RSA. Our N has 5 bits, the circuit was compiled from known answers (Lessons 14–15), it ran on a classical simulator, and trial division beat it instantly.
