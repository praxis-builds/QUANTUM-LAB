# Lesson 20: reality check, AES and SHA

## The idea
Lesson 19 measured Grover's square root: a search over 2ⁿ possibilities needs about (π/4)·2^(n/2) oracle calls, where a classical search needs about 2^(n−1). Applied to real cryptography, that is 2^64 calls for an AES-128 key and 2^128 for an AES-256 key or a SHA-256 preimage.

Three facts make those numbers far worse than they look. Each call is a **complete reversible AES or SHA-256 circuit**, run twice (compute and uncompute) on a fault-tolerant machine. The calls must happen **one after another**, since Grover's rotation cannot be split into independent pieces. And **parallel machines help only by √p**. So Grover *weakens* symmetric cryptography by roughly halving the key length in bits. Shor (Lesson 16) *breaks* RSA outright.

This lesson is arithmetic plus published estimates; no circuit is simulated.

## Predict first
1. How many sequential Grover calls does an AES-128 key search need? An AES-256 key search?
2. To finish AES-128 within 2^40 sequential calls, how many quantum machines working in parallel do you need, and what happens to the total work?
3. Which of AES-128, AES-256 and SHA-256 would you still trust against a large quantum computer?

## How to run

    .venv/bin/python lessons/20_grover_reality_check.py

It prints four labelled steps (no plot, no simulation) instantly.

## What you should see, and why
Answers are below.

## Spoiler
1. About 2^63.65 for AES-128 and 2^127.65 for AES-256 (and for a SHA-256 preimage), against 2^127 and 2^255 classical trials on average. Every call is a full AES circuit, not a single step.
2. 2^47.3 machines. Each machine searches 2^128/p keys in (π/4)·√(2^128/p) steps, so p machines cut the time by only √p, and the **total** work grows to 2^87.3 = (π/4)·√(2^128·p). A classical search splits perfectly: p machines, p times faster, the same total work.
3. **AES-256 and SHA-256 are safe**: 2^128 sequential full-circuit calls is beyond any plausible machine. **AES-128 is the debated case.** 2^64 sequential AES circuits sounds reachable on paper, but the per-call cost and the poor parallelism push it far out. NIST's own PQC FAQ, answering "should we double the key length for AES now?", says Grover "will provide little or no advantage in attacking AES, and AES 128 will remain secure for decades to come", and that "current applications can continue to use AES with key sizes 128, 192, or 256 bits". Some organisations still require AES-256 for long-lived secrets, for extra margin.

**Published estimates (sources checked on 2026-09-30).**
- NIST, *Post-Quantum Cryptography: Security (Evaluation Criteria)*, part of the 2016 call for proposals, [csrc.nist.gov](https://csrc.nist.gov/projects/post-quantum-cryptography/post-quantum-cryptography-standardization/evaluation-criteria/security-(evaluation-criteria)). Security categories 1, 3 and 5 = as hard as key search on AES-128, -192 and -256; categories 2 and 4 = collision search on SHA-256 and SHA-384. It caps quantum circuit depth at a MAXDEPTH, with "plausible values" from 2^40 logical gates (about a year of serial gates on envisioned hardware), through 2^64 (about a decade of serial classical gates), to no more than 2^96. Its estimate for AES-128 key search is 2^170/MAXDEPTH quantum gates, i.e. 2^130, 2^106 or 2^74 at those depths (Step 3), against 2^143 classical gates.
- M. Grassl, B. Langenberg, M. Roetteler, R. Steinwandt, "Applying Grover's algorithm to AES: quantum resource estimates", PQCrypto 2016, [arXiv:1512.04965](https://arxiv.org/abs/1512.04965): roughly 3,000 to 7,000 logical qubits for AES-128/192/256 key search.
- S. Jaques, M. Naehrig, M. Roetteler, F. Virdia, "Implementing Grover oracles for quantum key search on AES and LowMC", Eurocrypt 2020, [ePrint 2019/1146](https://eprint.iacr.org/2019/1146): depth-limited costs, with Q# code for the full AES oracles.
- M. Amy, O. Di Matteo, V. Gheorghiu, M. Mosca, A. Parent, J. Schanck, "Estimating the cost of generic quantum pre-image attacks on SHA-2 and SHA-3", SAC 2016, [ePrint 2016/992](https://eprint.iacr.org/2016/992): a SHA-256 preimage attack about 2^153.8 surface-code cycles deep on about 2^12.6 logical qubits, 2^166.4 logical-qubit-cycles in total.
- NIST, [PQC FAQ](https://csrc.nist.gov/projects/post-quantum-cryptography/faqs), quoted above. NIST IR 8547, *Transition to Post-Quantum Cryptography Standards*, is an initial public draft (12 November 2024) with the timeline for retiring quantum-vulnerable **public-key** algorithms. I could not extract its text in this environment, so nothing is quoted from it here.

**Not covered: collisions.** For collisions (NIST categories 2 and 4) there is a quantum algorithm with about 2^(n/3) queries (Brassard, Høyer and Tapp, 1998). It needs a comparably huge quantum-accessible memory, and Bernstein ("Cost analysis of hash collisions: will quantum computers make SHARCS obsolete?", SHARCS 2009; title and venue from memory, not re-checked) argued that once that cost is counted it is no better than classical parallel collision search. I have not checked the current consensus beyond that, so no numbers are given.

**Contrast with Lesson 16.** Shor turns factoring from infeasible to polynomial, so RSA and elliptic-curve cryptography must be replaced (program step 7). Grover turns a 2^128 search into roughly 2^64 sequential, expensive, badly parallelisable steps. That is a margin cut, fixed if needed by longer keys.

**What this does NOT show.** A timeline. Every number here depends on hardware that does not exist, and the estimates above use different cost models (gates, depth, logical-qubit-cycles) that should not be mixed.
