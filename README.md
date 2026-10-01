# Praxis Quantum Lab: from qubits to post-quantum migration

**What it is.** A local, simulator-only lab that goes from single qubits to Shor's and Grover's algorithms, error correction, quantum key distribution and NIST's post-quantum standards. Each step is a short lesson you can run and test. It ends in a practical tool: **`pq_inventory`**, a read-only scanner that finds quantum-vulnerable cryptography in code and configuration and turns it into a prioritised migration plan.

**What it demonstrates.**
- How Shor's period finding breaks RSA (a toy 5-bit key is recovered from its public key on local Aer), and why the same idea threatens elliptic curves.
- How Grover's search only *weakens* symmetric crypto (a measured square-root scaling on toy sizes), and why AES-256 remains safe.
- Why real attacks need error-corrected machines (noise experiments, repetition and Shor codes, thresholds), tied to published RSA-2048 resource estimates.
- What BB84 quantum key distribution does and doesn't give you, and why security agencies favour post-quantum cryptography.
- ML-KEM, ML-DSA and a hybrid X25519 + ML-KEM-768 exchange through liboqs, with sizes and timings against RSA and elliptic curves.
- A consulting-style case study: inventory, risk classes, a Mosca-based roadmap and a before/after diff ([`docs/case-study.md`](docs/case-study.md)).

**Honest limits.** Everything quantum runs on a **classical simulator** (Qiskit Aer) on a laptop: no cloud, no quantum hardware, no provider tokens. **No quantum advantage is claimed anywhere.** Every quantum result sits next to an honestly counted classical baseline, and at these toy sizes the classical method usually wins. The toy RSA keys, ciphers and hashes are for teaching only. Resource estimates for real attacks are quoted from published papers with sources and years, and unverified figures are marked as such.

## Program map

| Step | Topic | Where |
|---|---|---|
| 1 | Foundations: qubits, interference, phase, entanglement, Grover on 2 qubits, noise | [`lessons/`](lessons/README.md) 01–06 |
| 2 | First quantum algorithms: oracles, Deutsch–Jozsa, Bernstein–Vazirani, Simon | 07–10 |
| 3 | Quantum Fourier transform and phase estimation (the engine of Shor) | 11–12 |
| 4 | Shor: factor 15 and 21 on Aer; break a toy RSA key | 13–16 |
| 5 | Grover in depth: toy key search, hash preimages, why it only halves key strength | 17–20 |
| 6 | Noise and error correction: bit-flip, phase-flip and Shor's 9-qubit codes, thresholds | 21–25 |
| 7 | Quantum security: BB84, intercept-resend, key distillation, quantum randomness | 26–29 |
| 8 | Post-quantum cryptography: why RSA/ECC must go, ML-KEM, hybrid key exchange, ML-DSA (plus a C demo via liboqs) | 30–33, [`lessons/c/`](lessons/c/README.md) |
| → | **Crypto-inventory scanner** and a case study | [`tools/pq_inventory`](docs/pq-inventory.md), [`examples/warehouse-demo`](examples/warehouse-demo/README.md) |

Each lesson is a script, a plain-words page with "Predict first" questions and a spoiler, and a test. The local dashboard has a Circuit Playground with presets for most algorithms, plus a **Security Lab** tab (live BB84, toy RSA break, Grover key search, Mosca calculator).

## Quick start

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e '.[dev]'           # core: lessons 01-30, dashboard, scanner (without key parsing)
.venv/bin/pip install -e '.[dev,pqc]'       # optional: lessons 31-33 and certificate/key parsing
                                            # (needs the liboqs C library: docs/DECISIONS.md, D1)
.venv/bin/python -m pytest                  # post-quantum tests skip cleanly without the extra
.venv/bin/python lessons/16_toy_rsa_break.py
.venv/bin/python -m praxis_quantum_lab.dashboard_server --port 8765   # http://127.0.0.1:8765
```

## Scanner usage

```bash
python -m pq_inventory scan path/to/code --out reports/            # JSON, HTML, Markdown, CycloneDX CBOM
python -m pq_inventory scan path/to/code --out reports/ --systems systems.json   # Mosca roadmap per system
python -m pq_inventory scan path/to/code --out reports/ --fail-on quantum-broken # exit 1 for CI
python -m pq_inventory diff before/scan.json after/scan.json --out progress/    # fixed / new / unchanged
```

Exit codes (the same for `scan` and `diff`):

| Code | Meaning |
|---|---|
| 0 | Done; no `--fail-on` threshold reached |
| 1 | A finding at the `--fail-on` level **or worse** (order: CLASSICALLY-BROKEN > QUANTUM-BROKEN > QUANTUM-WEAKENED); for `diff`, a *new* finding |
| 2 | Usage or input error (bad option, missing path, malformed `scan.json` or systems config, `--out` not a directory) |
| 3 | Nothing was scanned (empty tree, only skipped files, symlinked root): never a pass |
| 4 | Internal error (a bug; please report it) |

Read-only and offline: no network code, nothing written outside `--out`, symlinks never followed, private keys reported by type and size only, and no source text in any output. Details, risk classes, rule format and honest accuracy numbers: [`docs/pq-inventory.md`](docs/pq-inventory.md). Every non-obvious choice in this build is logged in [`docs/DECISIONS.md`](docs/DECISIONS.md); the final review is [`docs/REVIEW.md`](docs/REVIEW.md).

## Completed study: classical vs quantum-kernel classification (frozen)

The lab began as a kernel study: a classical RBF classifier against a quantum-kernel classifier on one small data set, followed by finite-shot and PSD-repair experiments. That study is **complete and frozen**: its code, results, tests and docs stay as they are and are not extended. The index is [`docs/studies/README.md`](docs/studies/README.md). The sections below describe it and the shared foundations.

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

The [local dashboard](docs/dashboard.md) provides a live Circuit Playground (1–3 qubits), a live Bell Lab and a saved-result
Kernel Observatory (raw, clipped and Higham kernels) using the existing environment. Start it from the project root:

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

## Stages and study path (foundations + frozen kernel study)

1. **Foundations from scratch** — inspect the NumPy implementation, manually alter an amplitude, and run the state-vector tests.
2. **Circuit equivalents** — inspect the four circuit constructors and compare exact statevector probabilities with finite-shot Aer counts and noisy Aer.
3. **Density matrices and noise** — compare a hand-applied Kraus channel with the exact same local Aer Kraus instruction.
4. **Kernel evaluation** — read the report metadata before comparing accuracy, precision, recall, F1, training time, inference time, and confusion matrix.
5. **Repeated evaluation** — use the paired repeated-split report before drawing a conclusion from one held-out split.
6. **Analytical validation** — derive the implemented Bell-channel limits before trusting a simulator agreement.
7. **Expanded descriptive evaluation** — use the 5×10 paired report and training-only kernel diagnostics without treating overlapping folds as independent evidence.
8. **Finite-shot kernel study** — compare compute–uncompute estimates with the existing exact kernel on one fixed split and inspect sampling error and PSD changes.
9. **PSD repair study** — compare raw finite-shot kernels with a transductively repaired full-subset kernel; read the scope caveat before interpreting classifier metrics.
10. **Kernel rank and PSD violation** — read the pre-registered predictions in `docs/kernel-rank-prediction.md`, then compare them with `results/kernel_rank_prediction.json` to see why raw kernels are indefinite when rank < n.
11. **Per-eigenvalue negativity** — compare the pre-registered first-order prediction in `docs/eigenvalue-negativity-prediction.md` with `results/eigenvalue_negativity_calibration.png`, and see why it is biased and where second order helps.
12. **Higham vs clipping** — read `docs/higham-vs-clipping.md` to see why eigenvalue clipping plus rescaling moves saved finite-shot kernels *away* from the exact kernel, while Higham's nearest-correlation repair moves them closer. Both repairs change the data.
13. **Metrics that separate models** — read `docs/repair-metric-comparison.md`: all models tie at 10/12 accuracy, but kernel alignment and decision-function correlation still separate RBF, raw, clipped and Higham kernels.
14. **Out-of-sample second-order test** — `docs/second-order-negativity-test.md` freezes the post-hoc second-order eigenvalue model, pre-registers pass/fail thresholds, and tests it on unseen subsets, sizes and shot counts, with near-degenerate kernels reported separately.
15. **Repeated-split model comparison** — `docs/repeated-model-comparison.md` compares RBF, exact, raw, clipped and Higham (transductive and inductive) kernels over 50 splits, with paired cluster-bootstrap CIs. RBF wins on accuracy, and repairs only move decision correlation and alignment.
16. **Kernel concentration** — `docs/kernel-concentration.md` shows the final CZ chain cancels in the kernel, and that with two input features, adding qubits or layers narrows the kernel's bandwidth rather than producing Haar-like concentration.

The experiment guide explains every circuit and the comparison protocol. See [density-matrix notes](docs/density-matrices.md), [analytical Bell-noise validation](docs/bell-noise-analytical-validation.md), [repeated-kernel notes](docs/repeated-kernel-comparison.md), [expanded kernel evaluation](docs/extended-kernel-evaluation.md), [finite-shot kernel study](docs/finite-shot-kernel.md), and [finite-shot PSD repair](docs/finite-shot-psd-repair.md) for later milestones. The learning log is an editable record of progress and open questions. The security directions document deliberately discusses future relevance without turning this first lab into a cryptography implementation.
