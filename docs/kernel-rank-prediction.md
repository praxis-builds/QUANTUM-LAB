# Kernel rank predicts PSD violation

Status: **pre-registered**. This file was committed before `kernel_spectrum.py`, the runner or any finite-shot sweep existed. Results and verdicts are appended later in a separate commit; the Theory and Predictions sections are not edited afterwards.

## Theory

For pure states, the fidelity kernel is K_ij = |⟨φ_i|φ_j⟩|² = Tr(ρ_i ρ_j) with ρ_i = |φ_i⟩⟨φ_i|. That is the Hilbert–Schmidt inner product of Hermitian matrices, which live in a real vector space of dimension 4^q. So K is a Gram matrix of n vectors in R^(4^q):

- K is exactly PSD, and rank(K) ≤ min(n, 4^q). The nullity is n − rank.
- Hence a 40-point, q = 2 kernel has at most 16 nonzero eigenvalues and at least 24 exact zeros.
- A finite-shot estimate is K̃ = K + E, where E is symmetric with independent entries of mean zero and variance σ_ij² = K_ij(1 − K_ij)/shots (each entry is Binomial(shots, K_ij)/shots; the diagonal is exactly 1).
- Zero eigenvalues of K are not protected against E. To first order the null-space eigenvalues become those of P E P (P = projector onto the null space), which is a symmetric random matrix with a spectrum symmetric around 0 (a semicircle of radius about 2σ√nullity). Second-order perturbation theory adds −Σ (uᵀEv)²/(λ_v) terms, which push null eigenvalues *down* only through coupling to positive eigenvalues, and pushes up nothing, so the net shift is biased negative.
- Random-matrix scaling: ‖E‖ ≈ 2σ√n ∝ 1/√shots.
- A full-rank K can survive noise only if λ_min(K) exceeds roughly the noise norm.
- Qubits/features: samples have 2 features. Qubit i receives feature i mod 2 (H, RZ(x), RY(x²), then a CZ chain). q = 1 uses only feature 0; q = 3 uses feature 0 twice. Expected consequence: the reachable states lie on a low-dimensional manifold, so the "unless the feature map gives less" clause may bind for q = 3.

Conventions: basis |q1 q0>. Rank tolerance: eigenvalue > max(n, 4^q)·ε·λ_max. PSD tolerance: λ_min ≥ −1e-10 (the repo's PSD_TOLERANCE). Sweep: q ∈ {1,2,3}, n ∈ {8,16,24,40}, shots ∈ {128,512,2048,8192}, 5 seeds (base seed 20260928 + k for subset choice, sampling seeded separately). Data: existing `make_dataset` (80-point moons), stratified subset of size n, StandardScaler fitted on that subset. Sampling: NumPy binomial model, cross-checked against Aer at q = 2, n = 40.

## Disclosure: what was looked at before writing this

Before committing this file I computed the **exact** (no sampling) kernels for the sweep with a scratch script, because P4 needs λ_min(exact). That exposed exact ranks and λ_min(exact), and I did not run any finite-shot sample. So P1 for q = 3, n = 40 (and the P4 numbers) are not blind predictions; they are reported here and the finite-shot behaviour (P2, P3) remains untested.

Exact-only pre-look (same in all 5 seeds unless a range is given):

| q | n=8 | n=16 | n=24 | n=40 |
|---|-----|------|------|------|
| 1 | rank 4 | rank 4 | rank 4 | rank 4 |
| 2 | rank 8 | rank 16 | rank 16 | rank 16 |
| 3 | rank 8 | rank 16 | rank 24 | rank **36** |

## Predictions

**P1. Exact rank = min(n, 4^q), unless the feature map gives less.**
Theory-only expected ranks: q=1 → 4 for every n (4^1 = 4); q=2 → 8, 16, 16, 16; q=3 → 8, 16, 24, 40 (4^3 = 64 exceeds n). Caveat: the q = 3 map uses only two independent features, so rank < 40 at n = 40 is possible; the pre-look above found 36 there, so that cell is already informed, not blind. All other cells match the theory value in the pre-look.

**P2. When nullity > 0, every raw finite-shot kernel is indefinite.**
About half or more of the null directions go negative, biased negative by the second-order term. Concretely: all q = 1 rows (nullity n − 4 ≥ 4), q = 2 with n ≥ 24, and q = 3 with n = 40 have PSD rate 0%. Expect the negative count to be ≥ ~50% of the nullity (semicircle symmetric) and likely above it.

**P3. λ_min(raw) ≈ −c/√shots.**
The log–log slope of |mean λ_min(raw)| against shots is expected in [−0.6, −0.4] for nullity > 0 configurations, with c growing with n.

**P4. With nullity = 0, raw kernel is PSD only if λ_min(exact) > ~2σ√n**, σ = √(K̄(1 − K̄)/shots) using each config's mean off-diagonal K̄.
Full-rank configs and their mean λ_min(exact): (q=2, n=8) 1.8e-2; (q=2, n=16) 1.7e-5 (small: rank equals n only barely above tolerance); (q=3, n=8) 3.2e-2; (q=3, n=16) 1.0e-3; (q=3, n=24) 1.6e-5.
Predicted noise threshold 2σ√n at shots 128 / 512 / 2048 / 8192: (2,8) 0.24 / 0.12 / 0.060 / 0.030; (2,16) 0.35 / 0.17 / 0.086 / 0.043; (3,8) 0.23 / 0.11 / 0.056 / 0.028; (3,16) 0.33 / 0.16 / 0.082 / 0.041; (3,24) 0.40 / 0.20 / 0.10 / 0.050.
Prediction: **every full-rank config is indefinite at every shot count, with one marginal exception: (q=3, n=8, shots=8192) is predicted PSD (0.032 > 0.028)**. That is a borderline call; a per-seed split is plausible.
