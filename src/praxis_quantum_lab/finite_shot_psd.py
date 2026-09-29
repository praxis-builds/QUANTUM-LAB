"""PSD diagnostics and transductive spectral repair for finite-shot kernels."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from qiskit import transpile
from qiskit_aer import AerSimulator
from sklearn.metrics.pairwise import rbf_kernel

from praxis_quantum_lab.finite_shot_kernel import (
    DEFAULT_SAMPLE_SIZE,
    DEFAULT_SEED,
    DEFAULT_SHOT_BUDGETS,
    DEFAULT_SHOT_SEEDS,
    PSD_TOLERANCE,
    _fit_result,
    _make_fixed_split,
    _scaled_rbf_gamma,
    compute_uncompute_circuit,
    training_kernel_diagnostics,
)
from praxis_quantum_lab.kernel_experiment import feature_statevectors, fidelity_quantum_kernel
from praxis_quantum_lab.kernel_experiment import DEFAULT_DATASET_SIZE

PSD_REPAIR_RESULT_FILENAME = "finite_shot_kernel_psd_repair.json"
PSD_REPAIR_PLOT_FILENAME = "finite_shot_kernel_psd_repair_min_eigenvalues.png"


def repair_kernel_psd(raw_kernel: np.ndarray, *, tolerance: float = PSD_TOLERANCE) -> np.ndarray:
    """Clip negative eigenvalues and renormalize the diagonal to one.

    The input must be a finite, symmetric, unit-diagonal square matrix. This
    function never mutates the input. Spectral clipping followed by diagonal
    scaling is a simple PSD repair; it is not guaranteed to find the nearest
    correlation matrix under a chosen matrix norm.
    """
    raw = np.asarray(raw_kernel, dtype=np.float64)
    if raw.ndim != 2 or raw.shape[0] != raw.shape[1] or raw.size == 0:
        raise ValueError("raw_kernel must be a non-empty square matrix.")
    if not np.isfinite(raw).all():
        raise ValueError("raw_kernel must contain only finite values.")
    if tolerance < 0:
        raise ValueError("tolerance must be non-negative.")
    if not np.allclose(raw, raw.T, atol=tolerance, rtol=0.0):
        raise ValueError("raw_kernel must be symmetric within tolerance.")
    if not np.allclose(np.diag(raw), 1.0, atol=tolerance, rtol=0.0):
        raise ValueError("raw_kernel must have a unit diagonal within tolerance.")

    eigenvalues, eigenvectors = np.linalg.eigh((raw + raw.T) / 2.0)
    clipped = np.maximum(eigenvalues, 0.0)
    positive_semidefinite = (eigenvectors * clipped) @ eigenvectors.T
    positive_semidefinite = (positive_semidefinite + positive_semidefinite.T) / 2.0
    diagonal = np.diag(positive_semidefinite)
    if np.any(diagonal <= np.finfo(np.float64).eps):
        raise ValueError("PSD reconstruction has a zero diagonal; cannot renormalize it.")
    inverse_sqrt_diagonal = 1.0 / np.sqrt(diagonal)
    repaired = (
        inverse_sqrt_diagonal[:, np.newaxis]
        * positive_semidefinite
        * inverse_sqrt_diagonal[np.newaxis, :]
    )
    repaired = (repaired + repaired.T) / 2.0
    np.fill_diagonal(repaired, 1.0)
    return repaired


def _upper_triangle_pairs(size: int) -> list[tuple[int, int]]:
    return [(row, col) for row in range(size) for col in range(row + 1, size)]


def _compile_all_pair_circuits(
    features: np.ndarray, backend: AerSimulator, seed: int
) -> tuple[list[Any], list[tuple[int, int]]]:
    pairs = _upper_triangle_pairs(len(features))
    circuits = [compute_uncompute_circuit(features[row], features[col]) for row, col in pairs]
    compiled = transpile(
        circuits,
        backend,
        seed_transpiler=seed,
        optimization_level=0,
        num_processes=1,
    )
    return compiled, pairs


def _sample_symmetric_kernel(
    result: Any,
    circuits: list[Any],
    pairs: list[tuple[int, int]],
    *,
    size: int,
    shots: int,
) -> np.ndarray:
    """Build one symmetric matrix from one sampled estimate per unique pair."""
    matrix = np.eye(size, dtype=np.float64)
    for index, (row, col) in enumerate(pairs):
        counts = result.get_counts(index)
        estimate = counts.get("0" * circuits[index].num_qubits, 0) / shots
        matrix[row, col] = matrix[col, row] = estimate
    return matrix


def estimate_full_kernel_matrix(
    features: np.ndarray, *, shots: int, seed: int
) -> np.ndarray:
    """Sample all unique input pairs on local Aer and reflect the triangle."""
    if not isinstance(shots, int) or shots < 1:
        raise ValueError("shots must be a positive integer.")
    values = np.asarray(features, dtype=np.float64)
    if values.ndim != 2 or len(values) < 2:
        raise ValueError("features must be a two-dimensional array with at least two rows.")
    backend = AerSimulator(method="statevector")
    compiled, pairs = _compile_all_pair_circuits(values, backend, seed)
    result = backend.run(compiled, shots=shots, seed_simulator=seed).result()
    return _sample_symmetric_kernel(result, compiled, pairs, size=len(values), shots=shots)


def _summary(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "mean": float(np.mean(array)),
        "standard_deviation": float(np.std(array, ddof=1)) if len(array) > 1 else 0.0,
        "minimum": float(np.min(array)),
        "maximum": float(np.max(array)),
    }


def run_psd_repair_experiment(
    *,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    seed: int = DEFAULT_SEED,
    shot_budgets: tuple[int, ...] = DEFAULT_SHOT_BUDGETS,
    shot_seeds: tuple[int, ...] = DEFAULT_SHOT_SEEDS,
    test_fraction: float = 0.30,
) -> dict[str, Any]:
    """Sample the complete fixed subset kernel and compare raw/PSD-repaired fits."""
    if not shot_budgets or any(not isinstance(value, int) or value < 1 for value in shot_budgets):
        raise ValueError("shot_budgets must contain positive integers.")
    if not shot_seeds or any(not isinstance(value, int) for value in shot_seeds):
        raise ValueError("shot_seeds must contain integers and cannot be empty.")

    x_train, x_test, y_train, y_test, selected_indices = _make_fixed_split(
        sample_size=sample_size, seed=seed, test_fraction=test_fraction
    )
    n_train, n_test = len(x_train), len(x_test)
    # Keep the deterministic subset order from the earlier result: train rows,
    # followed by test rows. Scaling has already been fitted on train only.
    x_full = np.concatenate((x_train, x_test), axis=0)
    full_states = feature_statevectors(x_full)
    exact_full = fidelity_quantum_kernel(full_states, full_states)
    exact_train, exact_test = exact_full[:n_train, :n_train], exact_full[n_train:, :n_train]

    gamma = _scaled_rbf_gamma(x_train)
    rbf_train = rbf_kernel(x_train, x_train, gamma=gamma)
    rbf_test = rbf_kernel(x_test, x_train, gamma=gamma)
    exact_metrics, exact_fit, exact_predict, exact_predictions = _fit_result(
        exact_train, exact_test, y_train, y_test
    )
    rbf_metrics, rbf_fit, rbf_predict, rbf_predictions = _fit_result(
        rbf_train, rbf_test, y_train, y_test
    )

    backend = AerSimulator(method="statevector")
    compilation_seed = seed + 100_003
    compilation_started = perf_counter()
    compiled, pairs = _compile_all_pair_circuits(x_full, backend, compilation_seed)
    compilation_seconds = perf_counter() - compilation_started
    backend.run(compiled[0], shots=8, seed_simulator=compilation_seed).result()

    budget_reports: list[dict[str, Any]] = []
    for shots in shot_budgets:
        replicates: list[dict[str, Any]] = []
        for replicate, shot_seed in enumerate(shot_seeds):
            execution_started = perf_counter()
            sampled_result = backend.run(
                compiled, shots=shots, seed_simulator=shot_seed
            ).result()
            execution_seconds = perf_counter() - execution_started
            raw_full = _sample_symmetric_kernel(
                sampled_result, compiled, pairs, size=sample_size, shots=shots
            )

            repair_started = perf_counter()
            repaired_full = repair_kernel_psd(raw_full)
            repair_seconds = perf_counter() - repair_started

            raw_train, raw_test = raw_full[:n_train, :n_train], raw_full[n_train:, :n_train]
            repaired_train = repaired_full[:n_train, :n_train]
            repaired_test = repaired_full[n_train:, :n_train]
            raw_metrics, raw_fit, raw_predict, raw_predictions = _fit_result(
                raw_train, raw_test, y_train, y_test
            )
            repaired_metrics, repaired_fit, repaired_predict, repaired_predictions = _fit_result(
                repaired_train, repaired_test, y_train, y_test
            )
            raw_diagnostics = {
                **training_kernel_diagnostics(raw_full),
                "frobenius_distance_from_raw": 0.0,
            }
            repaired_diagnostics = training_kernel_diagnostics(repaired_full)
            distance = float(np.linalg.norm(repaired_full - raw_full, ord="fro"))

            replicates.append(
                {
                    "replicate": replicate,
                    "shot_seed": shot_seed,
                    "evaluation_scope": {
                        "raw": "fixed-split raw-kernel evaluation; no PSD repair",
                        "repaired": "transductive: PSD repair used the full unlabeled subset kernel, including test inputs",
                        "repair_uses_test_labels": False,
                    },
                    "raw_matrix_diagnostics": raw_diagnostics,
                    "repaired_matrix_diagnostics": {
                        **repaired_diagnostics,
                        "frobenius_distance_from_raw": distance,
                    },
                    "classifier_results": {
                        "raw_finite_shot_kernel": {
                            **raw_metrics,
                            "fit_seconds": raw_fit,
                            "prediction_seconds": raw_predict,
                            "predictions": raw_predictions,
                        },
                        "psd_repaired_transductive_kernel": {
                            **repaired_metrics,
                            "fit_seconds": repaired_fit,
                            "prediction_seconds": repaired_predict,
                            "predictions": repaired_predictions,
                        },
                    },
                    "timing_seconds": {
                        "all_pair_kernel_circuit_execution": execution_seconds,
                        "psd_repair": repair_seconds,
                        "raw_svc_fit": raw_fit,
                        "raw_svc_prediction": raw_predict,
                        "repaired_svc_fit": repaired_fit,
                        "repaired_svc_prediction": repaired_predict,
                    },
                    "raw_sampled_kernel_matrix": raw_full.tolist(),
                    "psd_repaired_kernel_matrix": repaired_full.tolist(),
                }
            )

        raw_diagnostics = [rep["raw_matrix_diagnostics"] for rep in replicates]
        repaired_diagnostics = [rep["repaired_matrix_diagnostics"] for rep in replicates]
        classifiers = {
            model: {
                metric: _summary([
                    rep["classifier_results"][model][metric] for rep in replicates
                ])
                for metric in ("accuracy", "f1")
            }
            for model in ("raw_finite_shot_kernel", "psd_repaired_transductive_kernel")
        }
        budget_reports.append(
            {
                "shots": shots,
                "summary": {
                    "replicate_count": len(replicates),
                    "raw_minimum_eigenvalue": _summary([
                        diag["minimum_eigenvalue"] for diag in raw_diagnostics
                    ]),
                    "repaired_minimum_eigenvalue": _summary([
                        diag["minimum_eigenvalue"] for diag in repaired_diagnostics
                    ]),
                    "raw_psd_replicates_within_tolerance": sum(
                        diag["positive_semidefinite_within_tolerance"] for diag in raw_diagnostics
                    ),
                    "repaired_psd_replicates_within_tolerance": sum(
                        diag["positive_semidefinite_within_tolerance"]
                        for diag in repaired_diagnostics
                    ),
                    "frobenius_distance_from_raw": _summary([
                        diag["frobenius_distance_from_raw"] for diag in repaired_diagnostics
                    ]),
                    "classifier_results": classifiers,
                    "timing_seconds_median": {
                        key: float(np.median([rep["timing_seconds"][key] for rep in replicates]))
                        for key in (
                            "all_pair_kernel_circuit_execution",
                            "psd_repair",
                            "raw_svc_fit",
                            "repaired_svc_fit",
                        )
                    },
                },
                "replicates": replicates,
            }
        )

    return {
        "metadata": {
            "experiment": "finite-shot kernel PSD violation and spectral repair study",
            "seed": seed,
            "dataset": "sklearn.datasets.make_moons",
            "source_dataset_size": DEFAULT_DATASET_SIZE,
            "sample_size": sample_size,
            "train_size": n_train,
            "test_size": n_test,
            "test_fraction": test_fraction,
            "stratified_subset_source_indices_in_train_then_test_order": selected_indices,
            "shot_budgets": list(shot_budgets),
            "shot_seeds": list(shot_seeds),
            "measured_unique_pairs_per_replicate": len(pairs),
            "feature_map": "existing H, RZ(x), RY(x^2) on each qubit, then CZ(0,1)",
            "simulator": "local qiskit_aer.AerSimulator(method='statevector') with finite-shot measurements",
            "raw_kernel": "one estimate per upper-triangle pair, reflected; exact unit diagonal",
            "repair": "clip negative symmetric-matrix eigenvalues at zero, reconstruct, then diagonal-renormalize to unit diagonal",
            "repair_is_nearest_correlation_matrix": False,
            "repaired_evaluation_scope": "transductive; full unlabeled 40-point matrix includes test inputs; no test labels used in repair",
            "raw_evaluation_scope": "fixed train/test split; raw test-to-training block used for prediction",
            "psd_tolerance": PSD_TOLERANCE,
            "no_quantum_advantage_claim": True,
            "circuit_compilation_seconds": compilation_seconds,
            "timing_note": "Circuit execution, spectral repair, SVC fitting and prediction are local CPU timings.",
        },
        "baselines": {
            "exact_statevector_kernel_svc": {
                **exact_metrics,
                "fit_seconds": exact_fit,
                "prediction_seconds": exact_predict,
                "predictions": exact_predictions,
            },
            "fixed_rbf_svc": {
                **rbf_metrics,
                "fit_seconds": rbf_fit,
                "prediction_seconds": rbf_predict,
                "gamma_scale_value": gamma,
                "predictions": rbf_predictions,
            },
        },
        "shot_budgets": budget_reports,
    }


def save_psd_repair_plot(report: dict[str, Any], path: Path) -> None:
    """Plot raw violations against repaired eigenvalues for each shot budget."""
    budgets = report["shot_budgets"]
    shots = [budget["shots"] for budget in budgets]
    raw_means = [budget["summary"]["raw_minimum_eigenvalue"]["mean"] for budget in budgets]
    repaired_means = [
        budget["summary"]["repaired_minimum_eigenvalue"]["mean"] for budget in budgets
    ]
    figure, axis = plt.subplots(figsize=(6.4, 4.0))
    axis.plot(shots, raw_means, marker="o", color="#335c81", label="Raw sampled kernel")
    axis.plot(shots, repaired_means, marker="s", color="#b15b35", label="PSD repaired")
    axis.axhline(0.0, color="#555555", linewidth=0.8, linestyle="--")
    axis.set_xscale("log", base=2)
    axis.set_xlabel("shots per pair")
    axis.set_ylabel("mean minimum eigenvalue")
    axis.set_title("Raw and repaired kernel PSD status")
    axis.legend(frameon=False)
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def write_psd_repair_artifacts(
    report: dict[str, Any], output_dir: str | Path = "results"
) -> tuple[Path, Path]:
    """Write JSON and plot to new paths; refuse either overwrite."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / PSD_REPAIR_RESULT_FILENAME
    plot_path = destination / PSD_REPAIR_PLOT_FILENAME
    existing = [path.name for path in (json_path, plot_path) if path.exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite existing PSD-repair artifact(s): {existing}")
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    save_psd_repair_plot(report, plot_path)
    return json_path, plot_path
