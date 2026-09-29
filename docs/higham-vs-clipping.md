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
