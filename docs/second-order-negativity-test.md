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

---

# Results (added after sampling; everything above is unchanged)

Artifacts: `results/second_order_negativity_test.json`, `results/second_order_negativity_test.png`. Runner: `experiments/run_second_order_negativity_test.py` (~8 s; rerun byte-identical). 600 rows; target set 207 rows, flagged 393, as counted before sampling. Raw binomial kernels, no repair.

## Prediction vs observed (target set: non-flagged, spacing/s ≥ 0.5)

| # | Threshold | Observed | Milestone-2 baseline | Verdict |
|---|---|---|---|---|
| T1 | second-order mean \|P(PSD) gap\| ≤ 0.08 | **0.034** | 0.054 | PASS |
| T2 | inside Wilson 95% ≥ 54% | **73%** | 64% | PASS |
| T3 | first / second \|gap\| ratio ≥ 2 | **6.1** (0.209 / 0.034) | 4.3 | PASS |
| T4 | second-order mean \|N gap\| ≤ 0.12 | **0.061** | 0.078 | PASS |

**Verdict: the frozen second-order model passes the out-of-sample test.** It did slightly *better* than on the data it was fitted to. By subgroup: q=2 |gap| 0.042 with 68% inside (79 rows); q=3 0.029 with 76% (128 rows); 256 shots 0.045 with 62%, 1024 shots 0.035 with 72%, 4096 shots 0.029 with 78%. First order again under-predicted negatives in 100% of target rows with N̂ ≥ 0.5.

Flagged rows (393), as expected:

- Second-order mean |N gap| is **0.80** (expected ≥ 0.3), signed +0.65: it still under-counts negatives when eigenvalues mix. For q=3, n ≥ 17 (120 rows, never PSD in any draw), the gap is +1.48.
- First order under-predicted negatives in 100% of flagged rows with N̂ ≥ 0.5 (expected ≥ 90%).
- The P(PSD) gap looks small (0.021, 79% inside) only because most flagged rows have P(PSD) ≈ 0 both predicted and observed.
- The expected failure mode appeared in **6 flagged rows** (all q=3, n = 9–13): second order predicts P(PSD) ≤ 0.27, but the observed rate is 0.31–0.88. No flagged row missed in the other direction. Near-degenerate pairs make the 1/(λ_k − λ_j) terms too large, so second order is **biased pessimistic** there, never optimistic.

## Why it generalised

The correction has no fitted parameter. It is the expected second-order shift, computed from the exact kernel and σ_ij alone, so there was nothing to over-fit. The post-hoc part of milestone 2 was only the choice to add it. The improvement over the baseline is mostly composition: the new data has more rows at 4096 shots, where λ/s is larger and the model is most accurate. The guard does what it should, separating rows where perturbation theory is valid from those where it isn't. It is conservative: 393 of 600 rows are flagged, and many of them still have calibrated PSD rates.

Limits: same 80-point pool, same feature-map family, binomial model only (Aer was cross-checked in milestone 1 at q=2, n=40 only). The independence assumption in P(PSD) is still untested as a separate claim.
