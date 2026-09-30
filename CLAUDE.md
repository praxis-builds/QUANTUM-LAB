# CLAUDE.md

## Purpose
Local, simulator-only Qiskit/Aer **learning lab** for **quantum computing** (circuits, gates,
algorithms), aimed at cybersecurity: understand the Shor/Grover threat, then bridge to
post-quantum crypto. Workflow for every experiment or lesson:
theory → written prediction → code → result → explain any mismatch.
The repo (code, tests, `results/`) is the source of truth; `docs/history/` is background only.

## Program (main path)
1. Foundations — qubits, interference, phase, entanglement, Grover-2q, noise (lessons 01–06).
2. First quantum algorithms — Deutsch–Jozsa, Bernstein–Vazirani, Simon (lessons 07–10).
3. QFT + phase estimation (lessons 11–12).
4. Shor — factor 15 and 21 on Aer (order finding + classical post-processing).
5. Grover in depth — toy key search; why it only halves key strength.
6. Noise + error-correction basics — 3-qubit bit-flip/phase-flip codes.
7. Bridge to post-quantum crypto — ML-KEM (Kyber); needs a dependency decision first.

Each algorithm = a lesson (script + plain-words doc + test) + a Circuit Playground preset.
The kernel/PSD work is a **completed, frozen study** (`docs/studies/README.md`):
kept, not moved, not extended.

## Hard rules
- Local simulators only. No cloud, no QPU, no provider tokens.
- Never claim quantum advantage.
- Every quantum result needs a fair classical baseline.
- Never hide raw pathologies (e.g. indefinite kernels); report them unrepaired.
- Any repair (PSD projection etc.) must state that it changes the data.
- Seeds, shots and splits must be explicit.
- Don't regenerate existing `results/` files unless asked.
- No new dependencies without asking.
- Commit predictions before running the experiment that tests them (research experiments; lessons may commit their "Predict first" questions and spoilers together).

## Repo map (`src/praxis_quantum_lab/`)
- `state_vectors.py` – NumPy state-vector foundations (no SDK)
- `complex_math.py` – minimal complex ops for those lessons
- `qiskit_experiments.py` – Qiskit/Aer equivalents of the hand-built lessons
- `density_matrices.py` – density matrices and Kraus channels
- `density_matrix_noise.py` – Bell-state Kraus sweeps vs Aer
- `bell_noise_analytics.py` – analytical Bell-noise references
- Frozen kernel/PSD study (see `docs/studies/README.md`):
  - `kernel_experiment.py` – feature map, exact fidelity kernel, classical-vs-quantum comparison
  - `finite_shot_kernel.py` – compute–uncompute shot-noise kernel estimates
  - `finite_shot_psd.py` – PSD diagnostics and transductive repair
- `dashboard_server.py` + `dashboard_assets/` – loopback dashboard (Circuit Playground, Bell Lab, Kernel Observatory); loads Qiskit at start-up (lazy import in a request thread segfaults)
- `circuit_playground.py` – Playground request validation, 1–3 qubit NumPy states, Bloch vectors, presets
- `observatory.py` – read-only raw/clipped/Higham comparison for the Observatory
- `lessons/` (outside `src/`) – lessons 01–06 (foundations), 07–10 (oracles, DJ, BV, Simon) and 11–12 (QFT, phase estimation); script + .md + test each; shared helpers `_grover.py`, `_oracles.py`, `_qft.py` (checked in `tests/test_oracles.py`, `tests/test_qft.py`); see `lessons/README.md`

## Commands (from repo root; use `.venv/bin/python`)
- Setup: `python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]'`
- Tests: `.venv/bin/python -m pytest`
- Verify same-seed reproducibility: `experiments/verify_reproducibility.py`, `verify_repeated_classification.py`, `verify_extended_kernel_evaluation.py`
- Dashboard: `.venv/bin/python -m praxis_quantum_lab.dashboard_server --port 8765` (http://127.0.0.1:8765)

## Conventions
- Basis ordering is `|q1 q0>` (Qiskit little-endian).
- Results are JSON + PNG in `results/`.
- Each experiment has a runner in `experiments/`, a test in `tests/`, and a doc in `docs/`.
