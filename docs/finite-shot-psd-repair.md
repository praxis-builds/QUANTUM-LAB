# Finite-shot kernel PSD violations and spectral repair

This follow-up reuses the original seeded 80-point `make_moons` source data,
stratified 40-point subset, fixed 28/12 split, existing two-qubit feature map,
shot budgets (128, 512, 2048), and five simulator seeds. It measures all 780
unique pairs among the ordered train-plus-test subset for every budget/seed.
The same measured pair values make both the raw and repaired matrices.

## Why exact and sampled kernels differ

For feature states `|φ(x_i)>`, an exact fidelity kernel has entries
`K_ij = |<φ(x_i)|φ(x_j)>|²`. It is a Gram matrix: it can be represented as
inner products of the states' rank-one projectors, so for any vector `c`,
`c†Kc = tr[(Σ_i c_i |φ_i><φ_i|)†(Σ_j c_j |φ_j><φ_j|)] >= 0` (with the usual
complex-conjugate coefficient convention). Thus it is positive semidefinite.

The finite-shot compute–uncompute estimator independently samples each
pair's all-zero probability. Reflecting one sampled triangle makes the matrix
symmetric, and setting the diagonal to its exact self-kernel value makes every
diagonal entry one. Those operations do not impose the cross-entry constraints
required of a Gram matrix, so the raw symmetric matrix can still have negative
eigenvalues.

## Repair and its tradeoff

For raw symmetric `K = V diag(λ) Vᵀ`, the experiment clips eigenvalues,
`λ_i⁺ = max(λ_i, 0)`, and reconstructs
`K₊ = V diag(λ⁺) Vᵀ`. It then divides each entry by the square root of the
corresponding reconstructed diagonal values and sets the diagonal to one.
The result is symmetric, PSD up to floating-point tolerance, and unit
diagonal. The report includes the full Frobenius distance `||K_repaired -
K_raw||_F` and diagnostics for both matrices. Eigenvalue clipping followed
by rescaling is a simple spectral repair; it is not guaranteed to be the
nearest correlation matrix. It trades fidelity to measured pair values for
satisfying the PSD condition needed by a conventional kernel interpretation.
It is post-processing of simulated estimates, not quantum error mitigation.

## Evaluation scope

The raw classifier uses the raw train/train and test/train blocks from the
sampled matrix. The repaired classifier uses blocks of a repaired matrix
formed from all 40 unlabeled inputs, including the held-out test inputs. No
test labels enter repair, but this makes repaired evaluation **transductive**;
it is not directly comparable to a standard inductive held-out result. The
exact statevector kernel and fixed RBF SVC remain reference baselines on the
same fixed split. Metrics describe this dataset and split only.

The JSON keeps each raw sampled matrix unchanged beside its repaired copy,
per-seed metrics, matrix diagnostics, Frobenius distances, and per-budget
summaries. The plot compares the mean raw and repaired minimum eigenvalues
against the zero PSD boundary. All circuit timings are local Aer simulation
timings; the study makes no quantum-advantage claim.

## Default run findings

Across the five seeds at each budget, all 15 raw matrices violated the PSD
tolerance and all 15 repaired matrices passed it. The average minimum
eigenvalue and Frobenius change were:

| Shots | Raw minimum eigenvalue | Repaired minimum eigenvalue | Mean Frobenius change |
|---:|---:|---:|---:|
| 128 | −0.3571 | −2.23 × 10⁻¹⁵ | 1.5838 |
| 512 | −0.1784 | −2.57 × 10⁻¹⁵ | 0.7916 |
| 2048 | −0.0892 | −2.45 × 10⁻¹⁵ | 0.3709 |

Raw, repaired-transductive, exact-kernel, and RBF classifiers all scored 0.833
accuracy and 0.833 F1 on this one 12-point test set. This result shows the
repair changed the matrix geometry substantially at lower shot counts while
not changing these particular predictions; it does not establish comparable
behavior on another split or dataset.

## Run

```bash
.venv/bin/python experiments/run_finite_shot_psd_repair.py
```

It writes new files `results/finite_shot_kernel_psd_repair.json` and
`results/finite_shot_kernel_psd_repair_min_eigenvalues.png`, and refuses to
overwrite either one.
