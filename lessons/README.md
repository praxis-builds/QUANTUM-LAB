# Lessons

Short lessons, one idea each, using this repo's own code and local Aer only (no cloud, no hardware). Do them in order; each builds on the last. Lessons 01–06 are program step 1 (foundations); 07–10 are step 2 (first quantum algorithms); 11–12 are step 3 (QFT and phase estimation); 13–16 are step 4 (Shor and a toy RSA break); 17–20 are step 5 (Grover in depth); 21–25 are step 6 (noise and error correction); 26–29 are step 7 (quantum security); 30–33 are step 8 (post-quantum cryptography, which needs the optional `[pqc]` extra for 31–33). Run every script from the repo root with `.venv/bin/python`.

Each lesson has a `.py` script and a `.md` page: the idea in plain words, three "predict first" questions, how to run, and what you should see. **Answer the questions before you run the script.** The answers sit at the bottom of the `.md` page under "Spoiler". Plots go to `lessons/out/` (git-ignored).

| # | Lesson | One-line idea | Uses |
|---|---|---|---|
| 01 | [One qubit](01_one_qubit.md) | Amplitudes squared are probabilities, and shots only estimate them | `state_vectors.py`, Aer |
| 02 | [Interference](02_interference.md) | H, H returns to 0 because paths cancel; a classical coin cannot do this | `state_vectors.py`, Aer |
| 03 | [Phase](03_phase.md) | A hidden sign changes nothing you can measure, until interference reveals it | `state_vectors.py`, Aer |
| 04 | [Entanglement](04_entanglement.md) | Perfect correlation with 50/50 marginals; why the kernel's last CZ cancels | Aer, `kernel_spectrum.py` |
| 05 | [Grover search](05_grover.md) | One oracle call finds the marked item of four; interference does useful work | Aer |
| 06 | [Noise](06_noise.md) | Depolarizing noise erases the phase relations, and success falls toward 25% | `density_matrices.py`, Aer |
| 07 | [Oracles and phase kickback](07_oracles_kickback.md) | An oracle XORs f(x) into a qubit; with that qubit in \|−⟩ the answer becomes a phase | `_oracles.py`, Aer |
| 08 | [Deutsch–Jozsa](08_deutsch_jozsa.md) | One query tells constant from balanced for certain; classical needs up to 2^(n−1)+1 | `_oracles.py`, Aer |
| 09 | [Bernstein–Vazirani](09_bernstein_vazirani.md) | One query reads out a hidden n-bit string s; classical needs n | `_oracles.py`, Aer |
| 10 | [Simon](10_simon.md) | Runs give equations y·s = 0; GF(2) algebra finds the hidden period, the idea behind Shor | `_oracles.py`, Aer |
| 11 | [Quantum Fourier transform](11_qft.md) | A repeating pattern in amplitudes becomes sharp peaks; the QFT is the DFT with a + sign and Qiskit's bit order | `_qft.py`, Aer |
| 12 | [Phase estimation](12_phase_estimation.md) | Kickback plus inverse QFT reads a gate's eigenphase; more qubits sharpen it, the engine of Shor | `_qft.py`, Aer |
| 13 | [Period finding, classically](13_period_finding.md) | The period r of aˣ mod N gives the factors by gcd; Shor's quantum part only finds r | `_shor.py` |
| 14 | [Shor for N = 15](14_shor_15.md) | Phase estimation of "multiply by a mod 15" plus continued fractions finds 3 × 5; "compiled Shor", stated | `_shor.py`, `_qft.py`, Aer |
| 15 | [Shor for N = 21](15_shor_21.md) | Generic permutation unitaries, spread peaks, which a work, and how the qubit count grows | `_shor.py`, Aer |
| 16 | [Break a toy RSA key](16_toy_rsa_break.md) | From the public key (21, 5) alone: factor, compute d, decrypt; RSA-2048 estimates and why RSA is being replaced | `_shor.py`, Aer |
| 17 | [Grover on n qubits](17_grover_n_qubits.md) | About (π/4)√(N/M) rotations to the answer; too many overshoot; unknown M needs BBHT or quantum counting | `_grover_n.py`, Aer |
| 18 | [Toy key search](18_toy_key_search.md) | Grover runs a 4-bit cipher inside a reversible oracle; false positives, and a second known pair | `_grover_n.py`, Aer |
| 19 | [Toy hash preimages](19_toy_hash_preimage.md) | Measured slope of log₂(calls): 0.50 for Grover against 0.99 classical, the square-root speed-up | `_grover_n.py`, Aer |
| 20 | [Reality check: AES and SHA](20_grover_reality_check.md) | 2^64 / 2^128 sequential full-circuit calls, √p parallelism, NIST categories; Grover weakens, Shor breaks | arithmetic only |
| 21 | [Why errors matter](21_why_errors_matter.md) | Per-gate noise on Shor-15 and Grover: bigger circuits break sooner, but which gates are sensitive matters too | `_qec.py`, Aer |
| 22 | [Bit-flip code](22_bit_flip_code.md) | Three qubits, a two-ancilla syndrome, one flip fixed; logical error 3p² − 2p³ | `_qec.py`, Aer stabilizer |
| 23 | [Phase-flip code](23_phase_flip_code.md) | The same code in the H basis fixes Z; each code is blind to the other's error | `_qec.py`, Aer stabilizer |
| 24 | [Shor's 9-qubit code](24_shor_nine_qubit_code.md) | Nesting both codes fixes any single-qubit error: all 27 Paulis, and non-stabilizer inputs | `_qec.py`, Aer |
| 25 | [Thresholds and overhead](25_threshold_reality_check.md) | Bigger codes help below threshold and hurt above it; why RSA-2048 needs about a million physical qubits | `_qec.py`, Aer stabilizer |
| 26 | [BB84 key distribution](26_bb84.md) | Random bases, public sifting keeps about half; QBER is 0 on a perfect channel and p with noise p | `_qkd.py`, Aer |
| 27 | [Intercept-resend attack](27_intercept_resend.md) | Eve causes 25% errors; k sample bits miss her with probability (3/4)^k | `_qkd.py`, Aer |
| 28 | [Raw key to secret key](28_raw_to_secret_key.md) | Parity error correction plus Toeplitz privacy amplification; abort above 11%; what QKD does not give you | `_qkd.py`, Aer |
| 29 | [Quantum randomness](29_quantum_randomness.md) | Same seed, same "quantum" bits; statistical tests and a von Neumann extractor; why passing tests proves nothing | `_qkd.py`, Aer |
| 30 | [Why RSA and ECC must go](30_why_rsa_and_ecc_must_go.md) | Shor recovers a toy RSA key; ECC needs only a few thousand logical qubits; harvest now, decrypt later (Mosca); FIPS 203/204/205 | `_shor.py`, Aer |
| 31 | [ML-KEM hands-on](31_ml_kem.md) | Keygen, encapsulate, decapsulate; 1,184-byte keys and 1,088-byte ciphertexts vs RSA and X25519; implicit rejection | `_pqc.py`, liboqs |
| 32 | [Hybrid key exchange](32_hybrid_key_exchange.md) | X25519 + ML-KEM-768 through HKDF: an attacker must break both (educational, not production) | `_pqc.py`, liboqs |
| 33 | [ML-DSA signatures](33_ml_dsa.md) | Sign and verify; tampering fails; 3,309-byte signatures vs 71 for ECDSA; SLH-DSA for comparison | `_pqc.py`, liboqs |

Run one lesson: `.venv/bin/python lessons/02_interference.py`. Run all their checks: `.venv/bin/python -m pytest tests/test_lesson_*.py tests/test_oracles.py`.

## Mapping to Coursera "Complete Quantum Computing Course for Beginners" (Course 1)

**Unverified.** I could not retrieve the module-by-module syllabus of Course 1. The public course page describes the specialization as covering qubits, superposition, quantum gates, entanglement and building circuits in Qiskit. This table matches the lessons to those concepts only. Check the real module list on the [course page](https://www.coursera.org/specializations/packt-the-complete-quantum-computing-course-for-beginners) and adjust.

| Concept named in the course description | Lessons |
|---|---|
| Qubits, superposition, measurement | 01, 02 |
| Quantum gates (H, X, Z, phase, CZ, CNOT) | 02, 03, 05 |
| Interference and phase | 02, 03, 05 |
| Entanglement (Bell state) | 04 |
| Building and running circuits in Qiskit | all (each uses Qiskit circuits on local Aer) |
| A first quantum algorithm (Grover) | 05 |
| Noise (usually a later topic, so this is extra) | 06 |

Lessons 07–10 (oracle algorithms) go beyond that description. Lessons 11–12 add the QFT and phase estimation. Lessons 13–16 add Shor and a toy RSA break. Lessons 17–20 cover Grover in depth, 21–25 error-correction basics, 26–29 BB84 and randomness. Lessons 30–33 cover post-quantum cryptography, with a C companion in [`c/`](c/README.md). Not covered: fault-tolerant codes, post-quantum crypto, real hardware, and programming-language basics.

## Honest limits

These are simulations on a classical computer. The Grover lesson compares oracle calls on 4 items; lessons 07–10 compare oracle calls on at most 4 input bits, with the oracle given for free. Lessons 11–12 run on at most 6 qubits and compare against numpy's FFT and eigenvalue routines. Lessons 13–16 factor 15 and 21 with compiled multipliers built from known answers, and trial division beats them instantly. Lessons 17–20 search at most 1,024 items; their resource figures for AES and SHA come from cited papers. Lessons 21–25 use perfect syndrome extraction, so their thresholds are far above real ones. Lessons 26–29 simulate photons as ideal qubits and produce pseudo-random bits: none of it is usable cryptography. Each states its classical baseline and what it does not show. Nothing here claims a quantum speed-up. The repo's rules on this (see `CLAUDE.md`) apply to lessons too.
