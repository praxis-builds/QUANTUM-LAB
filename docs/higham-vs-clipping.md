# Higham nearest-correlation repair vs eigenvalue clipping

Status: **pre-registered**. Written and committed before `nearest_correlation.py` existed and before either repair was applied for this study. Results are appended later; this part is not edited afterwards.

**Both repairs change the data.** A repaired kernel is no longer the measured estimate. Both are also **transductive** here: each repairs the full 40 × 40 subset kernel, which includes the 12 test inputs (never their labels), as in [finite-shot-psd-repair.md](finite-shot-psd-repair.md).

## Setup

- Input: the 15 raw finite-shot 40 × 40 kernels saved in `results/finite_shot_kernel_psd_repair.json` (3 shot budgets 128 / 512 / 2048 × 5 Aer shot seeds; train rows first). That file is read only.
- Exact reference: the exact statevector kernel on the same 40 points in the same order, regenerated with the existing `_make_fixed_split` + `feature_statevectors` path (seed 20260928, 28/12 split, scaler fitted on training data).
- **Clipping** (existing `repair_kernel_psd`): set negative eigenvalues to 0, then rescale D^{-1/2} P D^{-1/2} to restore a unit diagonal.
- **Higham (2002)**: alternating projections with Dykstra's correction between the PSD cone S and the unit-diagonal affine set U. It converges to the Frobenius-nearest correlation matrix P_C(R), with C = S ∩ U.
- Reported per matrix: ‖repair − raw‖_F, ‖repair − exact‖_F, λ_min, iterations (clipping = 1 pass).

## Reasoning: which repair lands closer to the exact kernel?

Being nearest to raw does not by itself imply being nearest to exact. But here the exact kernel K has a special property: **K ∈ C** (it is PSD with unit diagonal). For a projection onto a closed convex set and any point K in that set,

    ‖P_C(R) − K‖² ≤ ‖R − K‖² − ‖R − P_C(R)‖².

So Higham is **guaranteed** to be closer to exact than raw is, by at least its own repair distance.

Clipping has no such guarantee. Its first step is the projection onto S, which also contains K, so that step alone does move closer to K. The rescale step is not a projection, though. Clipping only removes negative eigenvalues, so diag(P) = 1 + Σ_{λ<0} |λ| u_i² ≥ 1, and the rescale divides every off-diagonal entry by a factor ≥ 1. That is a systematic **shrink toward 0**, while the raw off-diagonal entries are unbiased estimates of K (mean ≈ 0.4). Higham fixes the diagonal without that uniform shrink.

Neither repair recovers the true rank. K has rank 16, but a repair only zeros the negative directions, and about half of the null-space noise is positive and stays.

## Predictions

- **B-P1 (guaranteed).** ‖Higham − raw‖_F ≤ ‖clip − raw‖_F for all 15 matrices.
- **B-P2 (guaranteed).** ‖Higham − exact‖_F < ‖raw − exact‖_F for all 15.
- **B-P3.** Clipping is also closer to exact than raw is, for all 15. The shrink from rescaling is second order compared with the gain from removing negative energy.
- **B-P4 (the real question).** Higham is closer to exact than clipping for **all 15**, but only by a little: the ratio ‖H − K‖/‖clip − K‖ lies in [0.95, 1.00), and the difference shrinks as shots increase.
- **B-P5 (magnitude).** ‖repair − exact‖/‖raw − exact‖ ≈ 0.85–0.95 for both repairs. Rough estimate: the null space holds about 24/40 of the dimensions, so the noise energy there is about (24/40)² ≈ 36% of ‖E‖². About half of that is negative and gets removed, which is roughly 18% of the energy, or about 10% of the distance.
- **B-P6.** λ_min: both repairs are ≥ −1e-10 and sit on the PSD boundary (λ_min ≈ 0). Higham needs 20–500 iterations at tolerance 1e-10.

---

# Results (added after running; everything above is unchanged)

Artifacts: `results/higham_vs_clipping.json`, `results/higham_vs_clipping_distances.png`. Runner: `experiments/run_higham_vs_clipping.py` (~3 s). The source file `results/finite_shot_kernel_psd_repair.json` was read only (md5 unchanged). Both repairs **change the data** and are transductive.

| shots | rep | ‖raw − exact‖ | ‖clip − raw‖ | ‖clip − exact‖ | ‖Higham − raw‖ | ‖Higham − exact‖ | λ_min Higham | Higham iterations |
|---|---|---|---|---|---|---|---|---|
| 128 | 0 | 1.387 | 1.623 | 1.715 | 0.975 | 0.914 | -7.5e-11 | 60 |
| 128 | 1 | 1.484 | 1.687 | 1.877 | 1.031 | 0.997 | -9.1e-11 | 52 |
| 128 | 2 | 1.370 | 1.580 | 1.690 | 0.974 | 0.890 | -9.7e-11 | 58 |
| 128 | 3 | 1.373 | 1.554 | 1.729 | 0.951 | 0.916 | -7.6e-11 | 60 |
| 128 | 4 | 1.336 | 1.475 | 1.556 | 0.901 | 0.907 | -8.9e-11 | 66 |
| 512 | 0 | 0.712 | 0.791 | 0.913 | 0.471 | 0.499 | -7.8e-11 | 49 |
| 512 | 1 | 0.724 | 0.808 | 0.931 | 0.482 | 0.509 | -9.8e-11 | 51 |
| 512 | 2 | 0.705 | 0.799 | 0.887 | 0.483 | 0.478 | -7.9e-11 | 58 |
| 512 | 3 | 0.685 | 0.800 | 0.893 | 0.475 | 0.460 | -9.8e-11 | 50 |
| 512 | 4 | 0.702 | 0.760 | 0.830 | 0.455 | 0.501 | -8.2e-11 | 52 |
| 2048 | 0 | 0.343 | 0.358 | 0.445 | 0.211 | 0.260 | -8.5e-11 | 45 |
| 2048 | 1 | 0.326 | 0.356 | 0.413 | 0.211 | 0.237 | -9.4e-11 | 47 |
| 2048 | 2 | 0.343 | 0.387 | 0.433 | 0.229 | 0.240 | -7.0e-11 | 47 |
| 2048 | 3 | 0.357 | 0.394 | 0.454 | 0.233 | 0.257 | -7.1e-11 | 48 |
| 2048 | 4 | 0.344 | 0.359 | 0.408 | 0.213 | 0.256 | -9.1e-11 | 45 |

Clipped λ_min is about −2e-15 in every row (numerically 0). Clipping is one pass.

Mean distance ratios per shot budget (to exact):

| shots | Higham / raw | clip / raw | Higham / clip |
|---|---|---|---|
| 128 | 0.67 | 1.23 | 0.54 |
| 512 | 0.69 | 1.26 | 0.55 |
| 2048 | 0.73 | 1.26 | 0.58 |

## Prediction vs observed

| # | Prediction | Observed | Verdict |
|---|---|---|---|
| B-P1 | ‖Higham − raw‖ ≤ ‖clip − raw‖, 15/15 | 15/15; Higham is 0.59–0.62 of clipping's distance to raw | Confirmed (a theorem) |
| B-P2 | Higham closer to exact than raw, 15/15 | 15/15, ratio 0.65–0.76 | Confirmed (a theorem) |
| B-P3 | clipping closer to exact than raw, 15/15 | **0/15**. Clipping is *further* from exact than raw in every matrix (ratio 1.16–1.30). | **Wrong** |
| B-P4 | Higham closer to exact than clip in 15/15, ratio in [0.95, 1.00) | Direction right in 15/15, but the ratio is **0.52–0.63**, a large effect, not a small one. It does not shrink with shots. | Direction confirmed, magnitude wrong |
| B-P5 | ‖repair − exact‖/‖raw − exact‖ ≈ 0.85–0.95 for both | Higham 0.65–0.76 (better than predicted); clipping 1.16–1.30 (worse than raw) | Wrong for both |
| B-P6 | λ_min ≈ 0 within 1e-10; Higham 20–500 iterations | Higham λ_min between −1e-10 and −7e-11 (the stopping rule's edge); clipping about −2e-15; 45–66 iterations | Confirmed |

## Explanation of mismatches

1. **B-P3: clipping moves away from exact because of the rescale, not the clipping.** A diagnostic (not saved as an artifact) split the two steps. At 128 shots, replicate 0, the PSD projection alone takes the distance from 1.39 to **1.12**, closer to exact as the convex-projection argument says. It also raises the diagonal to a mean of 1.067, because it adds back the removed negative energy (Σ|λ_neg| ≈ 2.7). Rescaling to a unit diagonal then divides every off-diagonal entry by about 1.07, and the mean off-diagonal value falls from 0.436 (exact, and raw 0.438) to **0.408**. That bias is coherent across all 1,560 off-diagonal entries, so it adds up to O(1) in Frobenius norm. I called it "second order", which was wrong: the noise reduction lives in a subspace, while the shrink hits every entry with the same sign. The same pattern holds at 512 (diag 1.031, mean off-diagonal 0.421) and 2048 (1.014, 0.429).
2. **B-P5: Higham is better than predicted** because the effective null space is much larger than the exact nullity (24). The exact spectrum falls fast (top five eigenvalues 18.5, 10.3, 4.8, 2.3, 2.1, then 0.73 and below), and 31–33 of the 40 exact eigenvalues are below the noise norm 2σ√n. The same effect appeared in milestone 1. On top of that, the unit-diagonal constraint is true of the exact kernel, and Higham enforces it without any shrink, so it adds real information that clipping only imitates by distorting all entries.
3. **B-P4 does not shrink with shots.** Both the noise and the rescale shrink scale as 1/√shots, so their ratio stays about constant (per-budget means 0.54, 0.55, 0.58; range 0.52–0.63).

Consequence for [finite-shot-psd-repair.md](finite-shot-psd-repair.md): the existing repaired kernels there are further from the exact kernel than the raw ones. That document already says clipping is not a nearest-correlation repair. This result quantifies what that costs. The existing study and its files are not changed.
