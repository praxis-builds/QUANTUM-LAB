# Learning log — Lab 01

This is intentionally a working document. Update the “confused me” and “next” sections after each hands-on session rather than treating a passing test as understanding.

## What I built

- A small NumPy state-vector layer with visible complex amplitudes, normalization, Pauli/Hadamard gates, tensor products, and seeded sampling.
- Equivalent local Qiskit circuits for superposition, measurement, entanglement, Bell states, exact statevectors, ideal samples, and noisy Aer samples.
- One controlled classical RBF SVC versus exact statevector quantum-kernel SVC comparison, including timing and classification metrics.
- Tests and reproducibility checks that make a repeated same-seed result inspectable.

## What I understood

- Amplitudes can be complex; their squared magnitudes become probabilities.
- Normalization preserves the rule that all mutually exclusive measurement probabilities sum to one.
- A Hadamard changes a basis state into a superposition, while a CNOT after a Hadamard can create a Bell state with correlated outcomes.
- A kernel is a similarity measure. A quantum kernel changes how similarity is defined; it does not automatically make a classifier better.
- A simulator is a classical program. Exact statevector simulation is useful for learning but scales exponentially with qubit count.

## What confused me or needs deliberate follow-up

- Global phase does not change measurement probabilities, but relative phase can change a later gate’s outcome. Verify this by adding a `Z` between two Hadamards.
- Qiskit’s displayed bit order can differ from the mental ordering used in a hand-written tensor product. Reconcile it with small basis-state experiments.
- An ideal kernel matrix is positive semidefinite in theory; learn how finite shots and hardware noise can make estimated kernels numerically troublesome.
- Timing an exact simulator is not timing a QPU. Identify what would be different for circuit compilation, repeated shots, queueing, and mitigation.

## What each experiment demonstrated

| Experiment | Demonstration |
|---|---|
| NumPy H, X, Y, Z tests | Gate matrices act predictably on one-qubit vectors. |
| Seeded sampling | Pseudorandom measurement samples can be reproduced exactly. |
| One-qubit Aer measurement | A superposition produces frequencies near Born-rule probabilities. |
| Bell state | Entanglement produces correlated `00`/`11` outcomes. |
| Noisy Bell Aer run | A simple noise channel can degrade ideal correlations. |
| Kernel comparison | Same-split metrics, not intuition, decide which model performed better in this setup. |
| Kraus Bell sweep | A density-matrix channel and Aer agree when they use the same operators and qubit ordering. |
| Repeated kernel comparison | Paired split differences give more context than a single held-out split. |

## What to study next

1. Derive matrix representations of controlled gates and compare them with Qiskit’s little-endian convention.
2. Study density matrices, mixed states, and Kraus noise channels.
3. Compare this fixed feature map with at least one simple classical polynomial kernel before changing data size or tuning hyperparameters.
4. Learn statistical evaluation: repeated stratified splits, confidence intervals, and avoiding test-set-driven model selection.
5. Study the computational limits of statevector simulation before increasing the number of qubits.
6. Compare density-matrix noise on both qubits and explain why independently applying a local channel differs from one two-qubit correlated-noise channel.
