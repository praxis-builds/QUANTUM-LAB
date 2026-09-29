"""A small, reproducible classical-versus-quantum-kernel comparison.

The quantum kernel is evaluated from exact local Qiskit statevectors.  It is
not a claim that a quantum computer is faster or more accurate than the
classical baseline; it is a controlled learning experiment on one small data
set and one feature map.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, TypeVar

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from sklearn.datasets import make_moons
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.metrics.pairwise import rbf_kernel
from sklearn.model_selection import RepeatedStratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

DEFAULT_SEED = 20260928
DEFAULT_DATASET_SIZE = 80
DEFAULT_REPEATED_SPLITS = 3
DEFAULT_REPEATS = 2
DEFAULT_TIMING_REPETITIONS = 1
REPEATED_RESULT_FILENAME = "classification_repeated_comparison.json"
DEFAULT_EXTENDED_SPLITS = 5
DEFAULT_EXTENDED_REPEATS = 10
EXTENDED_RESULT_FILENAME = "classification_extended_5x10_comparison.json"
KERNEL_DIAGNOSTIC_TOLERANCE = 1e-10
T = TypeVar("T")


@dataclass(frozen=True)
class ClassifierMeasurement:
    """Metrics and timing for one classifier on the common held-out test set."""

    accuracy: float
    precision: float
    recall: float
    f1: float
    training_time_seconds: float
    inference_time_seconds: float
    confusion_matrix: list[list[int]]
    predictions: list[int]


def timed(callable_: Callable[[], T]) -> tuple[T, float]:
    """Run a function and return its result plus wall-clock duration."""
    start = perf_counter()
    value = callable_()
    return value, perf_counter() - start


def median_timed(callable_: Callable[[], T], *, repetitions: int) -> tuple[T, float]:
    """Return a result and median local wall-clock time across repetitions."""
    if not isinstance(repetitions, int) or repetitions < 1:
        raise ValueError("repetitions must be a positive integer.")
    durations: list[float] = []
    result: T | None = None
    for _ in range(repetitions):
        result, duration = timed(callable_)
        durations.append(duration)
    return result, float(np.median(durations))


def make_dataset(
    *, dataset_size: int = DEFAULT_DATASET_SIZE, seed: int = DEFAULT_SEED
) -> tuple[np.ndarray, np.ndarray]:
    """Make a compact nonlinear binary data set appropriate for a laptop."""
    if dataset_size < 20:
        raise ValueError("Use at least 20 samples so both classes reach each split.")
    features, labels = make_moons(n_samples=dataset_size, noise=0.12, random_state=seed)
    return features.astype(np.float64), labels.astype(np.int64)


def quantum_feature_map(values: np.ndarray) -> QuantumCircuit:
    """Encode a two-feature vector into a small entangling Qiskit circuit.

    The circuit first creates local phase-sensitive superpositions, then adds a
    CZ entangler.  It remains intentionally shallow: this lesson is about the
    kernel construction, not an architecture search.
    """
    vector = np.asarray(values, dtype=np.float64)
    if vector.ndim != 1 or vector.size != 2:
        raise ValueError("This first lab feature map accepts exactly two features/qubits.")
    circuit = QuantumCircuit(2, name="two_feature_map")
    for qubit, value in enumerate(vector):
        circuit.h(qubit)
        circuit.rz(float(value), qubit)
        circuit.ry(float(value * value), qubit)
    circuit.cz(0, 1)
    return circuit


def feature_statevectors(features: np.ndarray) -> np.ndarray:
    """Represent every sample exactly as the statevector of its feature map."""
    return np.asarray(
        [Statevector.from_instruction(quantum_feature_map(row)).data for row in features],
        dtype=np.complex128,
    )


def fidelity_quantum_kernel(left_states: np.ndarray, right_states: np.ndarray) -> np.ndarray:
    """Compute K(x, z) = |⟨φ(x)|φ(z)⟩|² for every pair of encoded samples."""
    overlaps = left_states.conjugate() @ right_states.T
    kernel = np.abs(overlaps) ** 2
    return np.clip(kernel.real, 0.0, 1.0)


def _metrics(labels: np.ndarray, predictions: np.ndarray, train_time: float, inference_time: float) -> ClassifierMeasurement:
    return ClassifierMeasurement(
        accuracy=float(accuracy_score(labels, predictions)),
        precision=float(precision_score(labels, predictions, zero_division=0)),
        recall=float(recall_score(labels, predictions, zero_division=0)),
        f1=float(f1_score(labels, predictions, zero_division=0)),
        training_time_seconds=float(train_time),
        inference_time_seconds=float(inference_time),
        confusion_matrix=confusion_matrix(labels, predictions, labels=[0, 1]).astype(int).tolist(),
        predictions=np.asarray(predictions, dtype=int).tolist(),
    )


def run_classification_experiment(
    *,
    dataset_size: int = DEFAULT_DATASET_SIZE,
    seed: int = DEFAULT_SEED,
    test_size: float = 0.30,
) -> dict[str, Any]:
    """Fit both classifiers using exactly the same deterministic train/test split."""
    features, labels = make_dataset(dataset_size=dataset_size, seed=seed)
    x_train, x_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=test_size,
        random_state=seed,
        stratify=labels,
    )

    # A pipeline prevents test-set information from influencing fitted scaling.
    classical = Pipeline(
        [
            ("scale", StandardScaler()),
            ("classifier", SVC(kernel="rbf", C=1.0, gamma="scale")),
        ]
    )
    _, classical_train_time = timed(lambda: classical.fit(x_train, y_train))
    classical_predictions, classical_inference_time = timed(lambda: classical.predict(x_test))

    scaler = StandardScaler().fit(x_train)
    x_train_scaled = scaler.transform(x_train)
    x_test_scaled = scaler.transform(x_test)

    def fit_quantum_classifier() -> tuple[SVC, np.ndarray, np.ndarray]:
        train_states = feature_statevectors(x_train_scaled)
        test_states = feature_statevectors(x_test_scaled)
        train_kernel = fidelity_quantum_kernel(train_states, train_states)
        classifier = SVC(kernel="precomputed", C=1.0)
        classifier.fit(train_kernel, y_train)
        return classifier, train_states, test_states

    (quantum_classifier, train_states, test_states), quantum_train_time = timed(
        fit_quantum_classifier
    )

    def predict_quantum() -> np.ndarray:
        test_kernel = fidelity_quantum_kernel(test_states, train_states)
        return quantum_classifier.predict(test_kernel)

    quantum_predictions, quantum_inference_time = timed(predict_quantum)
    circuit = quantum_feature_map(x_train_scaled[0])

    return {
        "metadata": {
            "seed": seed,
            "dataset": "sklearn.datasets.make_moons",
            "dataset_size": dataset_size,
            "train_size": int(len(x_train)),
            "test_size": int(len(x_test)),
            "test_fraction": test_size,
            "class_balance": {"class_0": int((labels == 0).sum()), "class_1": int((labels == 1).sum())},
            "classical_model": "StandardScaler + SVC(kernel='rbf', C=1.0, gamma='scale')",
            "quantum_model": "SVC(kernel='precomputed', C=1.0) with statevector fidelity kernel",
            "feature_map": "H, RZ(x), RY(x²) on each qubit, followed by CZ(0, 1)",
            "circuit_depth": circuit.depth(),
            "number_of_qubits": circuit.num_qubits,
            "simulator_type": "qiskit.quantum_info.Statevector (exact local simulation)",
        },
        "classical_rbf_svc": asdict(
            _metrics(y_test, classical_predictions, classical_train_time, classical_inference_time)
        ),
        "quantum_kernel_svc": asdict(
            _metrics(y_test, quantum_predictions, quantum_train_time, quantum_inference_time)
        ),
    }


def reproducibility_signature(report: dict[str, Any]) -> dict[str, Any]:
    """Extract deterministic outputs while deliberately excluding wall-clock time."""
    return {
        "metadata": report["metadata"],
        "classical": {
            key: value
            for key, value in report["classical_rbf_svc"].items()
            if not key.endswith("time_seconds")
        },
        "quantum": {
            key: value
            for key, value in report["quantum_kernel_svc"].items()
            if not key.endswith("time_seconds")
        },
    }


def verify_reproducibility(
    *, dataset_size: int = DEFAULT_DATASET_SIZE, seed: int = DEFAULT_SEED
) -> bool:
    """Repeat the experiment with the same seed and compare non-timing outputs."""
    first = run_classification_experiment(dataset_size=dataset_size, seed=seed)
    second = run_classification_experiment(dataset_size=dataset_size, seed=seed)
    return reproducibility_signature(first) == reproducibility_signature(second)


def _metric_values(labels: np.ndarray, predictions: np.ndarray) -> dict[str, Any]:
    """Return the classification values shared by single and repeated reports."""
    return {
        "accuracy": float(accuracy_score(labels, predictions)),
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "confusion_matrix": confusion_matrix(labels, predictions, labels=[0, 1])
        .astype(int)
        .tolist(),
        "predictions": np.asarray(predictions, dtype=int).tolist(),
    }


def _precomputed_rbf_gamma(features: np.ndarray) -> float:
    """Match SVC(gamma='scale') after a train-split-only standardization."""
    variance = float(np.var(features))
    if np.isclose(variance, 0.0):
        raise ValueError("The scaled training features have zero variance.")
    return 1.0 / (features.shape[1] * variance)


def _aggregate_values(values: list[float]) -> dict[str, float]:
    """Return descriptive mean, sample deviation, median, and IQR."""
    array = np.asarray(values, dtype=np.float64)
    lower_quartile, upper_quartile = np.percentile(array, [25, 75])
    return {
        "mean": float(np.mean(array)),
        "standard_deviation": float(np.std(array, ddof=1)) if len(array) > 1 else 0.0,
        "median": float(np.median(array)),
        "interquartile_range": float(upper_quartile - lower_quartile),
    }


def _aggregate_repeated_model_results(
    split_reports: list[dict[str, Any]], model_key: str
) -> dict[str, Any]:
    metrics = ("accuracy", "precision", "recall", "f1")
    timing_keys = (
        "train_kernel_construction",
        "test_kernel_construction",
        "svc_fit",
        "prediction",
    )
    return {
        "metrics": {
            metric: _aggregate_values([split[model_key][metric] for split in split_reports])
            for metric in metrics
        },
        "local_simulator_timing_seconds": {
            timing_key: _aggregate_values(
                [
                    split[model_key]["local_simulator_timing_seconds"][timing_key]
                    for split in split_reports
                ]
            )
            for timing_key in timing_keys
        },
    }


def training_kernel_diagnostics(
    kernel_matrix: np.ndarray, *, tolerance: float = KERNEL_DIAGNOSTIC_TOLERANCE
) -> dict[str, Any]:
    """Describe an exact training kernel without looking at labels or test data."""
    matrix = np.asarray(kernel_matrix, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("Kernel diagnostics require a square training Gram matrix.")
    symmetric_matrix = (matrix + matrix.T) / 2.0
    diagonal = np.diag(matrix)
    eigenvalues = np.linalg.eigvalsh(symmetric_matrix)
    return {
        "matrix_size": int(matrix.shape[0]),
        "symmetry_max_abs_error": float(np.max(np.abs(matrix - matrix.T))),
        "diagonal_values": diagonal.astype(float).tolist(),
        "diagonal_min": float(np.min(diagonal)),
        "diagonal_max": float(np.max(diagonal)),
        "diagonal_mean": float(np.mean(diagonal)),
        "minimum_eigenvalue": float(np.min(eigenvalues)),
        "positive_semidefinite_within_tolerance": bool(np.min(eigenvalues) >= -tolerance),
        "tolerance": tolerance,
    }


def training_kernel_similarity(
    quantum_kernel: np.ndarray, classical_rbf_kernel: np.ndarray
) -> dict[str, float | None]:
    """Compare training kernels geometrically without consulting class labels."""
    quantum = np.asarray(quantum_kernel, dtype=np.float64)
    classical = np.asarray(classical_rbf_kernel, dtype=np.float64)
    if quantum.shape != classical.shape or quantum.ndim != 2 or quantum.shape[0] != quantum.shape[1]:
        raise ValueError("Kernel similarity requires same-shaped square training Gram matrices.")
    denominator = float(np.linalg.norm(quantum, ord="fro") * np.linalg.norm(classical, ord="fro"))
    frobenius_cosine_similarity = (
        float(np.clip(np.sum(quantum * classical) / denominator, -1.0, 1.0))
        if denominator
        else None
    )
    off_diagonal = ~np.eye(quantum.shape[0], dtype=bool)
    quantum_values = quantum[off_diagonal]
    classical_values = classical[off_diagonal]
    if np.isclose(np.std(quantum_values), 0.0) or np.isclose(np.std(classical_values), 0.0):
        off_diagonal_correlation: float | None = None
    else:
        off_diagonal_correlation = float(np.corrcoef(quantum_values, classical_values)[0, 1])
    return {
        "frobenius_cosine_similarity": frobenius_cosine_similarity,
        "off_diagonal_pearson_correlation": off_diagonal_correlation,
        "mean_absolute_entry_difference": float(np.mean(np.abs(quantum - classical))),
    }


def _aggregate_training_kernel_diagnostics(split_reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate scalar training-only diagnostic summaries across paired splits."""
    scalar_keys = (
        "symmetry_max_abs_error",
        "diagonal_min",
        "diagonal_max",
        "diagonal_mean",
        "minimum_eigenvalue",
    )
    kernels = ("classical_rbf", "quantum")
    result: dict[str, Any] = {"scope": "training data only"}
    for kernel_name in kernels:
        result[kernel_name] = {
            scalar_key: _aggregate_values(
                [
                    split["training_kernel_diagnostics"][kernel_name][scalar_key]
                    for split in split_reports
                ]
            )
            for scalar_key in scalar_keys
        }
        result[kernel_name]["all_positive_semidefinite_within_tolerance"] = all(
            split["training_kernel_diagnostics"][kernel_name][
                "positive_semidefinite_within_tolerance"
            ]
            for split in split_reports
        )
    similarity_keys = (
        "frobenius_cosine_similarity",
        "off_diagonal_pearson_correlation",
        "mean_absolute_entry_difference",
    )
    result["quantum_vs_classical_rbf"] = {
        key: _aggregate_values(
            [
                split["training_kernel_diagnostics"]["quantum_vs_classical_rbf"][key]
                for split in split_reports
                if split["training_kernel_diagnostics"]["quantum_vs_classical_rbf"][key]
                is not None
            ]
        )
        for key in similarity_keys
    }
    return result


def _warm_up_repeated_timing() -> None:
    """Warm up imports and small linear-algebra paths before recording timings."""
    warm_features = np.array([[0.0, 0.0], [0.2, -0.2]], dtype=np.float64)
    warm_states = feature_statevectors(warm_features)
    fidelity_quantum_kernel(warm_states, warm_states)
    rbf_kernel(warm_features, warm_features, gamma=0.5)


def _run_repeated_split(
    *,
    split_index: int,
    repeat_index: int,
    fold_index: int,
    x_train: np.ndarray,
    x_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
    timing_repetitions: int,
) -> dict[str, Any]:
    """Evaluate both precomputed kernels on one common, leakage-free split."""
    scaler = StandardScaler()
    (x_train_scaled, x_test_scaled), preprocessing_time = median_timed(
        lambda: (scaler.fit_transform(x_train), scaler.transform(x_test)),
        repetitions=timing_repetitions,
    )

    classical_gamma = _precomputed_rbf_gamma(x_train_scaled)
    classical_train_kernel, classical_train_kernel_time = median_timed(
        lambda: rbf_kernel(x_train_scaled, x_train_scaled, gamma=classical_gamma),
        repetitions=timing_repetitions,
    )

    def fit_classical() -> SVC:
        classifier = SVC(kernel="precomputed", C=1.0)
        classifier.fit(classical_train_kernel, y_train)
        return classifier

    classical_classifier, classical_fit_time = median_timed(
        fit_classical, repetitions=timing_repetitions
    )
    classical_test_kernel, classical_test_kernel_time = median_timed(
        lambda: rbf_kernel(x_test_scaled, x_train_scaled, gamma=classical_gamma),
        repetitions=timing_repetitions,
    )
    classical_predictions, classical_prediction_time = median_timed(
        lambda: classical_classifier.predict(classical_test_kernel),
        repetitions=timing_repetitions,
    )

    def construct_quantum_train_kernel() -> tuple[np.ndarray, np.ndarray]:
        train_states = feature_statevectors(x_train_scaled)
        return train_states, fidelity_quantum_kernel(train_states, train_states)

    (quantum_train_states, quantum_train_kernel), quantum_train_kernel_time = median_timed(
        construct_quantum_train_kernel, repetitions=timing_repetitions
    )
    diagnostics = {
        "scope": "training data only; no labels or test features are used",
        "classical_rbf": training_kernel_diagnostics(classical_train_kernel),
        "quantum": training_kernel_diagnostics(quantum_train_kernel),
        "quantum_vs_classical_rbf": training_kernel_similarity(
            quantum_train_kernel, classical_train_kernel
        ),
    }

    def fit_quantum() -> SVC:
        classifier = SVC(kernel="precomputed", C=1.0)
        classifier.fit(quantum_train_kernel, y_train)
        return classifier

    quantum_classifier, quantum_fit_time = median_timed(
        fit_quantum, repetitions=timing_repetitions
    )

    def construct_quantum_test_kernel() -> np.ndarray:
        test_states = feature_statevectors(x_test_scaled)
        return fidelity_quantum_kernel(test_states, quantum_train_states)

    quantum_test_kernel, quantum_test_kernel_time = median_timed(
        construct_quantum_test_kernel, repetitions=timing_repetitions
    )
    quantum_predictions, quantum_prediction_time = median_timed(
        lambda: quantum_classifier.predict(quantum_test_kernel),
        repetitions=timing_repetitions,
    )

    classical_result = _metric_values(y_test, classical_predictions)
    classical_result["local_simulator_timing_seconds"] = {
        "train_kernel_construction": classical_train_kernel_time,
        "test_kernel_construction": classical_test_kernel_time,
        "svc_fit": classical_fit_time,
        "prediction": classical_prediction_time,
    }
    quantum_result = _metric_values(y_test, quantum_predictions)
    quantum_result["local_simulator_timing_seconds"] = {
        "train_kernel_construction": quantum_train_kernel_time,
        "test_kernel_construction": quantum_test_kernel_time,
        "svc_fit": quantum_fit_time,
        "prediction": quantum_prediction_time,
    }
    return {
        "split_index": split_index,
        "repeat_index": repeat_index,
        "fold_index": fold_index,
        "train_size": int(len(x_train)),
        "test_size": int(len(x_test)),
        "shared_train_split_preprocessing_seconds": preprocessing_time,
        "training_kernel_diagnostics": diagnostics,
        "classical_rbf_svc": classical_result,
        "quantum_kernel_svc": quantum_result,
        "paired_accuracy_difference_quantum_minus_classical": float(
            quantum_result["accuracy"] - classical_result["accuracy"]
        ),
    }


def run_repeated_classification_experiment(
    *,
    dataset_size: int = DEFAULT_DATASET_SIZE,
    seed: int = DEFAULT_SEED,
    n_splits: int = DEFAULT_REPEATED_SPLITS,
    n_repeats: int = DEFAULT_REPEATS,
    timing_repetitions: int = DEFAULT_TIMING_REPETITIONS,
) -> dict[str, Any]:
    """Run repeated stratified, paired classical-versus-quantum comparisons.

    The default six splits (three folds repeated twice) are a practical local
    starting point.  ``timing_repetitions`` defaults to one after an unmeasured
    warm-up; increase it to three or more when studying timing stability.
    """
    if not isinstance(n_splits, int) or n_splits < 2:
        raise ValueError("n_splits must be an integer of at least two.")
    if not isinstance(n_repeats, int) or n_repeats < 1:
        raise ValueError("n_repeats must be a positive integer.")
    if not isinstance(timing_repetitions, int) or timing_repetitions < 1:
        raise ValueError("timing_repetitions must be a positive integer.")

    features, labels = make_dataset(dataset_size=dataset_size, seed=seed)
    if n_splits > int(np.bincount(labels).min()):
        raise ValueError("n_splits cannot exceed the smallest class count.")
    _warm_up_repeated_timing()
    splitter = RepeatedStratifiedKFold(
        n_splits=n_splits, n_repeats=n_repeats, random_state=seed
    )
    split_reports: list[dict[str, Any]] = []
    for split_index, (train_indices, test_indices) in enumerate(splitter.split(features, labels)):
        split_reports.append(
            _run_repeated_split(
                split_index=split_index,
                repeat_index=split_index // n_splits,
                fold_index=split_index % n_splits,
                x_train=features[train_indices],
                x_test=features[test_indices],
                y_train=labels[train_indices],
                y_test=labels[test_indices],
                timing_repetitions=timing_repetitions,
            )
        )

    paired_differences = [
        split["paired_accuracy_difference_quantum_minus_classical"]
        for split in split_reports
    ]
    circuit = quantum_feature_map(np.zeros(2, dtype=np.float64))
    return {
        "metadata": {
            "seed": seed,
            "dataset": "sklearn.datasets.make_moons",
            "dataset_size": dataset_size,
            "n_splits": n_splits,
            "n_repeats": n_repeats,
            "total_evaluated_splits": len(split_reports),
            "timing_repetitions": timing_repetitions,
            "timing_method": (
                "Median local wall-clock time across timing_repetitions after one unmeasured "
                "warm-up. Quantum-kernel timings are exact local classical-simulation timings; "
                "classical RBF timings are local CPU timings, and neither predicts QPU runtime."
            ),
            "preprocessing": "StandardScaler is fit separately inside each training split.",
            "classical_model": "Precomputed RBF kernel + SVC(kernel='precomputed', C=1.0)",
            "quantum_model": "Exact statevector fidelity kernel + SVC(kernel='precomputed', C=1.0)",
            "feature_map": "H, RZ(x), RY(x²) on each qubit, followed by CZ(0, 1)",
            "circuit_depth": circuit.depth(),
            "number_of_qubits": circuit.num_qubits,
            "simulator_type": "qiskit.quantum_info.Statevector (exact local simulation)",
            "kernel_diagnostics_scope": "Training Gram matrices only; labels and test data are excluded.",
        },
        "per_split": split_reports,
        "aggregate": {
            "classical_rbf_svc": _aggregate_repeated_model_results(
                split_reports, "classical_rbf_svc"
            ),
            "quantum_kernel_svc": _aggregate_repeated_model_results(
                split_reports, "quantum_kernel_svc"
            ),
            "paired_accuracy_difference_quantum_minus_classical": {
                **_aggregate_values(paired_differences),
                "values": paired_differences,
            },
            "training_kernel_diagnostics": _aggregate_training_kernel_diagnostics(
                split_reports
            ),
        },
    }


def repeated_reproducibility_signature(report: dict[str, Any]) -> dict[str, Any]:
    """Extract deterministic repeated-split outputs while excluding timings."""
    return {
        "metadata": {
            key: value
            for key, value in report["metadata"].items()
            if not key.startswith("timing")
        },
        "per_split": [
            {
                "split_index": split["split_index"],
                "repeat_index": split["repeat_index"],
                "fold_index": split["fold_index"],
                "train_size": split["train_size"],
                "test_size": split["test_size"],
                "training_kernel_diagnostics": split["training_kernel_diagnostics"],
                "classical_rbf_svc": {
                    key: value
                    for key, value in split["classical_rbf_svc"].items()
                    if key != "local_simulator_timing_seconds"
                },
                "quantum_kernel_svc": {
                    key: value
                    for key, value in split["quantum_kernel_svc"].items()
                    if key != "local_simulator_timing_seconds"
                },
                "paired_accuracy_difference_quantum_minus_classical": split[
                    "paired_accuracy_difference_quantum_minus_classical"
                ],
            }
            for split in report["per_split"]
        ],
        "paired_accuracy_difference_values": report["aggregate"][
            "paired_accuracy_difference_quantum_minus_classical"
        ]["values"],
        "aggregated_training_kernel_diagnostics": report["aggregate"][
            "training_kernel_diagnostics"
        ],
    }


def verify_repeated_reproducibility(
    *,
    dataset_size: int = DEFAULT_DATASET_SIZE,
    seed: int = DEFAULT_SEED,
    n_splits: int = DEFAULT_REPEATED_SPLITS,
    n_repeats: int = DEFAULT_REPEATS,
) -> bool:
    """Repeat the paired experiment and compare all non-timing results."""
    first = run_repeated_classification_experiment(
        dataset_size=dataset_size, seed=seed, n_splits=n_splits, n_repeats=n_repeats
    )
    second = run_repeated_classification_experiment(
        dataset_size=dataset_size, seed=seed, n_splits=n_splits, n_repeats=n_repeats
    )
    return repeated_reproducibility_signature(first) == repeated_reproducibility_signature(second)


def write_repeated_experiment_artifact(
    report: dict[str, Any], output_dir: str | Path = "results"
) -> Path:
    """Save a new repeated-split result without replacing earlier experiments."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / REPEATED_RESULT_FILENAME
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing result artifact: {path.name}")
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def run_extended_kernel_evaluation(
    *,
    dataset_size: int = DEFAULT_DATASET_SIZE,
    seed: int = DEFAULT_SEED,
    n_splits: int = DEFAULT_EXTENDED_SPLITS,
    n_repeats: int = DEFAULT_EXTENDED_REPEATS,
    timing_repetitions: int = DEFAULT_TIMING_REPETITIONS,
) -> dict[str, Any]:
    """Run the configurable expanded paired evaluation, defaulting to 5x10."""
    report = run_repeated_classification_experiment(
        dataset_size=dataset_size,
        seed=seed,
        n_splits=n_splits,
        n_repeats=n_repeats,
        timing_repetitions=timing_repetitions,
    )
    report["metadata"].update(
        {
            "evaluation_name": "expanded repeated paired kernel evaluation",
            "requested_configuration": "5 folds x 10 repeats by default",
            "completed_configuration": f"{n_splits} folds x {n_repeats} repeats",
            "descriptive_inference_note": (
                "Repeated-fold observations overlap and are not independent samples; no naive "
                "significance test is reported."
            ),
        }
    )
    return report


def write_extended_kernel_evaluation_artifact(
    report: dict[str, Any], output_dir: str | Path = "results"
) -> Path:
    """Save an expanded result separately, refusing to replace previous reports."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / EXTENDED_RESULT_FILENAME
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing result artifact: {path.name}")
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def verify_extended_kernel_reproducibility(
    *,
    dataset_size: int = DEFAULT_DATASET_SIZE,
    seed: int = DEFAULT_SEED,
    n_splits: int = DEFAULT_EXTENDED_SPLITS,
    n_repeats: int = DEFAULT_EXTENDED_REPEATS,
) -> bool:
    """Check deterministic non-timing outcomes for an expanded configuration."""
    first = run_extended_kernel_evaluation(
        dataset_size=dataset_size, seed=seed, n_splits=n_splits, n_repeats=n_repeats
    )
    second = run_extended_kernel_evaluation(
        dataset_size=dataset_size, seed=seed, n_splits=n_splits, n_repeats=n_repeats
    )
    return repeated_reproducibility_signature(first) == repeated_reproducibility_signature(second)


def save_confusion_matrices(report: dict[str, Any], path: Path) -> None:
    """Persist both held-out-test confusion matrices side by side."""
    figure, axes = plt.subplots(1, 2, figsize=(8.4, 3.8))
    for axis, (name, content) in zip(
        axes,
        (
            ("Classical RBF SVC", report["classical_rbf_svc"]),
            ("Quantum-kernel SVC", report["quantum_kernel_svc"]),
        ),
        strict=True,
    ):
        display = ConfusionMatrixDisplay(
            confusion_matrix=np.asarray(content["confusion_matrix"]), display_labels=[0, 1]
        )
        display.plot(ax=axis, colorbar=False)
        axis.set_title(name)
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def write_experiment_artifacts(
    report: dict[str, Any], output_dir: str | Path = "results"
) -> None:
    """Write a machine-readable report and a comparison figure."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "classification_comparison.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    save_confusion_matrices(report, destination / "classification_confusion_matrices.png")


def main() -> None:
    """CLI entry point used by ``praxis-kernel-experiment``."""
    report = run_classification_experiment()
    write_experiment_artifacts(report)
    reproducible = verify_reproducibility()
    classical = report["classical_rbf_svc"]
    quantum = report["quantum_kernel_svc"]
    print("Classical versus quantum-kernel experiment completed.")
    print(f"Classical accuracy/F1: {classical['accuracy']:.3f} / {classical['f1']:.3f}")
    print(f"Quantum-kernel accuracy/F1: {quantum['accuracy']:.3f} / {quantum['f1']:.3f}")
    print(f"Same-seed non-timing outputs reproducible: {reproducible}")
    print("Saved results/classification_comparison.json and confusion-matrix PNG.")


if __name__ == "__main__":
    main()
