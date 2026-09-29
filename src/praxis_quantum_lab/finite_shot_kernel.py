"""Finite-shot compute-uncompute estimates for the existing fidelity feature map.

All circuits run on a local Qiskit Aer statevector simulator with measurements.
The states are classically simulated; this module measures sampling sensitivity,
not quantum-device performance.
"""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator
from sklearn.metrics import accuracy_score, f1_score
from sklearn.metrics.pairwise import rbf_kernel
from sklearn.model_selection import StratifiedShuffleSplit, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from praxis_quantum_lab.kernel_experiment import (
    DEFAULT_DATASET_SIZE,
    DEFAULT_SEED,
    feature_statevectors,
    fidelity_quantum_kernel,
    make_dataset,
    quantum_feature_map,
)

DEFAULT_SAMPLE_SIZE = 40
DEFAULT_TEST_FRACTION = 0.30
DEFAULT_SHOT_BUDGETS = (128, 512, 2048)
DEFAULT_SHOT_SEEDS = (20260929, 20260930, 20260931, 20260932, 20260933)
FINITE_SHOT_RESULT_FILENAME = "finite_shot_quantum_kernel_comparison.json"
PSD_TOLERANCE = 1e-10


def compute_uncompute_circuit(x: np.ndarray, z: np.ndarray) -> QuantumCircuit:
    """Return U(z)†U(x)|00>, measured into matching classical-bit indices.

    The project feature map uses two qubits. Qiskit displays counts in
    ``|q1 q0>`` order, but the all-zero outcome is invariant under that display
    order. The circuit order is important: ``U(x)`` is applied first, then
    ``U(z).inverse()``, giving amplitude ``<0|U(z)†U(x)|0>``.
    """
    x_circuit = quantum_feature_map(x)
    z_inverse = quantum_feature_map(z).inverse()
    circuit = QuantumCircuit(x_circuit.num_qubits, x_circuit.num_qubits, name="compute_uncompute")
    circuit.compose(x_circuit, inplace=True)
    circuit.compose(z_inverse, inplace=True)
    circuit.measure(range(circuit.num_qubits), range(circuit.num_qubits))
    return circuit


def exact_compute_uncompute_probability(x: np.ndarray, z: np.ndarray) -> float:
    """Return exact all-zero probability, independently via circuit evolution."""
    circuit = compute_uncompute_circuit(x, z).remove_final_measurements(inplace=False)
    probabilities = Statevector.from_instruction(circuit).probabilities_dict()
    return float(probabilities.get("0" * circuit.num_qubits, 0.0))


def estimate_compute_uncompute_probability(
    x: np.ndarray,
    z: np.ndarray,
    *,
    shots: int,
    seed: int,
    simulator: AerSimulator | None = None,
) -> float:
    """Sample one compute-uncompute circuit on local Aer and return p(00)."""
    if not isinstance(shots, int) or shots < 1:
        raise ValueError("shots must be a positive integer.")
    backend = simulator or AerSimulator(method="statevector")
    compiled = transpile(compute_uncompute_circuit(x, z), backend, seed_transpiler=seed)
    result = backend.run(compiled, shots=shots, seed_simulator=seed).result()
    counts = result.get_counts()
    return float(counts.get("0" * compiled.num_qubits, 0) / shots)


def training_kernel_diagnostics(kernel: np.ndarray) -> dict[str, Any]:
    """Report symmetry, exact diagonal, and unmodified minimum eigenvalue."""
    matrix = np.asarray(kernel, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1] or matrix.size == 0:
        raise ValueError("training kernel must be a non-empty square matrix.")
    symmetric_for_eigenvalue = (matrix + matrix.T) / 2.0
    minimum_eigenvalue = float(np.linalg.eigvalsh(symmetric_for_eigenvalue).min())
    symmetry_error = float(np.max(np.abs(matrix - matrix.T)))
    return {
        "symmetry_max_abs_error": symmetry_error,
        "diagonal_values": np.diag(matrix).astype(float).tolist(),
        "minimum_eigenvalue": minimum_eigenvalue,
        "psd_tolerance": PSD_TOLERANCE,
        "positive_semidefinite_within_tolerance": minimum_eigenvalue >= -PSD_TOLERANCE,
        "eigenvalue_note": (
            "Computed from the symmetric part for numerical stability; the stored kernel is "
            "unchanged and no PSD projection is applied."
        ),
    }


def _make_fixed_split(
    *, sample_size: int, seed: int, test_fraction: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[int]]:
    if not isinstance(sample_size, int) or sample_size < 20:
        raise ValueError("sample_size must be an integer of at least 20.")
    if sample_size > DEFAULT_DATASET_SIZE:
        raise ValueError(f"sample_size cannot exceed the source dataset size ({DEFAULT_DATASET_SIZE}).")
    if not 0.1 <= test_fraction <= 0.5:
        raise ValueError("test_fraction must be between 0.1 and 0.5.")
    full_x, full_y = make_dataset(seed=seed)
    subset = StratifiedShuffleSplit(n_splits=1, train_size=sample_size, random_state=seed)
    subset_indices, _ = next(subset.split(full_x, full_y))
    x_subset, y_subset = full_x[subset_indices], full_y[subset_indices]
    x_train, x_test, y_train, y_test, train_indices, test_indices = train_test_split(
        x_subset,
        y_subset,
        np.asarray(subset_indices, dtype=np.int64),
        test_size=test_fraction,
        random_state=seed,
        stratify=y_subset,
    )
    scaler = StandardScaler().fit(x_train)
    return (
        scaler.transform(x_train),
        scaler.transform(x_test),
        y_train,
        y_test,
        train_indices.astype(int).tolist() + test_indices.astype(int).tolist(),
    )


def _scaled_rbf_gamma(features: np.ndarray) -> float:
    """Match SVC(gamma='scale') for the already training-scaled matrix."""
    variance = float(np.asarray(features).var())
    return 1.0 / (features.shape[1] * variance) if variance > 0.0 else 1.0


def _pair_specs(n_train: int, n_test: int) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    training_pairs = [(row, col) for row in range(n_train) for col in range(row + 1, n_train)]
    test_pairs = [(row, col) for row in range(n_test) for col in range(n_train)]
    return training_pairs, test_pairs


def _build_compiled_pair_circuits(
    x_train: np.ndarray, x_test: np.ndarray, backend: AerSimulator, seed: int
) -> tuple[list[Any], list[tuple[int, int]], list[tuple[int, int]]]:
    train_pairs, test_pairs = _pair_specs(len(x_train), len(x_test))
    circuits = [compute_uncompute_circuit(x_train[i], x_train[j]) for i, j in train_pairs]
    circuits.extend(compute_uncompute_circuit(x_test[i], x_train[j]) for i, j in test_pairs)
    return (
        transpile(
            circuits,
            backend,
            seed_transpiler=seed,
            optimization_level=0,
            num_processes=1,
        ),
        train_pairs,
        test_pairs,
    )


def _sample_matrices(
    result: Any,
    compiled_circuits: list[Any],
    train_pairs: list[tuple[int, int]],
    test_pairs: list[tuple[int, int]],
    *,
    shots: int,
    n_train: int,
    n_test: int,
) -> tuple[np.ndarray, np.ndarray]:
    train_kernel = np.eye(n_train, dtype=np.float64)
    test_kernel = np.empty((n_test, n_train), dtype=np.float64)
    for index, (row, col) in enumerate(train_pairs):
        counts = result.get_counts(index)
        estimate = counts.get("0" * compiled_circuits[index].num_qubits, 0) / shots
        train_kernel[row, col] = train_kernel[col, row] = estimate
    offset = len(train_pairs)
    for index, (row, col) in enumerate(test_pairs, start=offset):
        counts = result.get_counts(index)
        test_kernel[row, col] = counts.get("0" * compiled_circuits[index].num_qubits, 0) / shots
    return train_kernel, test_kernel


def _matrix_errors(estimated: np.ndarray, exact: np.ndarray) -> dict[str, float]:
    differences = np.asarray(estimated) - np.asarray(exact)
    return {
        "mae": float(np.mean(np.abs(differences))),
        "rmse": float(np.sqrt(np.mean(np.square(differences)))),
        "entries_compared": int(differences.size),
    }


def _fit_result(kernel_train: np.ndarray, kernel_test: np.ndarray, y_train: np.ndarray,
                y_test: np.ndarray) -> tuple[dict[str, float], float, float, list[int]]:
    classifier = SVC(kernel="precomputed", C=1.0)
    start = perf_counter()
    classifier.fit(kernel_train, y_train)
    fit_seconds = perf_counter() - start
    start = perf_counter()
    predictions = classifier.predict(kernel_test)
    predict_seconds = perf_counter() - start
    return (
        {"accuracy": float(accuracy_score(y_test, predictions)),
         "f1": float(f1_score(y_test, predictions, zero_division=0))},
        fit_seconds,
        predict_seconds,
        np.asarray(predictions, dtype=int).tolist(),
    )


def run_finite_shot_kernel_experiment(
    *,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    seed: int = DEFAULT_SEED,
    test_fraction: float = DEFAULT_TEST_FRACTION,
    shot_budgets: tuple[int, ...] = DEFAULT_SHOT_BUDGETS,
    shot_seeds: tuple[int, ...] = DEFAULT_SHOT_SEEDS,
) -> dict[str, Any]:
    """Run fixed-split exact and shot-based kernels plus a fixed RBF baseline."""
    budgets = tuple(shot_budgets)
    seeds = tuple(shot_seeds)
    if not budgets or any(not isinstance(shots, int) or shots < 1 for shots in budgets):
        raise ValueError("shot_budgets must contain positive integers.")
    if not seeds or any(not isinstance(value, int) for value in seeds):
        raise ValueError("shot_seeds must contain integers and cannot be empty.")
    x_train, x_test, y_train, y_test, selected_indices = _make_fixed_split(
        sample_size=sample_size, seed=seed, test_fraction=test_fraction
    )
    train_states, test_states = feature_statevectors(x_train), feature_statevectors(x_test)
    exact_train = fidelity_quantum_kernel(train_states, train_states)
    exact_test = fidelity_quantum_kernel(test_states, train_states)
    rbf_gamma = _scaled_rbf_gamma(x_train)
    classical_train = rbf_kernel(x_train, x_train, gamma=rbf_gamma)
    classical_test = rbf_kernel(x_test, x_train, gamma=rbf_gamma)

    exact_metrics, exact_fit, exact_predict, exact_predictions = _fit_result(
        exact_train, exact_test, y_train, y_test
    )
    rbf_metrics, rbf_fit, rbf_predict, rbf_predictions = _fit_result(
        classical_train, classical_test, y_train, y_test
    )

    backend = AerSimulator(method="statevector")
    transpilation_seed = seed + 100_003
    compile_start = perf_counter()
    compiled, train_pairs, test_pairs = _build_compiled_pair_circuits(
        x_train, x_test, backend, transpilation_seed
    )
    compilation_seconds = perf_counter() - compile_start
    # Warm-up is excluded from measured circuit-execution timings.
    backend.run(compiled[0], shots=8, seed_simulator=transpilation_seed).result()
    shot_reports: list[dict[str, Any]] = []
    for shots in budgets:
        replicate_reports: list[dict[str, Any]] = []
        for replicate_index, shot_seed in enumerate(seeds):
            started = perf_counter()
            aer_result = backend.run(
                compiled, shots=shots, seed_simulator=shot_seed
            ).result()
            execution_seconds = perf_counter() - started
            sampled_train, sampled_test = _sample_matrices(
                aer_result, compiled, train_pairs, test_pairs,
                shots=shots, n_train=len(x_train), n_test=len(x_test)
            )
            sampled_metrics, fit_seconds, predict_seconds, predictions = _fit_result(
                sampled_train, sampled_test, y_train, y_test
            )
            exact_unique_train = np.asarray(
                [exact_train[row, col] for row, col in train_pairs], dtype=np.float64
            )
            sampled_unique_train = np.asarray(
                [sampled_train[row, col] for row, col in train_pairs], dtype=np.float64
            )
            exact_test_values = np.asarray(
                [exact_test[row, col] for row, col in test_pairs], dtype=np.float64
            )
            sampled_test_values = np.asarray(
                [sampled_test[row, col] for row, col in test_pairs], dtype=np.float64
            )
            replicate_reports.append(
                {
                    "replicate": replicate_index,
                    "shot_seed": shot_seed,
                    "kernel_errors": {
                        "training_unique_off_diagonal": _matrix_errors(
                            sampled_unique_train, exact_unique_train
                        ),
                        "test_to_training": _matrix_errors(sampled_test_values, exact_test_values),
                        "all_estimated_entries": _matrix_errors(
                            np.concatenate((sampled_unique_train, sampled_test_values)),
                            np.concatenate((exact_unique_train, exact_test_values)),
                        ),
                    },
                    "training_kernel_diagnostics": training_kernel_diagnostics(sampled_train),
                    "classifier": {
                        **sampled_metrics,
                        "fit_seconds": fit_seconds,
                        "prediction_seconds": predict_seconds,
                        "predictions": predictions,
                    },
                    "timing": {
                        "kernel_circuit_execution_seconds": execution_seconds,
                        "classifier_fit_seconds": fit_seconds,
                        "classifier_prediction_seconds": predict_seconds,
                    },
                }
            )
        error_groups = {
            group: {
                metric: [replicate["kernel_errors"][group][metric] for replicate in replicate_reports]
                for metric in ("mae", "rmse")
            }
            for group in ("training_unique_off_diagonal", "test_to_training", "all_estimated_entries")
        }
        summary: dict[str, Any] = {
            "replicate_count": len(replicate_reports),
            "kernel_error_mean_by_scope": {
                group: {metric: float(np.mean(values)) for metric, values in metrics.items()}
                for group, metrics in error_groups.items()
            },
            "kernel_error_standard_deviation_by_scope": {
                group: {metric: float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
                        for metric, values in metrics.items()}
                for group, metrics in error_groups.items()
            },
            "classifier": {
                metric: {
                    "mean": float(np.mean([replicate["classifier"][metric] for replicate in replicate_reports])),
                    "standard_deviation": float(np.std(
                        [replicate["classifier"][metric] for replicate in replicate_reports], ddof=1
                    )) if len(replicate_reports) > 1 else 0.0,
                }
                for metric in ("accuracy", "f1")
            },
            "minimum_training_eigenvalue": {
                "mean": float(np.mean([
                    replicate["training_kernel_diagnostics"]["minimum_eigenvalue"]
                    for replicate in replicate_reports
                ])),
                "minimum": float(min(
                    replicate["training_kernel_diagnostics"]["minimum_eigenvalue"]
                    for replicate in replicate_reports
                )),
            },
            "positive_semidefinite_replicates_within_tolerance": sum(
                replicate["training_kernel_diagnostics"]["positive_semidefinite_within_tolerance"]
                for replicate in replicate_reports
            ),
            "timing_seconds_median": {
                key: float(np.median([replicate["timing"][key] for replicate in replicate_reports]))
                for key in ("kernel_circuit_execution_seconds", "classifier_fit_seconds",
                            "classifier_prediction_seconds")
            },
        }
        shot_reports.append({"shots": shots, "summary": summary, "replicates": replicate_reports})

    sample_exact_pairs = [(0, 0), (0, min(1, len(x_train) - 1)),
                          (min(1, len(x_train) - 1), 0),
                          (len(x_train) - 1, len(x_train) - 1)]
    circuit_checks = [
        {
            "train_pair_indices": [i, j],
            "compute_uncompute_exact_probability": exact_compute_uncompute_probability(
                x_train[i], x_train[j]
            ),
            "statevector_kernel": float(exact_train[i, j]),
        }
        for i, j in sample_exact_pairs
    ]
    return {
        "metadata": {
            "experiment": "finite-shot compute-uncompute fidelity-kernel sampling sensitivity",
            "seed": seed,
            "dataset": "sklearn.datasets.make_moons",
            "source_dataset_size": DEFAULT_DATASET_SIZE,
            "sample_size": sample_size,
            "stratified_subset_source_indices_in_train_then_test_order": selected_indices,
            "train_size": int(len(x_train)),
            "test_size": int(len(x_test)),
            "test_fraction": test_fraction,
            "shot_budgets": list(budgets),
            "shot_seeds": list(seeds),
            "feature_map": "H, RZ(x), RY(x^2) per qubit, followed by CZ(0,1)",
            "kernel": "P(all-zero | U(z)^dagger U(x)|00>)",
            "circuit_order": "feature_map(x) followed by inverse(feature_map(z))",
            "count_bit_order": "Qiskit displays |q1 q0>; all-zero string is order invariant",
            "simulator": "qiskit_aer.AerSimulator(method='statevector'), local exact simulation with finite-shot measurement sampling",
            "classical_baseline": "SVC(kernel='rbf', C=1.0, gamma='scale') on the same training-only-scaled split",
            "classical_rbf_gamma_value": rbf_gamma,
            "quantum_baseline": "SVC(kernel='precomputed', C=1.0) with exact statevector fidelity kernel",
            "interpretation": "Fixed-split sampling sensitivity only; not a generalization estimate or quantum-advantage claim.",
            "psd_tolerance": PSD_TOLERANCE,
            "psd_policy": "No PSD projection; minimum eigenvalues are reported as observed.",
            "svc_indefinite_kernel_behavior": (
                "The sampled-kernel SVC fit is attempted without PSD correction. Successful per-seed "
                "metrics indicate sklearn SVC accepted that matrix; this does not make an indefinite "
                "similarity matrix a valid Mercer kernel."
            ),
            "circuit_compilation_seconds": compilation_seconds,
        },
        "compute_uncompute_checks": circuit_checks,
        "baselines": {
            "exact_quantum_kernel_svc": {
                **exact_metrics,
                "fit_seconds": exact_fit,
                "prediction_seconds": exact_predict,
                "predictions": exact_predictions,
            },
            "classical_rbf_svc": {
                **rbf_metrics,
                "fit_seconds": rbf_fit,
                "prediction_seconds": rbf_predict,
                "predictions": rbf_predictions,
            },
        },
        "shot_budgets": shot_reports,
    }


def write_finite_shot_result(report: dict[str, Any], output_dir: str | Path = "results") -> Path:
    """Write a new result JSON, refusing to replace an existing experiment."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / FINITE_SHOT_RESULT_FILENAME
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing result artifact: {path.name}")
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
