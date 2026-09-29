# Per-eigenvalue negativity prediction

Status: **pre-registered**. Theory, predictions and the table below were committed before any finite-shot sampling for this study. Results are appended later; this part is not edited afterwards.

Motivation: in [kernel-rank-prediction.md](kernel-rank-prediction.md), P4 used the whole-matrix noise norm 2σ√n as a PSD threshold. That is a sufficient condition (Weyl), not a necessary one, and it was too pessimistic at n = 8. This study replaces it with a per-eigenvalue first-order model.

## Theory

Finite-shot kernel K̃ = K + E. E is symmetric with **zero diagonal** (the diagonal is exactly 1) and independent upper-triangle entries with Var(E_ij) = σ_ij² = K_ij(1 − K_ij)/shots (Binomial(shots, K_ij)/shots).

For an exact eigenpair (λ_k, u_k), first-order perturbation gives λ̃_k ≈ λ_k + u_kᵀ E u_k, and

    u_kᵀEu_k = 2 Σ_{i<j} u_ki u_kj E_ij,   s_k² = Var(u_kᵀEu_k) = 4 Σ_{i<j} u_ki² u_kj² σ_ij².

Treating that term as Gaussian (a sum of many independent entries):

- P(eigenvalue k negative) ≈ Φ(−λ_k / s_k)
- predicted negative count N̂ = Σ_k Φ(−λ_k / s_k)
- P(PSD) ≈ Π_k Φ(λ_k / s_k). **Assumption: the n first-order terms are independent.** They are uncorrelated only approximately (they share the entries of E); this is stated, not tested separately.

All three quantities use the exact kernel alone. No sampling.

## Where it should fail

1. **Crowded bottom spectrum.** Second order adds Σ_{j≠k} (u_jᵀEu_k)² / (λ_k − λ_j). For the lowest eigenvalue every term is negative (all λ_j > λ_k), and it grows as the bottom spacing shrinks relative to s. First order ignores this level repulsion and mixing, so it should **under-predict N and over-predict P(PSD)** whenever several eigenvalues sit within a few s_k of each other near zero.
2. **(Near-)zero eigenvalues.** For λ_k ≪ s_k, first order gives Φ(0) = 0.5 per eigenvalue. Milestone 1 observed 0.61–0.88 negatives per exact null direction at q = 2. Here n ≤ 16, so nullity is 0, but q = 2 at n = 15, 16 has λ_min ~1e-5 ≪ s (a numerically near-null bottom), so I expect the same excess there.
3. **Well-separated, large λ/s.** When the bottom spacing is ≫ s and at most one eigenvalue is within ~3 s of zero, first order should be accurate. That favours small n and high shots (n = 8–10 at 2048–8192).

Conventions: basis |q1 q0>. Negative means λ < −1e-10 (PSD_TOLERANCE). Data: `make_subset_features(n, subset)` from `kernel_spectrum.py`, subsets 0–4 (seeds 20260928 + subset). Sampling: NumPy binomial model (cross-checked against Aer in milestone 1), 200 draws per kernel per shot count, RNG `default_rng([20260928, q, n, shots, subset, 1])`. Sweep: q ∈ {2, 3}, n ∈ {8, …, 16}, shots ∈ {128, 512, 2048, 8192}. The unit of comparison is **one exact kernel**: the prediction is conditional on it, so each of the 360 kernels gets a predicted vs observed PSD rate (200 draws) and N̂ vs mean observed count.

## Predictions

- **A-P1 (direction).** Aggregated over all kernels, observed mean negatives ≥ N̂ and observed PSD rate ≤ predicted P(PSD). Expect this for most individual kernels where N̂ ≥ 0.5.
- **A-P2 (where it works).** Kernels with bottom spacing (λ₂ − λ₁)/s₁ ≥ 2 and at most one eigenvalue within 3 s_k of zero: predicted P(PSD) within the Wilson 95% interval of the observed rate for ≥ 70% of them, and |N_obs − N̂| ≤ 0.15 on average.
- **A-P3 (where it breaks).** The gap N_obs − N̂ grows as spacing/s shrinks. Kernels with spacing/s < 1 have mean N_obs − N̂ ≥ 0.3.
- **A-P4 (near-null bottom).** For q = 2, n ∈ {15, 16}, the ratio N_obs/N̂ is 1.2–1.8 at every shot count.

### Predicted table (from exact kernels only)

Each cell: mean N̂ [min–max over 5 subsets] / mean P(PSD) [min–max].

**q = 2**

| n | mean λ_min(exact) | 128 shots | 512 | 2048 | 8192 |
|---|---|---|---|---|---|
| 8 | 1.8e-02 | 0.51 [0.18–0.79] / 0.57 [0.37–0.83] | 0.28 [0.01–0.59] / 0.74 [0.49–0.99] | 0.15 [0.00–0.35] / 0.85 [0.65–1.00] | 0.06 [0.00–0.22] / 0.94 [0.78–1.00] |
| 9 | 5.8e-03 | 0.87 [0.52–1.11] / 0.36 [0.25–0.54] | 0.54 [0.24–0.74] / 0.54 [0.41–0.77] | 0.29 [0.06–0.48] / 0.72 [0.52–0.94] | 0.15 [0.00–0.44] / 0.85 [0.56–1.00] |
| 10 | 3.8e-03 | 1.08 [0.73–1.34] / 0.28 [0.18–0.41] | 0.70 [0.35–0.97] / 0.45 [0.30–0.66] | 0.43 [0.14–0.63] / 0.62 [0.44–0.86] | 0.27 [0.01–0.48] / 0.74 [0.53–0.99] |
| 11 | 3.1e-03 | 1.27 [0.93–1.62] / 0.22 [0.13–0.33] | 0.86 [0.49–1.21] / 0.37 [0.22–0.58] | 0.53 [0.12–0.84] / 0.55 [0.34–0.88] | 0.30 [0.00–0.63] / 0.72 [0.45–1.00] |
| 12 | 1.8e-03 | 1.71 [1.45–1.90] / 0.12 [0.09–0.17] | 1.26 [0.91–1.48] / 0.21 [0.16–0.34] | 0.85 [0.43–1.14] / 0.37 [0.23–0.61] | 0.52 [0.14–0.87] / 0.56 [0.33–0.86] |
| 13 | 6.2e-04 | 2.00 [1.68–2.33] / 0.08 [0.05–0.12] | 1.53 [1.27–1.87] / 0.15 [0.09–0.20] | 1.10 [0.87–1.44] / 0.25 [0.16–0.34] | 0.76 [0.52–0.98] / 0.39 [0.30–0.53] |
| 14 | 3.1e-04 | 2.38 [2.24–2.54] / 0.05 [0.04–0.06] | 1.89 [1.71–2.05] / 0.09 [0.07–0.11] | 1.44 [1.19–1.68] / 0.16 [0.11–0.22] | 1.05 [0.87–1.28] / 0.27 [0.19–0.33] |
| 15 | 5.7e-05 | 2.73 [2.54–3.03] / 0.03 [0.02–0.04] | 2.20 [1.94–2.49] / 0.06 [0.04–0.08] | 1.69 [1.41–1.87] / 0.12 [0.09–0.16] | 1.27 [1.06–1.58] / 0.20 [0.13–0.24] |
| 16 | 1.7e-05 | 3.09 [2.88–3.39] / 0.02 [0.01–0.02] | 2.57 [2.33–2.84] / 0.04 [0.02–0.05] | 2.10 [1.82–2.29] / 0.07 [0.05–0.09] | 1.69 [1.38–2.03] / 0.11 [0.07–0.16] |

**q = 3**

| n | mean λ_min(exact) | 128 shots | 512 | 2048 | 8192 |
|---|---|---|---|---|---|
| 8 | 3.2e-02 | 0.29 [0.02–0.64] / 0.74 [0.47–0.98] | 0.11 [0.00–0.30] / 0.89 [0.71–1.00] | 0.02 [0.00–0.09] / 0.98 [0.91–1.00] | 0.00 [0.00–0.00] / 1.00 [1.00–1.00] |
| 9 | 1.8e-02 | 0.39 [0.21–0.82] / 0.66 [0.36–0.80] | 0.16 [0.02–0.49] / 0.85 [0.54–0.98] | 0.07 [0.00–0.35] / 0.93 [0.65–1.00] | 0.04 [0.00–0.21] / 0.96 [0.79–1.00] |
| 10 | 1.1e-02 | 0.61 [0.19–0.97] / 0.51 [0.30–0.82] | 0.34 [0.02–0.63] / 0.70 [0.44–0.98] | 0.19 [0.00–0.48] / 0.82 [0.53–1.00] | 0.12 [0.00–0.43] / 0.88 [0.57–1.00] |
| 11 | 9.0e-03 | 0.72 [0.46–1.15] / 0.44 [0.24–0.59] | 0.38 [0.18–0.77] / 0.66 [0.39–0.83] | 0.16 [0.01–0.44] / 0.85 [0.58–0.99] | 0.07 [0.00–0.28] / 0.93 [0.72–1.00] |
| 12 | 6.1e-03 | 1.04 [0.66–1.43] / 0.31 [0.16–0.47] | 0.61 [0.22–1.05] / 0.53 [0.26–0.78] | 0.31 [0.02–0.76] / 0.73 [0.39–0.98] | 0.17 [0.00–0.51] / 0.84 [0.53–1.00] |
| 13 | 5.2e-03 | 1.12 [0.68–1.59] / 0.27 [0.13–0.45] | 0.68 [0.30–1.17] / 0.47 [0.24–0.72] | 0.37 [0.07–0.71] / 0.67 [0.42–0.93] | 0.20 [0.00–0.39] / 0.80 [0.62–1.00] |
| 14 | 2.1e-03 | 1.58 [1.46–1.74] / 0.14 [0.11–0.16] | 1.06 [0.88–1.17] / 0.28 [0.24–0.35] | 0.60 [0.42–0.73] / 0.49 [0.40–0.62] | 0.31 [0.12–0.50] / 0.71 [0.54–0.88] |
| 15 | 1.8e-03 | 1.79 [1.47–1.97] / 0.11 [0.08–0.16] | 1.23 [0.95–1.47] / 0.23 [0.16–0.31] | 0.75 [0.59–0.96] / 0.41 [0.31–0.50] | 0.40 [0.29–0.57] / 0.63 [0.51–0.72] |
| 16 | 1.0e-03 | 2.15 [2.04–2.41] / 0.07 [0.05–0.08] | 1.56 [1.43–1.73] / 0.14 [0.12–0.17] | 1.04 [0.94–1.11] / 0.28 [0.24–0.32] | 0.64 [0.46–0.81] / 0.47 [0.37–0.59] |

## Disclosure: what was known before writing

- Milestone 1 already sampled subsets 0–4 at n = 8 and 16 (one draw each; same subsets, different RNG stream). There, (q=2, n=8) was PSD in 5/5 draws at 8192 (this table predicts 0.94), (q=3, n=8) 5/5 at 2048 and 8192 (0.98, 1.00), and n = 16 was never PSD (0.11 or below). Its negative counts at q=2, n=16 were 4.0 (128) and 2.6 (8192) against N̂ 3.09 and 1.69 here: under-prediction, as in A-P1. So A-P1 and A-P4 are informed by those rows, not blind.
- n = 9–15 have not been sampled at all.
