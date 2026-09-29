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

---

# Results (added after running; everything above is unchanged)

Artifacts: `results/repair_metric_comparison.json`, `results/repair_metric_comparison.png`. Runner: `experiments/run_repair_metric_comparison.py` (~3.5 s; rerun byte-identical). The source `results/finite_shot_kernel_psd_repair.json` is read only (md5 unchanged). Repairs are **transductive and change the data**.

Means over 5 replicates (min in brackets):

| shots | alignment raw | clipped | Higham | Pearson r raw | clipped | Higham | sign agreement (all three) | accuracy (all three) |
|---|---|---|---|---|---|---|---|---|
| 128 | 0.99795 [0.99759] | 0.99854 | 0.99913 | 0.9929 [0.9882] | 0.9977 | 0.9980 | 12/12 | 10/12 |
| 512 | 0.99949 | 0.99962 | 0.99976 | 0.9973 | 0.9988 | 0.9992 | 12/12 | 10/12 |
| 2048 | 0.99988 | 0.99991 | 0.99994 | 0.9995 | 0.9997 | 0.9998 | 12/12 | 10/12 |

References: exact SVC 10/12, Wilson 95% [0.552, 0.953]. **RBF (classical):** alignment to exact **0.9622**, Pearson r **0.975**, sign agreement 12/12, accuracy 10/12.

Per-matrix orderings (15 matrices): alignment clipped > raw 15/15 and Higham > clipped 15/15. Pearson r clipped > raw 15/15, Higham > clipped 13/15, Higham > raw 14/15.

## Prediction vs observed

| # | Prediction | Observed | Verdict |
|---|---|---|---|
| C-P1 | quantum-variant alignment ≥ 0.995 (≥ 0.999 at 2048); spread < 0.003; Higham highest ≥ 12/15; clipping not systematically above raw | min 0.9976, ≥ 0.99987 at 2048; max spread 0.0012; Higham highest **15/15**. But clipping > raw in **15/15**. | Confirmed except the clipping clause, which was **wrong** |
| C-P2 | RBF alignment < 0.97, clearly below every quantum variant | 0.962 vs ≥ 0.9976 | Confirmed |
| C-P3 | r ≥ 0.9 at 128 and ≥ 0.98 at 2048; sign ≥ 10/12 and ≥ 11/12; no consistent raw/clip/Higham winner; RBF r < 0.95 | r ≥ 0.988 at 128 and ≥ 0.9991 at 2048; sign 12/12 everywhere; mean r differences < 0.005 but **consistently ordered** Higham > clipped > raw; RBF r = **0.975** | Thresholds confirmed; "no winner" **wrong**; RBF r **wrong** |
| C-P4 | accuracy cannot separate: every Wilson interval contains every point estimate | All 47 models (exact, RBF, 45 finite-shot) score exactly 10/12, with identical intervals [0.55, 0.95] | Confirmed |

## Explanation of mismatches

1. **Clipping beats raw on alignment and r, yet is further from exact in Frobenius norm (Part B).** Both of these metrics are scale invariant. Clipping's main distortion is a near-uniform shrink of off-diagonal entries (Part B), and alignment and Pearson r are almost blind to that, so they only see the negative-direction noise it removes. **"Closer to exact" depends on the metric.** Frobenius distance penalises the shrink, while alignment and decision correlation do not. Higham wins on all three.
2. **A consistent ordering, even though the differences are tiny.** I expected noise to scramble the ordering at differences below 0.02. Instead, removing negative-eigenvalue noise is a systematic improvement, so it orders the models in almost every replicate even at the 1e-3 level. Whether a 1e-3 difference in r matters for anything downstream is not shown here. On this split it changes no prediction.
3. **RBF decisions correlate with exact more than predicted (0.975).** On 2-D moons with training-set scaling, both kernels are smooth, local similarity measures, and the SVCs produce the same predictions on all 12 test points. So the RBF baseline is separated by alignment (0.962, a different kernel geometry) and less strongly by r. It is not separated at all by sign or accuracy.

## What separates the models, and what doesn't

- **Separates:** training-block alignment and decision-function Pearson r. They separate RBF from every quantum variant, finite-shot from exact (monotone in shots), and Higham > clipped > raw.
- **Does not separate:** sign agreement and accuracy (all 12/12 and 10/12). With 12 test points the Wilson interval is about 0.4 wide, so accuracy could not distinguish these models even if they differed by several points.
- None of this is evidence that any quantum kernel is better than the classical baseline. It measures closeness to the exact quantum model only. One split, one data family, no hardware noise.
