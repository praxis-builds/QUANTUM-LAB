# Praxis Quantum Lab 01 — Classical vs Quantum-Kernel Classification

Praxis Quantum Lab is a local, simulator-only learning and research project. It starts with the mathematics of state vectors, recreates the ideas in Qiskit, then compares a classical classifier with a quantum-kernel classifier on one small, reproducible binary data set. It is designed for a laptop, not a cloud account or quantum hardware.

## What quantum computing means here

A **classical bit** has one definite value: `0` or `1`. A **qubit** is described by a normalized complex state vector:

```text
|ψ⟩ = α|0⟩ + β|1⟩, where |α|² + |β|² = 1.
```

The coefficients `α` and `β` are **amplitudes**, not directly observable probabilities. **Superposition** means both amplitudes can be nonzero before measurement. The Born rule turns them into probabilities: measurement returns `0` with probability `|α|²` and `1` with probability `|β|²`, then the state is observed in a definite basis state.

**Quantum gates** are linear transformations of state vectors. This project implements Hadamard (`H`) and the Pauli `X`, `Y`, and `Z` gates directly with NumPy before showing corresponding Qiskit circuits. A Hadamard applied to `|0⟩` creates the equal-amplitude state `(|0⟩ + |1⟩)/√2`.

For multiple qubits, tensor products produce a state space whose dimension grows as `2ⁿ`. **Entanglement** is a joint state that cannot be written as a tensor product of independent single-qubit states. The Bell state `(|00⟩ + |11⟩)/√2` has correlated measurement outcomes even though each individual qubit looks random.

Real devices are affected by **noise**: imperfect gates, decoherence, and readout error. The Aer lesson includes a small local depolarizing-noise model so its output can be compared to an ideal statevector calculation. It is a teaching model, not a calibration of a physical device.

## Why a classical baseline is mandatory

A **quantum kernel** maps an input `x` through a quantum feature map `|φ(x)⟩`, then measures sample similarity by fidelity:

```text
K(x, z) = |⟨φ(x)|φ(z)⟩|².
```

An SVC can use that precomputed similarity matrix just as it can use a classical kernel. In this lab, the comparison uses the same data, stratified train/test split, labels, and evaluation metrics for both models. The classical RBF SVC is not optional: without it, a quantum score has no meaningful local reference point.

This project does **not** demonstrate quantum advantage, production-ready machine learning, a superior feature map, or performance on quantum hardware. The quantum kernel is calculated by an exact classical statevector simulator; the time includes classical simulation overhead and does not predict runtime on a future quantum processor.

## Project layout

```text
src/praxis_quantum_lab/
  complex_math.py          # complex amplitudes and |z|²
  state_vectors.py         # NumPy state-vector foundations and seeded sampling
  qiskit_experiments.py    # ideal and noisy local Qiskit Aer circuits
  density_matrices.py      # density matrices, Kraus channels, qubit ordering
  density_matrix_noise.py  # Bell-state custom-versus-Aer channel sweep
  kernel_experiment.py     # fair classical vs quantum-kernel comparison
tests/                     # focused unit tests
experiments/               # runnable scripts, separate from reusable code
docs/                      # learning log, experiment guide, future directions
notebooks/                 # reserved for guided, exploratory lessons
results/                   # generated JSON reports and PNG figures
```

## Local setup (Windows + WSL)

The [local dashboard](docs/dashboard.md) provides a live Bell Lab and a saved-result
Kernel Observatory using the existing environment. Start it from the project root:

```bash
.venv/bin/python -m praxis_quantum_lab.dashboard_server --port 8765
```

Open **http://127.0.0.1:8765**. It binds only to loopback; Ctrl+C stops it.
Opening the page does not start a simulation.

The reference environment is Ubuntu 24.04 under WSL with Python 3.12.3. No provider token, cloud service, IBM Quantum account, GPU, or quantum hardware is used.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
```

Direct pins live in `pyproject.toml`: NumPy 2.5.3, scikit-learn 1.9.1, Qiskit 2.5.2, Qiskit Aer 0.17.2, matplotlib 3.11.2, and pytest 9.1.1 (development extra). `requirements.lock` records the resolved local environment used for the first run.

## Run and verify

Run these from the project folder in WSL:

```bash
.venv/bin/python -m pytest
.venv/bin/python experiments/run_qiskit_examples.py
.venv/bin/python experiments/run_classification.py
.venv/bin/python experiments/verify_reproducibility.py
.venv/bin/python experiments/run_density_matrix_noise_sweep.py
.venv/bin/python experiments/run_repeated_classification.py
.venv/bin/python experiments/verify_repeated_classification.py
.venv/bin/python experiments/run_analytical_bell_noise_validation.py
.venv/bin/python experiments/run_extended_kernel_evaluation.py
.venv/bin/python experiments/run_finite_shot_kernel.py
.venv/bin/python experiments/run_finite_shot_psd_repair.py
```

The Qiskit run writes exact probabilities, ideal sampled counts, noisy sampled counts, and two histograms. The comparison writes metrics, timing, confusion matrices, feature-map metadata, and predictions to `results/classification_comparison.json`.

For a clean-environment check, create a new empty virtual environment and run the same editable install followed by `python -m pytest`; do not reuse the existing `.venv` for that check. See the verification commands in `docs/experiment-guide.md`.

## Stages and study path

1. **Foundations from scratch** — inspect the NumPy implementation, manually alter an amplitude, and run the state-vector tests.
2. **Circuit equivalents** — inspect the four circuit constructors and compare exact statevector probabilities with finite-shot Aer counts and noisy Aer.
3. **Density matrices and noise** — compare a hand-applied Kraus channel with the exact same local Aer Kraus instruction.
4. **Kernel evaluation** — read the report metadata before comparing accuracy, precision, recall, F1, training time, inference time, and confusion matrix.
5. **Repeated evaluation** — use the paired repeated-split report before drawing a conclusion from one held-out split.
6. **Analytical validation** — derive the implemented Bell-channel limits before trusting a simulator agreement.
7. **Expanded descriptive evaluation** — use the 5×10 paired report and training-only kernel diagnostics without treating overlapping folds as independent evidence.
8. **Finite-shot kernel study** — compare compute–uncompute estimates with the existing exact kernel on one fixed split and inspect sampling error and PSD changes.
9. **PSD repair study** — compare raw finite-shot kernels with a transductively repaired full-subset kernel; read the scope caveat before interpreting classifier metrics.

The experiment guide explains every circuit and the comparison protocol. See [density-matrix notes](docs/density-matrices.md), [analytical Bell-noise validation](docs/bell-noise-analytical-validation.md), [repeated-kernel notes](docs/repeated-kernel-comparison.md), [expanded kernel evaluation](docs/extended-kernel-evaluation.md), [finite-shot kernel study](docs/finite-shot-kernel.md), and [finite-shot PSD repair](docs/finite-shot-psd-repair.md) for later milestones. The learning log is an editable record of progress and open questions. The security directions document deliberately discusses future relevance without turning this first lab into a cryptography implementation.
