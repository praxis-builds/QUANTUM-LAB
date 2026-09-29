# Expanded kernel evaluation: 5 folds × 10 repeats

## Implemented feature map and kernel

For an already train-split-scaled two-feature input `x=(x0,x1)`, the circuit is
exactly:

```text
|phi(x)> = CZ [RY(x0²) RZ(x0) H ⊗ RY(x1²) RZ(x1) H] |00>.
```

`H`, `RZ(x)`, and `RY(x²)` are applied on each qubit, then a `CZ(0,1)` creates
a fixed entangling phase relation. The quantum kernel is calculated from
exact local statevectors:

```text
K(x, z) = |<phi(x)|phi(z)>|².
```

This lab intentionally evaluates the overlap as `abs(vdot(state_x, state_z))`
squared. It does not claim an additional closed form, because the actual
input-dependent rotations and entangling phase are already directly and
reliably represented by the statevector calculation.

## Evaluation design

The new runner defaults to five stratified folds repeated ten times: 50 paired
splits. Both models receive each identical split. `StandardScaler` is fitted
inside each training fold, then transforms only that fold’s test data. The
classical baseline is a fixed precomputed RBF SVC; the quantum model is a
precomputed exact-statevector fidelity-kernel SVC. No test result influences
scaling, kernel construction, or model selection.

The report gives per-split accuracy, F1, precision, recall, predictions,
confusion matrices, and paired `accuracy_quantum - accuracy_classical` values.
It gives descriptive mean, sample standard deviation, median, and IQR for
accuracy, F1, and paired differences. Repeated folds overlap, so they are not
independent samples: this project reports no naive significance test and makes
no confidence claim from the 50 observations.

## Training-only kernel diagnostics

Every split records diagnostics only for its training Gram matrices:

- Symmetry maximum error checks numerical agreement with `K = K^T`.
- Diagonal values should be near one for self-similarity.
- Minimum eigenvalue checks positive semidefiniteness within `1e-10` tolerance.
- Frobenius cosine similarity and off-diagonal Pearson correlation compare the
  quantum and RBF similarity structures; mean absolute difference gives a
  scale-sensitive complement.

These diagnostics do not use labels and do not measure classification quality
by themselves. A valid PSD kernel can still be unhelpful for this data set, and
a similar kernel matrix does not imply identical decision boundaries.

## Timings and run command

Kernel construction, SVC fitting, and prediction are measured separately.
Quantum-kernel timing is exact local classical statevector-simulation timing;
the RBF baseline is local CPU timing. Neither predicts QPU runtime or proves
any performance advantage.

```bash
.venv/bin/python experiments/run_extended_kernel_evaluation.py
.venv/bin/python experiments/verify_extended_kernel_evaluation.py
```

The first command writes only
`results/classification_extended_5x10_comparison.json` and refuses to replace
it. The runner accepts `--n-splits`, `--n-repeats`, and
`--timing-repetitions`; use a smaller configuration only if the full 5×10 run
cannot finish reliably, and record the completed configuration in the result.
