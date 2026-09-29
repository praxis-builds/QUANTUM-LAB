# Model comparison with resolution: 50 repeated splits

Status: **pre-registered**. Committed before `repeated_model_comparison.py` existed and before any metric below was computed. Results are appended later in separate commits; this part is never amended.

## Why

In [repair-metric-comparison.md](repair-metric-comparison.md), every model scored 10/12 on a single 12-point test set, so accuracy could not separate anything. Here I use the extended study's repeated splits to get resolution. I report paired differences with bootstrap CIs, not single numbers.

## Design

- Data and splits: the 80-point `make_dataset` (seed 20260928) and `RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=20260928)`. That is the same 50 splits as the extended evaluation, 64 train and 16 test each. The scaler is fitted on each training fold.
- Per split, on all 80 points in train-then-test order:
  - **exact**: exact statevector fidelity kernel (existing 2-qubit map).
  - **raw**: one binomial finite-shot draw at **512 shots** of the full 80 × 80 kernel (unit diagonal), RNG `default_rng([20260928, split, 512, 3])`.
  - **clipped**: existing `repair_kernel_psd` on the full raw matrix (transductive).
  - **Higham-trans**: `higham_nearest_correlation` on the full 80 × 80 raw matrix (transductive: uses test inputs, never labels).
  - **Higham-ind**: Higham on the 64 × 64 raw **training block only**; the test-to-train block is left raw (inductive, no test inputs used).
  - **RBF**: classical baseline, precomputed RBF with the extended study's `gamma='scale'` rule.
- Classifier: `SVC(kernel="precomputed", C=1.0)` for all models.
- Metrics per split: test accuracy (16 points), Pearson r of the test decision values vs the exact SVC and vs the RBF SVC, and training-block alignment vs exact and vs RBF.
- Paired differences: per split, model − exact and model − RBF, for accuracy, and alignment and r where meaningful. Also Higham-trans − Higham-ind.
- **Uncertainty:** a cluster bootstrap over the 10 repeats (the 5 folds of one repeat stay together), with 10,000 resamples, RNG `default_rng([20260928, 4])`, and percentile 95% CIs. "Distinguishable from zero" means the CI excludes 0. **Caveat:** all 50 splits reuse the same 80 points, so these CIs describe split-to-split variability on this data set. They say nothing about generalisation to new data, and 10 clusters give coarse percentiles. This follows the extended study's warning that repeated folds are not independent. The CIs are descriptive, not significance tests.

**Repairs change the data.** Transductive repairs use test inputs (never labels) and are not standard held-out evaluations.

## Already known (disclosure)

The extended 5×10 study reported exact-quantum minus RBF accuracy on these same 50 splits: mean **−0.060**, median −0.0625, SD 0.059, with only 1 of 50 splits positive. Milestone 2 found Higham > clipped > raw on alignment and decision r at 128–2048 shots on one split.

## Predictions

- **B-P1 (accuracy vs exact).** For raw, clipped, Higham-trans and Higham-ind, the mean accuracy − exact is within ±0.02 and the CI **contains 0**. At 512 shots, sampling noise flips at most an occasional test point.
- **B-P2 (accuracy vs RBF).** Exact − RBF has a CI that **excludes 0**, with a negative mean ≈ −0.06 (known). Every finite-shot variant − RBF is also negative with a CI excluding 0. RBF is the better classifier here.
- **B-P3 (decision r vs exact).** For every finite-shot variant, 1 − r has a CI **excluding 0**, with mean r in [0.99, 0.9995]. The order of mean r is Higham-trans > clipped > raw (each paired difference has a CI excluding 0), and Higham-ind lies between raw and Higham-trans.
- **B-P4 (alignment vs exact, training block).** 1 − alignment has a CI excluding 0 for every finite-shot variant, with raw < clipped < Higham-trans (CIs of the paired differences excluding 0). Higham-ind and Higham-trans training blocks differ by < 2e-4 in alignment. RBF alignment to exact is clearly lowest (≈ 0.96, as on the single split).
- **B-P5 (transductive vs inductive Higham).** Accuracy difference: CI **contains 0**. Decision r: Higham-trans − Higham-ind is **positive with a CI excluding 0**, of size 0.0005–0.003, because the transductive repair also denoises the test-to-train block that the inductive version leaves raw.
- **B-P6 (the saved clipping-step diagnostic).** For the 15 saved matrices, the new `clipping_step_distances` reproduces the Part B explanation in [higham-vs-clipping.md](higham-vs-clipping.md). The projection alone is closer to exact than raw in 15/15, and projection plus rescale is further than raw in 15/15. The numbers match that doc to 3 decimals where they were quoted (e.g. 128 shots, replicate 0: 1.387 → 1.119 → 1.715).
