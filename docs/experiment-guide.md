# Experiment guide and verification protocol

## Stage 1: state vectors without a quantum SDK

`complex_math.py` keeps the probability rule explicit: `magnitude_squared(z)` computes `z* z` with a complex conjugate. `state_vectors.py` builds normalized vectors, applies visible 2×2 gate matrices, uses `np.kron` for tensor products, and samples with `numpy.random.default_rng(seed)`. The test suite checks normalization, non-negative probabilities summing to one, all four gate behaviours, two-qubit tensor dimensions, and deterministic measurements.

This layer is intentionally limited to state-vector concepts; it does not hide linear algebra behind Qiskit.

## Stage 2: local Qiskit circuit experiments

Run `python experiments/run_qiskit_examples.py`. It writes the observed values to `results/qiskit_experiments.json` so the documentation never substitutes an assumed value for a run result.

| Experiment | Circuit | Expected ideal result | Observed result recorded | Noise interpretation |
|---|---|---|---|---|
| One-qubit superposition | `H(0)` | Exact probabilities `P(0)=P(1)=0.5` | Statevector probabilities | No noise is applied to this exact calculation. |
| One-qubit measurement | `H(0); measure` | Counts near 50/50 at finite shots | Aer statevector count map | Finite-shot variation is sampling uncertainty, not hardware noise. |
| Two-qubit entanglement | `H(0); CX(0,1)` | Exact probabilities only for `00` and `11`, each 0.5 | Statevector probabilities | No noise is applied to this exact calculation. |
| Bell measurement, ideal | `H(0); CX(0,1); measure` | Only `00` and `11` counts | Ideal Aer count map | Finite shots can make the two allowed counts unequal. |
| Bell measurement, noisy | Same Bell circuit on Aer density matrix | Dominant correlated outcomes, with possible errors | Noisy Aer count map | Local depolarizing error after `H`/`CX` can corrupt the correlation and introduce `01`/`10`. |

The exact backend is `qiskit.quantum_info.Statevector`. Ideal finite-shot runs use local `AerSimulator(method="statevector")`; noisy runs use local `AerSimulator(method="density_matrix")` plus a small depolarizing noise model. Neither path creates a provider connection.

## Stage 3: fair comparison protocol

The data set is 80 samples from `sklearn.datasets.make_moons` with deterministic noise and a stratified 70/30 split. The classical model is `StandardScaler + SVC(kernel="rbf")`. The quantum path fits a scaler on the training data only, creates a two-qubit circuit per sample, calculates exact statevectors, builds the fidelity kernel, and fits `SVC(kernel="precomputed")`.

Both classifiers receive the same split. The report always records seed, dataset/train/test size, class balance, circuit depth, qubit count, simulator type, predictions, accuracy, precision, recall, F1, train time, inference time and the confusion matrix. Times are useful operational observations but not a fair speed contest: the quantum-kernel time includes classical statevector simulation and kernel construction.

The feature map is deliberately shallow:

```text
for each of two scaled features xᵢ: H(i), RZ(xᵢ), RY(xᵢ²)
then: CZ(0, 1)
```

This gives a concrete nonlinear embedding and entangling operation, but it is not optimized. A lower quantum score is an honest outcome, not a failed run.

## Verification commands

From the WSL project directory:

```bash
.venv/bin/python -m pytest
.venv/bin/python -c "import praxis_quantum_lab, qiskit, qiskit_aer, sklearn"
.venv/bin/python experiments/run_qiskit_examples.py
.venv/bin/python experiments/run_classification.py
.venv/bin/python experiments/verify_reproducibility.py
```

For the clean-environment setup check, create a separate, disposable local environment (do not delete an environment containing useful work):

```bash
python3 -m venv .venv-clean-check
.venv-clean-check/bin/python -m pip install --upgrade pip
.venv-clean-check/bin/python -m pip install -e '.[dev]'
.venv-clean-check/bin/python -m pytest
```

After checking, the disposable `.venv-clean-check` can be removed manually if you no longer need it. It is not needed for ordinary runs.
