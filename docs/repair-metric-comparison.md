# Metrics that can separate kernel models

Status: **pre-registered**. Written and committed before `repair_metrics.py` existed and before any metric below was computed. Results are appended later; this part is not edited afterwards.

## Question

On the fixed 40-point, 28/12 split, the existing PSD study found that raw, clipped, exact-kernel and RBF classifiers **all scored 0.833 accuracy (10/12)** ([finite-shot-psd-repair.md](finite-shot-psd-repair.md)). Accuracy on 12 points cannot tell these models apart. Which metrics can?

## Models (same split, seed 20260928, scaler fitted on training data)

- **exact**: exact statevector fidelity kernel (reference).
- **raw**: each of the 15 saved raw finite-shot kernels (read only from `results/finite_shot_kernel_psd_repair.json`; 128 / 512 / 2048 shots × 5 seeds). The test block is the raw test-to-train block.
- **clipped** and **Higham**: the two repairs from [higham-vs-clipping.md](higham-vs-clipping.md), applied to the full 40 × 40 raw matrix, then split into train and test blocks. **Transductive:** the repair uses the 12 test inputs (never their labels), so these are not clean held-out evaluations. **Both repairs change the data.**
- **RBF**: classical baseline, `SVC(kernel="rbf", C=1, gamma="scale")` equivalent, via `rbf_kernel` with the existing `_scaled_rbf_gamma` (0.5).

All classifiers are `SVC(kernel="precomputed", C=1.0)`, as in the existing studies.

## Metrics

- **Alignment to exact** on the 28 × 28 training block: A(K1, K2) = ⟨K1, K2⟩_F / (‖K1‖_F ‖K2‖_F).
- **Decision agreement**: `decision_function` on the 12 test points, compared with the exact-kernel SVC. Pearson r, and sign agreement out of 12.
- **Accuracy** with a Wilson 95% interval (z = 1.96).

## Reasoning

- ‖K_train‖_F ≈ √(28 + 756·0.44²) ≈ 14.7. At 128 shots the 28 × 28 noise has ‖E‖_F ≈ 0.97. For a perturbation, 1 − A ≈ ½ (‖E_⊥‖/‖K‖)² ≈ 2e-3, so alignment is very close to 1 and saturates quickly with shots.
- Alignment is scale invariant, so clipping's uniform off-diagonal shrink (factor ≈ 0.935 at 128 shots, see Part B) costs little: with a fixed unit diagonal, about 4e-4. That is about the same size as the noise it removes.
- The decision function f(x) = Σ α_i y_i K(x, x_i) + b depends on the support-vector set, which a small kernel change can alter. So I expect decision agreement to separate the finite-shot models from exact more clearly than alignment does, and to improve with shots.
- RBF is a different kernel, not a noisy copy of the exact one, so it should be clearly separated on alignment, even though its accuracy is identical.

## Predictions

- **C-P1 (alignment, quantum variants).** Raw, clipped and Higham alignments to exact are all ≥ 0.995 at every shot budget, and ≥ 0.999 at 2048. Among the three at a given budget, the mean alignments differ by < 0.003. Higham has the highest alignment in ≥ 12 of 15 matrices. Clipping is not systematically above raw.
- **C-P2 (alignment, RBF).** RBF alignment to exact is < 0.97, clearly below every quantum variant. It is a single number, since RBF is deterministic.
- **C-P3 (decision agreement).** Pearson r with the exact SVC: mean ≥ 0.9 at 128 and ≥ 0.98 at 2048 for raw and both repairs. Sign agreement: mean ≥ 10/12 at 128 and ≥ 11/12 at 2048. The raw/clipped/Higham differences in mean r are < 0.02 at every budget (no consistent winner). RBF has r < 0.95.
- **C-P4 (accuracy cannot separate).** Every model's Wilson 95% interval contains every other model's point estimate. For 10/12 the interval is [0.55, 0.95], about 0.4 wide, so no ranking by accuracy is possible at n_test = 12.

## Disclosure

Already known before writing: all models scored 10/12 in the existing study, and Part B's distances and shrink factors. No alignment or decision-function value had been computed for this split.
