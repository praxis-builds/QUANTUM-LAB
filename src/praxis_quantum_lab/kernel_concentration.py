"""Concentration of exact fidelity-kernel values as the qubit count grows.

Exact local statevectors only; no sampling.  Shot counts reported here are
derived from binomial standard deviations, not simulated.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from praxis_quantum_lab.kernel_experiment import fidelity_quantum_kernel
from praxis_quantum_lab.kernel_spectrum import make_subset_features

QUBIT_COUNTS = tuple(range(1, 9))
LAYER_COUNTS = (1, 2, 4)
BANDWIDTHS = (0.1, 0.3, 1.0)
SAMPLE_SIZE = 40
SUBSET = 0
RESULT_FILENAME = "kernel_concentration.json"
PLOT_FILENAME = "kernel_concentration_variance.png"


def layered_feature_map(values: np.ndarray, num_qubits: int, *, layers: int = 1, alpha: float = 1.0) -> QuantumCircuit:
    """Repeat (H, RZ(a x), RY((a x)^2) per qubit, then a CZ chain) ``layers`` times."""
    vector = np.asarray(values, dtype=np.float64) * alpha
    if vector.ndim != 1 or vector.size < 1:
        raise ValueError("values must be a non-empty 1-D feature vector.")
    if num_qubits < 1 or layers < 1:
        raise ValueError("num_qubits and layers must be positive.")
    circuit = QuantumCircuit(num_qubits, name=f"layered_q{num_qubits}_L{layers}")
    for _ in range(layers):
        for qubit in range(num_qubits):
            value = float(vector[qubit % vector.size])
            circuit.h(qubit)
            circuit.rz(value, qubit)
            circuit.ry(value * value, qubit)
        for qubit in range(num_qubits - 1):
            circuit.cz(qubit, qubit + 1)
    return circuit


def layered_kernel(features: np.ndarray, num_qubits: int, *, layers: int = 1, alpha: float = 1.0) -> np.ndarray:
    states = np.asarray(
        [Statevector.from_instruction(layered_feature_map(row, num_qubits, layers=layers, alpha=alpha)).data for row in features],
        dtype=np.complex128,
    )
    return fidelity_quantum_kernel(states, states)


def product_formula_kernel(features: np.ndarray, num_qubits: int, *, alpha: float = 1.0) -> np.ndarray:
    """k0^ceil(q/2) * k1^floor(q/2) from single-qubit fidelities (valid for one layer)."""
    per_feature = [layered_kernel(features[:, [f]], 1, alpha=alpha) for f in range(features.shape[1])]
    kernel = np.ones((len(features), len(features)))
    for qubit in range(num_qubits):
        kernel = kernel * per_feature[qubit % features.shape[1]]
    return kernel


def concentration_stats(kernel: np.ndarray) -> dict[str, float]:
    """Off-diagonal mean, variance, median and derived shot counts."""
    values = np.asarray(kernel, dtype=np.float64)[np.triu_indices(kernel.shape[0], k=1)]
    mean, variance, median = float(values.mean()), float(values.var()), float(np.median(values))
    binomial = median * (1.0 - median)
    return {
        "mean": mean,
        "variance": variance,
        "median": median,
        "shots_to_resolve_spread": binomial / variance if variance > 0 else float("inf"),
        "shots_relative_resolution_at_median": (1.0 - median) / median if median > 0 else float("inf"),
    }


def run_concentration_sweep(
    *,
    qubit_counts: tuple[int, ...] = QUBIT_COUNTS,
    layer_counts: tuple[int, ...] = LAYER_COUNTS,
    bandwidths: tuple[float, ...] = BANDWIDTHS,
) -> list[dict[str, Any]]:
    features = make_subset_features(SAMPLE_SIZE, SUBSET)
    rows = []
    for layers in layer_counts:
        for alpha in bandwidths:
            for q in qubit_counts:
                kernel = layered_kernel(features, q, layers=layers, alpha=alpha)
                row = {"layers": layers, "alpha": alpha, "qubits": q, **concentration_stats(kernel)}
                if layers == 1:
                    row["product_formula_max_abs_error"] = float(
                        np.max(np.abs(kernel - product_formula_kernel(features, q, alpha=alpha)))
                    )
                rows.append(row)
    return rows


def save_variance_plot(rows: list[dict[str, Any]], path: Path) -> None:
    figure, axis = plt.subplots(figsize=(8, 5.5))
    styles = {1: "-", 2: "--", 4: ":"}
    colors = {0.1: "#2ca02c", 0.3: "#ff7f0e", 1.0: "#1f77b4"}
    for layers in sorted({r["layers"] for r in rows}):
        for alpha in sorted({r["alpha"] for r in rows}):
            group = sorted((r for r in rows if r["layers"] == layers and r["alpha"] == alpha), key=lambda r: r["qubits"])
            axis.plot(
                [r["qubits"] for r in group], [r["variance"] for r in group],
                styles.get(layers, "-"), marker="o", ms=3, color=colors.get(alpha), label=f"L={layers}, α={alpha}",
            )
    qubits = np.arange(1, 9)
    axis.plot(qubits, 4.0**-qubits, "k-", lw=0.8, alpha=0.5, label="Haar ≈ 4^-q")
    axis.set_yscale("log")
    axis.set_xlabel("qubits q")
    axis.set_ylabel("Var(K) over off-diagonal pairs (40 points, exact)")
    axis.set_title("Fidelity-kernel concentration vs qubit count")
    axis.legend(fontsize=7, ncol=2)
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def write_artifacts(results_dir: Path) -> dict[str, Any]:
    rows = run_concentration_sweep()
    report = {
        "description": "Exact fidelity-kernel concentration versus qubit count, layers and feature bandwidth.",
        "settings": {
            "data": f"make_subset_features({SAMPLE_SIZE}, {SUBSET}) (seed 20260928)",
            "qubit_counts": list(QUBIT_COUNTS),
            "layer_counts": list(LAYER_COUNTS),
            "bandwidths": list(BANDWIDTHS),
            "layer": "H, RZ(alpha x), RY((alpha x)^2) per qubit, features cyclic, then CZ chain",
            "shots_to_resolve_spread": "median(1 - median) / Var(K)",
            "shots_relative_resolution_at_median": "(1 - median) / median",
            "sampling": "none; exact statevectors",
        },
        "rows": rows,
    }
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / RESULT_FILENAME).write_text(json.dumps(report, indent=2) + "\n")
    save_variance_plot(rows, results_dir / PLOT_FILENAME)
    return report
