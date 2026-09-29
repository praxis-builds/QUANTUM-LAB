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

---

# Results (added after the sweep; predictions above are unchanged)

Artifacts: `results/kernel_rank_prediction.json`, `results/kernel_rank_prediction_lambda_min.png`. Runner: `experiments/run_kernel_rank_prediction.py` (~5 s; rerun gives a byte-identical JSON). Raw kernels are unrepaired throughout. 240 sweep rows = 3 q × 4 n × 4 shots × 5 seeds.

**Sampler check.** For q = 2, n = 40, 512 shots, the standardized entry errors (error / √(K(1−K)/shots), 739 entries with K(1−K) ≥ 0.01) were: Aer mean 0.029, variance 1.000; binomial model mean 0.019, variance 1.048. Both match the theoretical (0, 1); the binomial shortcut is statistically consistent with Aer. This is a single-configuration check, not a proof for all q.

## Prediction vs observed

| # | Prediction | Observed | Verdict |
|---|------------|----------|---------|
| P1 | rank = min(n, 4^q) unless the map gives less | 11 of 12 (q, n) cells match exactly (q=1 → 4; q=2 → 8, 16, 16, 16; q=3 → 8, 16, 24). q=3, n=40 has rank **36**, not 40. Same in all 5 seeds. | Confirmed with the anticipated exception (note: the 36 was seen in the exact-only pre-look, so that cell is not a blind test) |
| P2 | nullity > 0 ⇒ every raw kernel indefinite; ≥ ~half of null directions negative, biased negative | Indefinite in **140/140** rows with nullity > 0. Negatives per nullity (mean over shots): q=1 0.50–0.55; q=2, n=40 0.61; q=2, n=24 0.88; q=3, n=40 **3.27**. | Indefiniteness confirmed. "≥ half" confirmed. "Biased negative": partial (see below) |
| P3 | λ_min(raw) ≈ −c/√shots; log–log slope in [−0.6, −0.4] for nullity > 0 | Slopes: q=1 −0.58, −0.50, −0.50, −0.49; q=2 n=24/40 −0.55, −0.52; q=3 n=40 −0.55. All within range; the plot shows the lines parallel to the 1/√shots reference. | Confirmed |
| P4 | Full-rank configs are PSD only if λ_min(exact) > 2σ√n; predicted indefinite everywhere except (q=3, n=8, 8192) | Indefinite at every shot count for (2,16), (3,16), (3,24), matching. But (3,8) is PSD in 5/5 seeds at 2048 **and** 8192 (predicted only 8192), and (2,8) is PSD in 5/5 seeds at 8192 (predicted indefinite), 3/5 at 2048, 2/5 at 128 and 512 (all predicted indefinite). | **Partly wrong**: the threshold was too pessimistic for n = 8 |

## Explanation of mismatches and caveats

1. **P1, q=3, n=40 (rank 36).** The q=3 map has only two independent features (qubit 2 reuses feature 0), so the 40 states lie on a 2-parameter family and 4 of them are linear combinations of the others in the Hermitian-matrix space. The 4^q bound was never the binding one here; the feature map was. This was disclosed as a possibility before running, not a surprise, but only the pre-look, not the theory, gave 36.
2. **P2, "biased negative" only partially.** For q=1 the negative fraction is about 0.50: no visible bias, consistent with the symmetric first-order term dominating. For q=2 (0.61 at n=40, 0.88 at n=24) the negative fraction is above 0.5, consistent with a negative second-order shift, but I did not isolate the second-order term, so this is suggestive, not demonstrated. The q=3, n=40 ratio of 3.27 is not a contradiction: negatives (11–15) exceed the nullity (4) because the kernel has many *tiny positive* eigenvalues below the noise floor, so the effective nullity is well above 4. Counting negatives per exact-zero eigenvalue undercounts the affected subspace. The n=16, q=2 and q=3 cases (nullity 0, λ_min(exact) ≈ 1e-5) are indefinite for the same reason.
3. **P4 too pessimistic at n = 8.** I used ‖E‖ ≈ 2σ√n as the shift of λ_min. By Weyl's inequality, λ_min(K) > ‖E‖ is a *sufficient* condition for PSD, not a necessary one, and I stated it as necessary. For a single well-separated smallest eigenvalue, the first-order shift is uᵀEu, whose standard deviation is about σ, not σ√n. The √n factor applies only when many eigenvalues are near-degenerate at the bottom (as at n ≥ 16 here). At (2,8), σ ≈ 0.005 at 8192 shots against λ_min(exact) ≈ 0.018 (about 3σ), so PSD in every seed is what this reasoning gives. This explanation fits the data but I did not test it with a separate experiment. The n ≥ 16 predictions (indefinite) held because there the spectrum's bottom is crowded.
4. **P3 outside its scope.** For full-rank n=8 the log–log slope is +0.18 (q=2) and +0.65 (q=3); n=16 gives −0.62 and −0.83. |mean λ_min| is not a meaningful scaling variable once the sign of the mean λ_min crosses zero (it flips positive at 8192 for n=8) or when λ_min(exact) offsets the noise. P3 was stated only for nullity > 0, so this is not a violation, just a boundary.

## What this supports and does not

Supports: in this simulator sweep, indefinite finite-shot fidelity kernels follow from rank deficiency (exact zeros or near-zeros) plus 1/√shots sampling noise; whenever rank < n the raw kernel was never PSD (140/140). Does not show: anything about hardware noise (there is none here), any classifier accuracy, or any comparison with a classical model. No repair was applied, so nothing in this study changes the data. Only one data family (moons, 2 features), one feature-map family and 5 seeds were used.
