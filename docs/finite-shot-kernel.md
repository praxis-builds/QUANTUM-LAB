# Finite-shot quantum-kernel study

This experiment measures how finite measurement counts perturb this project's
existing two-qubit fidelity kernel. It keeps the feature map fixed: on each
qubit it applies `H`, `RZ(x_i)`, and `RY(x_i²)`, then applies `CZ(0, 1)`.

## Compute–uncompute estimator

Let `U(x)|00> = |φ(x)>` be the existing feature-map circuit. The experiment
executes `U(x)` first and then `U(z)†`. The resulting all-zero probability is

```text
P(00 | U(z)†U(x)|00>) = |<00|U(z)†U(x)|00>|²
                       = |<φ(z)|φ(x)>|² = K(x, z).
```

Aer displays a measured bit string in Qiskit's `|q1 q0>` order, while the
measurement maps qubit 0 to classical bit 0 and qubit 1 to classical bit 1.
The outcome used by the estimator is the all-zero string, so it is unaffected
by display ordering. Tests compare exact probabilities from this circuit with
the existing statevector kernel on several input pairs.

For `N` shots, the estimate is the number of all-zero counts divided by `N`.
It is an unbiased binomial estimate of the exact probability, with variance
`K(1-K)/N`. Individual seeds need not improve monotonically with shot count;
the report therefore includes each independent seed and summaries across
seeds for each budget.

## Fixed split and comparisons

The default takes a stratified subset of 40 points from the existing seeded
80-point `make_moons` dataset, then makes one stratified 70/30 train/test
split. A `StandardScaler` is fitted on the training points only. The exact
statevector kernel and a fixed RBF SVC are evaluated on this same split.
This design isolates sensitivity to shot sampling on one split. Its test
metrics do not estimate generalization performance across new data or splits.

The default budgets are 128, 512, and 2048 shots, each repeated with five
independent simulator seeds. The CLI exposes sample size, budgets, and seeds.
Kernel circuit execution wall time is recorded separately from SVC fitting
and prediction. These are local classical simulation timings, not quantum
hardware measurements.

## Symmetry and positive semidefiniteness

The training matrix samples each off-diagonal pair once and reflects that
estimate into the opposite triangle. Its diagonal is set to the mathematical
self-kernel value `K(x,x)=1`. Test-to-training estimates form a separate
rectangular matrix and are never reflected into the training kernel.

An exact fidelity kernel is a Gram matrix and is positive semidefinite (PSD).
Finite-shot estimates can introduce eigenvalues below zero, even after the
matrix is made symmetric. The experiment reports the raw minimum eigenvalue
and checks it against a numerical tolerance of `1e-10`; it does not project
the matrix onto the PSD cone. Scikit-learn's precomputed SVC accepts the
sampled matrix in these runs, including potentially indefinite matrices. That
fit succeeding does not turn an indefinite similarity matrix into a valid
Mercer kernel, and its margins and predictions should be interpreted with
that limitation.

## Run and interpret

```bash
.venv/bin/python experiments/run_finite_shot_kernel.py
```

The runner creates
`results/finite_shot_quantum_kernel_comparison.json` and refuses to replace
an existing file. Example configuration overrides:

```bash
.venv/bin/python experiments/run_finite_shot_kernel.py --sample-size 32 --shot-budgets 128 512 --shot-seeds 10 20 30 40 50
```

The result reports train off-diagonal, test-to-training, and combined kernel
MAE/RMSE against exact probabilities; per-seed and aggregate accuracy/F1;
minimum training eigenvalues and PSD counts; and separate local execution,
fit, and prediction times. The exact-kernel and fixed RBF classifiers are
reference points. This is a simulator-based sampling-error study on one
dataset subset and one fixed split; it makes no quantum-advantage claim.
