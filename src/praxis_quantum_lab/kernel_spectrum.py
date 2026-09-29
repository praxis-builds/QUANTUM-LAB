"""Rank and spectrum of fidelity kernels versus finite-shot PSD violation.

Exact kernels come from local statevectors.  Finite-shot kernels use the
Binomial(shots, K_ij) / shots model of a compute-uncompute estimate, which is
cross-checked against local Aer sampling.  Raw sampled kernels are never
repaired here: indefiniteness is the quantity being measured.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.preprocessing import StandardScaler

from praxis_quantum_lab.finite_shot_kernel import PSD_TOLERANCE, compute_uncompute_circuit
from praxis_quantum_lab.kernel_experiment import (
    DEFAULT_SEED,
    fidelity_quantum_kernel,
    make_dataset,
)

QUBIT_COUNTS = (1, 2, 3)
SAMPLE_SIZES = (8, 16, 24, 40)
SHOT_BUDGETS = (128, 512, 2048, 8192)
SEED_OFFSETS = (0, 1, 2, 3, 4)
RESULT_FILENAME = "kernel_rank_prediction.json"
PLOT_FILENAME = "kernel_rank_prediction_lambda_min.png"


def feature_map_q(values: np.ndarray, num_qubits: int) -> QuantumCircuit:
    """H, RZ(x), RY(x^2) per qubit, features assigned cyclically, then a CZ chain.

    For ``num_qubits == 2`` this is the existing ``quantum_feature_map``.
    """
    vector = np.asarray(values, dtype=np.float64)
    if vector.ndim != 1 or vector.size < 1:
        raise ValueError("values must be a non-empty 1-D feature vector.")
    if num_qubits < 1:
        raise ValueError("num_qubits must be positive.")
    circuit = QuantumCircuit(num_qubits, name=f"feature_map_q{num_qubits}")
    for qubit in range(num_qubits):
        value = float(vector[qubit % vector.size])
        circuit.h(qubit)
        circuit.rz(value, qubit)
        circuit.ry(value * value, qubit)
    for qubit in range(num_qubits - 1):
        circuit.cz(qubit, qubit + 1)
    return circuit


def exact_kernel(features: np.ndarray, num_qubits: int) -> np.ndarray:
    states = np.asarray(
        [Statevector.from_instruction(feature_map_q(row, num_qubits)).data for row in features],
        dtype=np.complex128,
    )
    return fidelity_quantum_kernel(states, states)


def make_subset_features(sample_size: int, seed_offset: int) -> np.ndarray:
    """Stratified n-point subset of the existing moons data, scaled on the subset."""
    features, labels = make_dataset(seed=DEFAULT_SEED)
    splitter = StratifiedShuffleSplit(
        n_splits=1, train_size=sample_size, random_state=DEFAULT_SEED + seed_offset
    )
    indices, _ = next(splitter.split(features, labels))
    return StandardScaler().fit_transform(features[indices])


def exact_rank(kernel: np.ndarray, num_qubits: int) -> int:
    eigenvalues = np.linalg.eigvalsh(kernel)
    tolerance = max(kernel.shape[0], 4**num_qubits) * np.finfo(np.float64).eps * eigenvalues.max()
    return int((eigenvalues > tolerance).sum())


def sample_kernel_binomial(kernel: np.ndarray, shots: int, rng: np.random.Generator) -> np.ndarray:
    """Symmetric finite-shot kernel: upper triangle Binomial(shots, K_ij)/shots, unit diagonal."""
    if not isinstance(shots, int) or shots < 1:
        raise ValueError("shots must be a positive integer.")
    size = kernel.shape[0]
    upper = np.triu_indices(size, k=1)
    sampled = np.eye(size, dtype=np.float64)
    values = rng.binomial(shots, np.clip(kernel[upper], 0.0, 1.0)) / shots
    sampled[upper] = values
    sampled[(upper[1], upper[0])] = values
    return sampled


def sampling_rng(num_qubits: int, sample_size: int, shots: int, seed_offset: int) -> np.random.Generator:
    return np.random.default_rng([DEFAULT_SEED, num_qubits, sample_size, shots, seed_offset])


def spectrum_row(
    exact: np.ndarray, num_qubits: int, shots: int, rng: np.random.Generator
) -> dict[str, Any]:
    raw = sample_kernel_binomial(exact, shots, rng)
    raw_eigenvalues = np.linalg.eigvalsh(raw)
    exact_eigenvalues = np.linalg.eigvalsh(exact)
    rank = exact_rank(exact, num_qubits)
    size = exact.shape[0]
    return {
        "exact_rank": rank,
        "nullity": size - rank,
        "lambda_min_exact": float(exact_eigenvalues.min()),
        "negative_eigenvalue_count": int((raw_eigenvalues < -PSD_TOLERANCE).sum()),
        "lambda_min_raw": float(raw_eigenvalues.min()),
        "psd": bool(raw_eigenvalues.min() >= -PSD_TOLERANCE),
        "mean_offdiagonal_k": float(exact[np.triu_indices(size, k=1)].mean()),
    }


def run_sweep(
    *,
    qubit_counts: tuple[int, ...] = QUBIT_COUNTS,
    sample_sizes: tuple[int, ...] = SAMPLE_SIZES,
    shot_budgets: tuple[int, ...] = SHOT_BUDGETS,
    seed_offsets: tuple[int, ...] = SEED_OFFSETS,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for q in qubit_counts:
        for n in sample_sizes:
            for offset in seed_offsets:
                exact = exact_kernel(make_subset_features(n, offset), q)
                for shots in shot_budgets:
                    row = spectrum_row(exact, q, shots, sampling_rng(q, n, shots, offset))
                    rows.append({"qubits": q, "n": n, "shots": shots, "seed_offset": offset, **row})
    return rows


def aer_versus_binomial(
    *, sample_size: int = 40, shots: int = 512, seed_offset: int = 0
) -> dict[str, float]:
    """Compare standardized entry errors of Aer sampling and the binomial model (q = 2).

    Errors are divided by sqrt(K(1-K)/shots); both samplers should give mean ~0
    and variance ~1.  Entries with K(1-K) < 0.01 are excluded (near-deterministic).
    """
    features = make_subset_features(sample_size, seed_offset)
    exact = exact_kernel(features, 2)
    pairs = [(i, j) for i in range(sample_size) for j in range(i + 1, sample_size)]
    backend = AerSimulator(method="statevector")
    circuits = transpile(
        [compute_uncompute_circuit(features[i], features[j]) for i, j in pairs],
        backend,
        seed_transpiler=DEFAULT_SEED,
        optimization_level=0,
        num_processes=1,
    )
    result = backend.run(circuits, shots=shots, seed_simulator=DEFAULT_SEED).result()
    aer = np.asarray([result.get_counts(k).get("00", 0) / shots for k in range(len(pairs))])
    truth = np.asarray([exact[i, j] for i, j in pairs])
    binomial = sample_kernel_binomial(exact, shots, sampling_rng(2, sample_size, shots, seed_offset))
    binomial_values = np.asarray([binomial[i, j] for i, j in pairs])
    keep = truth * (1.0 - truth) >= 0.01
    scale = np.sqrt(truth[keep] * (1.0 - truth[keep]) / shots)
    out: dict[str, float] = {"entries_compared": int(keep.sum()), "shots": shots}
    for name, values in (("aer", aer), ("binomial", binomial_values)):
        z = (values[keep] - truth[keep]) / scale
        out[f"{name}_z_mean"] = float(z.mean())
        out[f"{name}_z_variance"] = float(z.var())
    return out


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per (q, n, shots) means over seeds, plus per-(q, n) log-log slope of |mean lambda_min|."""
    cells: list[dict[str, Any]] = []
    for q in sorted({r["qubits"] for r in rows}):
        for n in sorted({r["n"] for r in rows}):
            group = [r for r in rows if r["qubits"] == q and r["n"] == n]
            shots_list = sorted({r["shots"] for r in group})
            means = []
            for shots in shots_list:
                subset = [r for r in group if r["shots"] == shots]
                means.append(float(np.mean([r["lambda_min_raw"] for r in subset])))
                cells.append(
                    {
                        "qubits": q,
                        "n": n,
                        "shots": shots,
                        "exact_ranks": sorted({r["exact_rank"] for r in subset}),
                        "nullity_mean": float(np.mean([r["nullity"] for r in subset])),
                        "lambda_min_exact_mean": float(np.mean([r["lambda_min_exact"] for r in subset])),
                        "negative_count_mean": float(np.mean([r["negative_eigenvalue_count"] for r in subset])),
                        "lambda_min_raw_mean": means[-1],
                        "psd_fraction": float(np.mean([r["psd"] for r in subset])),
                        "mean_offdiagonal_k": float(np.mean([r["mean_offdiagonal_k"] for r in subset])),
                    }
                )
            slope = float(np.polyfit(np.log(shots_list), np.log(np.abs(means)), 1)[0])
            for cell in cells:
                if cell["qubits"] == q and cell["n"] == n:
                    cell["loglog_slope"] = slope
    return cells


def save_plot(cells: list[dict[str, Any]], path: Path) -> None:
    figure, axis = plt.subplots(figsize=(7.5, 5))
    colors = plt.cm.viridis(np.linspace(0, 0.9, len({(c["qubits"], c["n"]) for c in cells})))
    for color, key in zip(colors, sorted({(c["qubits"], c["n"]) for c in cells})):
        group = sorted((c for c in cells if (c["qubits"], c["n"]) == key), key=lambda c: c["shots"])
        axis.plot(
            [c["shots"] for c in group],
            [abs(c["lambda_min_raw_mean"]) for c in group],
            marker="o", ms=3, color=color, label=f"q={key[0]}, n={key[1]}",
        )
    shots = np.asarray(sorted({c["shots"] for c in cells}), dtype=float)
    anchor = abs(next(c for c in cells if c["qubits"] == 2 and c["n"] == 40 and c["shots"] == shots[0])["lambda_min_raw_mean"])
    axis.plot(shots, anchor * np.sqrt(shots[0] / shots), "k--", label="1/√shots (anchored q=2, n=40)")
    axis.set_xscale("log", base=2)
    axis.set_yscale("log")
    axis.set_xlabel("shots")
    axis.set_ylabel("|mean λ_min(raw)| over 5 seeds")
    axis.set_title("Raw finite-shot kernel minimum eigenvalue (unrepaired)")
    axis.legend(fontsize=7, ncol=2)
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def write_artifacts(results_dir: Path) -> dict[str, Any]:
    rows = run_sweep()
    report = {
        "description": "Exact kernel rank versus raw finite-shot PSD violation (binomial sampling model, unrepaired).",
        "settings": {
            "qubit_counts": list(QUBIT_COUNTS),
            "sample_sizes": list(SAMPLE_SIZES),
            "shot_budgets": list(SHOT_BUDGETS),
            "seed_offsets": list(SEED_OFFSETS),
            "base_seed": DEFAULT_SEED,
            "psd_tolerance": PSD_TOLERANCE,
            "rank_tolerance": "max(n, 4^q) * eps * lambda_max",
            "repair_applied": False,
        },
        "aer_versus_binomial_q2_n40": aer_versus_binomial(),
        "summary": summarize(rows),
        "rows": rows,
    }
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / RESULT_FILENAME).write_text(json.dumps(report, indent=2) + "\n")
    save_plot(report["summary"], results_dir / PLOT_FILENAME)
    return report
