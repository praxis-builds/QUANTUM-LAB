"""Metrics that can separate exact, raw, repaired and classical kernel models.

Same fixed 40-point 28/12 split as the PSD repair study.  Repaired kernels are
transductive (the repair saw test inputs, never test labels) and change the
data.  Accuracy on 12 test points is reported with a Wilson interval to show
how little it can resolve.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics.pairwise import rbf_kernel
from sklearn.svm import SVC

from praxis_quantum_lab.finite_shot_kernel import _scaled_rbf_gamma
from praxis_quantum_lab.finite_shot_psd import PSD_REPAIR_RESULT_FILENAME
from praxis_quantum_lab.kernel_negativity import wilson_interval
from praxis_quantum_lab.repair_comparison import fixed_split_data, load_saved_raw_kernels, repair_both

RESULT_FILENAME = "repair_metric_comparison.json"
PLOT_FILENAME = "repair_metric_comparison.png"
MODEL_ORDER = ("raw", "clipped", "higham")


def kernel_alignment(first: np.ndarray, second: np.ndarray) -> float:
    """<K1, K2>_F / (||K1||_F ||K2||_F)."""
    a, b = np.asarray(first, dtype=np.float64), np.asarray(second, dtype=np.float64)
    if a.shape != b.shape:
        raise ValueError("kernels must have the same shape.")
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    if denominator == 0:
        raise ValueError("alignment is undefined for a zero matrix.")
    return float(np.sum(a * b) / denominator)


def svc_decision(train_kernel: np.ndarray, test_kernel: np.ndarray, y_train: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Fit SVC(kernel='precomputed', C=1) and return (decision values, predictions)."""
    classifier = SVC(kernel="precomputed", C=1.0).fit(train_kernel, y_train)
    return classifier.decision_function(test_kernel), classifier.predict(test_kernel)


def decision_agreement(values: np.ndarray, reference: np.ndarray) -> dict[str, float]:
    """Pearson r and sign agreement between two decision-function vectors."""
    a, b = np.asarray(values, dtype=np.float64), np.asarray(reference, dtype=np.float64)
    if a.shape != b.shape or a.ndim != 1 or a.size < 2:
        raise ValueError("need two equal-length 1-D vectors with at least two entries.")
    if a.std() == 0 or b.std() == 0:
        pearson = float("nan")
    else:
        pearson = float(np.corrcoef(a, b)[0, 1])
    agree = int(np.sum(np.sign(a) == np.sign(b)))
    return {"pearson_r": pearson, "sign_agreement": agree, "points": int(a.size)}


def accuracy_with_wilson(y_true: np.ndarray, predictions: np.ndarray) -> dict[str, Any]:
    correct = int(np.sum(np.asarray(y_true) == np.asarray(predictions)))
    total = int(len(y_true))
    low, high = wilson_interval(correct, total)
    return {"correct": correct, "total": total, "accuracy": correct / total, "wilson95": [low, high]}


def _model_metrics(train, test, data, exact_train, exact_decision) -> dict[str, Any]:
    decision, predictions = svc_decision(train, test, data["y_train"])
    return {
        "alignment_to_exact_train": kernel_alignment(train, exact_train),
        **decision_agreement(decision, exact_decision),
        **accuracy_with_wilson(data["y_test"], predictions),
        "decision_values": decision.tolist(),
    }


def run_metric_comparison(saved_path: Path) -> dict[str, Any]:
    data = fixed_split_data()
    n_train = len(data["x_train"])
    exact = data["exact_full"]
    exact_train, exact_test = exact[:n_train, :n_train], exact[n_train:, :n_train]
    exact_decision, exact_predictions = svc_decision(exact_train, exact_test, data["y_train"])

    gamma = _scaled_rbf_gamma(data["x_train"])
    rbf_train = rbf_kernel(data["x_train"], data["x_train"], gamma=gamma)
    rbf_test = rbf_kernel(data["x_test"], data["x_train"], gamma=gamma)

    references = {
        "exact": {
            **accuracy_with_wilson(data["y_test"], exact_predictions),
            "decision_values": exact_decision.tolist(),
        },
        "rbf": {"gamma": gamma, **_model_metrics(rbf_train, rbf_test, data, exact_train, exact_decision)},
    }
    rows = []
    for item in load_saved_raw_kernels(saved_path):
        repaired = repair_both(item["raw"])
        matrices = {"raw": item["raw"], "clipped": repaired["clipped"], "higham": repaired["higham"]}
        rows.append(
            {
                "shots": item["shots"],
                "replicate": item["replicate"],
                "shot_seed": item["shot_seed"],
                **{
                    name: _model_metrics(m[:n_train, :n_train], m[n_train:, :n_train], data, exact_train, exact_decision)
                    for name, m in matrices.items()
                },
            }
        )
    return {
        "description": "Alignment, decision-function agreement and Wilson accuracy for exact, raw, repaired and RBF kernels.",
        "settings": {
            "split": "fixed 40-point subset, 28 train / 12 test, seed 20260928, scaler fitted on train",
            "classifier": "SVC(kernel='precomputed', C=1.0)",
            "alignment_block": "28x28 training block, versus exact",
            "decision_reference": "exact-kernel SVC decision_function on the 12 test points",
            "wilson_z": 1.96,
            "raw_source": f"results/{PSD_REPAIR_RESULT_FILENAME} (read only)",
            "repairs_change_the_data": True,
            "repaired_evaluation_scope": "transductive: repairs used the full 40x40 kernel including test inputs, never test labels",
        },
        "references": references,
        "summary": summarize(rows),
        "rows": rows,
    }


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for shots in sorted({r["shots"] for r in rows}):
        group = [r for r in rows if r["shots"] == shots]
        entry: dict[str, Any] = {"shots": shots, "replicates": len(group)}
        for name in MODEL_ORDER:
            for field in ("alignment_to_exact_train", "pearson_r", "sign_agreement", "accuracy"):
                values = [r[name][field] for r in group]
                entry[f"{name}_{field}_mean"] = float(np.mean(values))
                entry[f"{name}_{field}_min"] = float(np.min(values))
        entry["higham_highest_alignment_count"] = int(
            sum(
                r["higham"]["alignment_to_exact_train"]
                >= max(r["raw"]["alignment_to_exact_train"], r["clipped"]["alignment_to_exact_train"])
                for r in group
            )
        )
        out.append(entry)
    return out


def save_metric_plot(report: dict[str, Any], path: Path) -> None:
    rows, refs = report["rows"], report["references"]
    colors = {"raw": "#7f7f7f", "clipped": "#d62728", "higham": "#1f77b4"}
    offsets = {"raw": -0.12, "clipped": 0.0, "higham": 0.12}
    budgets = sorted({r["shots"] for r in rows})
    figure, axes = plt.subplots(1, 3, figsize=(16, 4.8))
    for axis, field, label in (
        (axes[0], "alignment_to_exact_train", "1 − alignment to exact (train block)"),
        (axes[1], "pearson_r", "1 − Pearson r vs exact decision values"),
    ):
        for name in MODEL_ORDER:
            xs = [budgets.index(r["shots"]) + offsets[name] for r in rows]
            axis.scatter(xs, [max(1 - r[name][field], 1e-7) for r in rows], s=14, color=colors[name], label=name)
        axis.axhline(max(1 - refs["rbf"][field], 1e-7), color="green", ls="--", label="RBF (classical)")
        axis.set_yscale("log")
        axis.set_xticks(range(len(budgets)), [str(b) for b in budgets])
        axis.set_xlabel("shots")
        axis.set_ylabel(label)
        axis.legend(fontsize=7)
    axis = axes[2]
    entries = [("exact", refs["exact"]), ("RBF", refs["rbf"])]
    for name in MODEL_ORDER:
        for shots in budgets:
            first = next(r for r in rows if r["shots"] == shots)
            entries.append((f"{name} {shots} r0", first[name]))
    for index, (label, entry) in enumerate(entries):
        low, high = entry["wilson95"]
        axis.errorbar(index, entry["accuracy"], yerr=[[entry["accuracy"] - low], [high - entry["accuracy"]]], fmt="o", ms=4, color="black")
    axis.set_xticks(range(len(entries)), [e[0] for e in entries], rotation=90, fontsize=7)
    axis.set_ylim(0, 1.05)
    axis.set_ylabel("test accuracy, Wilson 95% (n = 12)")
    axis.set_title("Accuracy cannot separate these models")
    figure.suptitle("Fixed 28/12 split; repairs are transductive and change the data", fontsize=9)
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def write_artifacts(results_dir: Path) -> dict[str, Any]:
    report = run_metric_comparison(results_dir / PSD_REPAIR_RESULT_FILENAME)
    (results_dir / RESULT_FILENAME).write_text(json.dumps(report, indent=2) + "\n")
    save_metric_plot(report, results_dir / PLOT_FILENAME)
    return report
