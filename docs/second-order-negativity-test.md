# Out-of-sample test of the second-order negativity model

Status: **pre-registered**. Committed before any finite-shot sampling for this study. Results are appended later in separate commits; this part is never amended.

## What is being tested

In [eigenvalue-negativity-prediction.md](eigenvalue-negativity-prediction.md) the first-order model λ̃_k ≈ λ_k + u_kᵀEu_k over-predicted P(PSD). After seeing the data, I added the expected second-order shift

    δ_k = Σ_{j≠k} Var(u_jᵀ E u_k) / (λ_k − λ_j)

and predicted P(eigenvalue k < 0) ≈ Φ(−(λ_k + δ_k)/s_k), with P(PSD) ≈ Π_k (1 − P_k) (independence assumed). That model was fitted post hoc. Here it is frozen (`predict_negativity_second_order`, unchanged) and tested on configurations it has never seen.

## New data

- Subsets 5–14 (`make_subset_features(n, subset)`; seed 20260928 + subset). These are **new random draws from the same 80-point moons pool**, not disjoint data: points can overlap with subsets 0–4.
- q = 2 with n ∈ {8, …, 14}; q = 3 with n ∈ {8, …, 20} (n = 17–20 never used before).
- Shots ∈ {256, 1024, 4096}, none used before.
- 200 binomial draws per kernel and shot count; RNG `default_rng([20260928, q, n, shots, subset, 2])` (stream tag 2, new).
- 600 kernel × shots rows in total. Negative means λ < −1e-10.

## Degeneracy guard

A kernel × shots row is **flagged** if some pair k ≠ j has |λ_k − λ_j| < 0.5 · s_k (`degeneracy_flag`). There the 1/(λ_k − λ_j) terms are unreliable. Flagged rows are **reported separately, not dropped**. With this guard, every row with bottom spacing/s < 0.5 is also flagged: in milestone 2, 211 of 360 rows were flagged, including all of them with spacing/s < 0.5.

## Baseline (milestone-2 rows, recomputed with the guard; no new sampling)

Target set = non-flagged rows with bottom spacing (λ₂ − λ₁)/s₁ ≥ 0.5 (149 rows):

| model | mean \|P(PSD) gap\| | inside Wilson 95% | mean \|N gap\| |
|---|---|---|---|
| second order | 0.054 | 64% | 0.078 |
| first order | 0.233 | 21% | 0.261 |

Flagged rows (211): second order mean |P(PSD) gap| 0.023, inside 70%, but mean |N gap| **0.616**. The PSD rate looks fine only because predicted and observed are both near 0 there; the count is badly off.

Exact-only look at the new data (no sampling): 207 of 600 rows are in the target set and 393 are flagged. All q=3 rows with n ≥ 17 are flagged at every shot count, as are q=2 rows with n ≥ 13.

## Pre-registered targets (target set, new data)

A target passes if its stated inequality holds on the new target-set rows.

| # | Target | Threshold | Basis |
|---|---|---|---|
| T1 | second-order mean \|P(PSD) gap\| | **≤ 0.08** | 1.5 × 0.054 |
| T2 | share of second-order P(PSD) inside the observed Wilson 95% | **≥ 54%** | 64% − 10 points |
| T3 | second order beats first order on mean \|P(PSD) gap\|, same rows | **ratio first/second ≥ 2** | old ratio 4.3 |
| T4 | second-order mean \|N gap\| | **≤ 0.12** | 1.5 × 0.078 |

The model **passes** the out-of-sample test if all of T1–T4 pass. It **fails** if T1 or T2 fails. If only T3 or T4 fails, the verdict is partial and the failure is explained.

Expectations for flagged rows (not pass/fail, reported for honesty): second-order mean |N gap| ≥ 0.3 (strong mixing makes counts unreliable), and first order still under-predicts negatives (observed ≥ first-order N̂ in ≥ 90% of rows with N̂ ≥ 0.5). A few flagged rows may show the milestone-2 failure mode, where the second-order P(PSD) is near 0 but the observed rate is well above it.

Why I expect it to generalise but lose some accuracy: the correction is a derived mean shift, not a fitted parameter, so it should transfer. But the new shot counts put more rows at intermediate λ/s, where Φ is steep, and the independence assumption in the P(PSD) product is untested.
