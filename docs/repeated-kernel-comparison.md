# Repeated paired kernel comparison

The original `classification_comparison.json` remains the first single split.
The repeated experiment adds a separate result file so one favorable or
unfavorable split is not over-interpreted.

## Protocol

`RepeatedStratifiedKFold` makes the same six default train/test splits (three
folds, repeated twice) available to both models. On every split,
`StandardScaler` is fit only on training features, then transforms that split’s
test features. This prevents test-set information leaking into either kernel.

The classical baseline uses a precomputed RBF kernel and the quantum model uses
the existing exact statevector fidelity kernel. Both are fitted by
`SVC(kernel="precomputed")`, which lets the report time train-kernel
construction, test-kernel construction, SVC fitting, and prediction separately.

The report contains per-split accuracy, precision, recall, F1, confusion
matrix, predictions, and timings. It also includes mean and sample standard
deviation across splits, plus the paired quantity:

```text
accuracy_quantum_kernel - accuracy_classical_RBF
```

Positive values on a small local experiment do not show quantum advantage; a
quantum kernel here is calculated by a classical exact statevector simulator.

## Timing

One unmeasured warm-up runs before timing. The default one timing repetition is
practical for a laptop and labels every number as a local simulator wall-clock
observation. Use three or more repetitions for a more stable timing study:

```bash
.venv/bin/python experiments/run_repeated_classification.py --timing-repetitions 3
```

This increases runtime proportionally. It still does not predict QPU runtime,
which would involve compilation, shots, queueing, and hardware noise.

## Run and reproduce

```bash
.venv/bin/python experiments/run_repeated_classification.py
.venv/bin/python experiments/verify_repeated_classification.py
```

The default runner writes `results/classification_repeated_comparison.json` and
refuses to replace it. Change no parameters when checking same-seed
reproducibility; timing values are excluded because wall-clock measurements
are intentionally nondeterministic.
