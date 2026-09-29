"""Paired comparison of exact, finite-shot, repaired and RBF kernels over 50 splits.

Splits follow the extended 5x10 evaluation.  Finite-shot kernels use the
binomial model at 512 shots.  Clipped and transductive Higham repairs use the
full matrix including test inputs (never labels) and change the data; the
inductive Higham variant repairs the training block only.  Bootstrap CIs
resample the 10 repeats, since folds share data; they are descriptive.
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
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.preprocessing import StandardScaler

from praxis_quantum_lab.finite_shot_psd import repair_kernel_psd
from praxis_quantum_lab.kernel_experiment import (
    DEFAULT_EXTENDED_REPEATS,
    DEFAULT_EXTENDED_SPLITS,
    DEFAULT_SEED,
    _precomputed_rbf_gamma,
    feature_statevectors,
    fidelity_quantum_kernel,
    make_dataset,
)
from praxis_quantum_lab.kernel_spectrum import sample_kernel_binomial
from praxis_quantum_lab.nearest_correlation import higham_nearest_correlation
from praxis_quantum_lab.repair_metrics import decision_agreement, kernel_alignment, svc_decision

SHOTS = 512
BOOTSTRAP_RESAMPLES = 10_000
MODELS = ("exact", "raw", "clipped", "higham_trans", "higham_ind", "rbf")
FINITE_SHOT_MODELS = ("raw", "clipped", "higham_trans", "higham_ind")
RESULT_FILENAME = "repeated_model_comparison.json"
PLOT_FILENAME = "repeated_model_comparison.png"
CONTRASTS = (
    ("clipped", "raw"),
    ("higham_trans", "clipped"),
    ("higham_trans", "raw"),
    ("higham_ind", "raw"),
    ("higham_trans", "higham_ind"),
)


def split_rng(split_index: int, shots: int = SHOTS) -> np.random.Generator:
    return np.random.default_rng([DEFAULT_SEED, split_index, shots, 3])


def split_kernels(x_train: np.ndarray, x_test: np.ndarray, rng: np.random.Generator, shots: int = SHOTS) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Return {model: (train block, test-to-train block)} for one split."""
    scaler = StandardScaler().fit(x_train)
    train, test = scaler.transform(x_train), scaler.transform(x_test)
    n_train = len(train)
    states = feature_statevectors(np.concatenate((train, test)))
    exact = fidelity_quantum_kernel(states, states)
    raw = sample_kernel_binomial(exact, shots, rng)
    clipped = repair_kernel_psd(raw)
    higham_full, _ = higham_nearest_correlation(raw)
    higham_train, _ = higham_nearest_correlation(raw[:n_train, :n_train])
    gamma = _precomputed_rbf_gamma(train)
    blocks = lambda m: (m[:n_train, :n_train], m[n_train:, :n_train])  # noqa: E731
    return {
        "exact": blocks(exact),
        "raw": blocks(raw),
        "clipped": blocks(clipped),
        "higham_trans": blocks(higham_full),
        "higham_ind": (higham_train, raw[n_train:, :n_train]),
        "rbf": (rbf_kernel(train, train, gamma=gamma), rbf_kernel(test, train, gamma=gamma)),
    }


def evaluate_split(kernels: dict[str, tuple[np.ndarray, np.ndarray]], y_train: np.ndarray, y_test: np.ndarray) -> dict[str, dict[str, float]]:
    decisions = {}
    accuracy = {}
    for name, (train, test) in kernels.items():
        decision, predictions = svc_decision(train, test, y_train)
        decisions[name] = decision
        accuracy[name] = float(np.mean(predictions == y_test))
    out = {}
    for name, (train, _) in kernels.items():
        out[name] = {
            "accuracy": accuracy[name],
            "r_vs_exact": decision_agreement(decisions[name], decisions["exact"])["pearson_r"],
            "r_vs_rbf": decision_agreement(decisions[name], decisions["rbf"])["pearson_r"],
            "alignment_vs_exact": kernel_alignment(train, kernels["exact"][0]),
            "alignment_vs_rbf": kernel_alignment(train, kernels["rbf"][0]),
        }
    return out


def cluster_bootstrap_ci(
    values: np.ndarray, clusters: np.ndarray, *, resamples: int = BOOTSTRAP_RESAMPLES, rng: np.random.Generator
) -> dict[str, float]:
    """Mean and percentile 95% CI, resampling whole clusters with replacement."""
    values, clusters = np.asarray(values, dtype=np.float64), np.asarray(clusters)
    if values.shape != clusters.shape or values.size == 0:
        raise ValueError("values and clusters must be equal-length and non-empty.")
    labels = np.unique(clusters)
    sums = np.array([values[clusters == label].sum() for label in labels])
    counts = np.array([np.sum(clusters == label) for label in labels])
    picks = rng.integers(0, len(labels), size=(resamples, len(labels)))
    means = sums[picks].sum(axis=1) / counts[picks].sum(axis=1)
    low, high = np.percentile(means, [2.5, 97.5])
    return {
        "mean": float(values.mean()),
        "ci95_low": float(low),
        "ci95_high": float(high),
        "excludes_zero": bool(low > 0 or high < 0),
    }


def run_repeated_comparison(
    *, n_splits: int = DEFAULT_EXTENDED_SPLITS, n_repeats: int = DEFAULT_EXTENDED_REPEATS, shots: int = SHOTS
) -> dict[str, Any]:
    features, labels = make_dataset(seed=DEFAULT_SEED)
    splitter = RepeatedStratifiedKFold(n_splits=n_splits, n_repeats=n_repeats, random_state=DEFAULT_SEED)
    rows = []
    for index, (train_idx, test_idx) in enumerate(splitter.split(features, labels)):
        kernels = split_kernels(features[train_idx], features[test_idx], split_rng(index, shots), shots)
        rows.append(
            {
                "split": index,
                "repeat": index // n_splits,
                "fold": index % n_splits,
                "metrics": evaluate_split(kernels, labels[train_idx], labels[test_idx]),
            }
        )
    return {"rows": rows, "summary": summarize(rows)}


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    clusters = np.array([r["repeat"] for r in rows])
    rng = np.random.default_rng([DEFAULT_SEED, 4])
    get = lambda model, metric: np.array([r["metrics"][model][metric] for r in rows])  # noqa: E731
    ci = lambda values: cluster_bootstrap_ci(values, clusters, rng=rng)  # noqa: E731
    summary: dict[str, Any] = {"means": {}, "vs_exact": {}, "vs_rbf": {}, "contrasts": {}}
    for model in MODELS:
        summary["means"][model] = {
            metric: float(get(model, metric).mean())
            for metric in ("accuracy", "r_vs_exact", "r_vs_rbf", "alignment_vs_exact", "alignment_vs_rbf")
        }
    for model in MODELS:
        if model != "exact":
            summary["vs_exact"][model] = {
                "accuracy_difference": ci(get(model, "accuracy") - get("exact", "accuracy")),
                "one_minus_r": ci(1.0 - get(model, "r_vs_exact")),
                "one_minus_alignment": ci(1.0 - get(model, "alignment_vs_exact")),
            }
        if model != "rbf":
            summary["vs_rbf"][model] = {
                "accuracy_difference": ci(get(model, "accuracy") - get("rbf", "accuracy")),
            }
    for first, second in CONTRASTS:
        summary["contrasts"][f"{first}_minus_{second}"] = {
            "accuracy": ci(get(first, "accuracy") - get(second, "accuracy")),
            "r_vs_exact": ci(get(first, "r_vs_exact") - get(second, "r_vs_exact")),
            "alignment_vs_exact": ci(get(first, "alignment_vs_exact") - get(second, "alignment_vs_exact")),
        }
    return summary


def save_forest_plot(summary: dict[str, Any], path: Path) -> None:
    figure, axes = plt.subplots(1, 3, figsize=(17, 5))
    entries = [(f"{m} − exact", summary["vs_exact"][m]["accuracy_difference"]) for m in MODELS if m != "exact"]
    entries += [(f"{m} − RBF", summary["vs_rbf"][m]["accuracy_difference"]) for m in MODELS if m != "rbf"]
    entries += [(f"{k.replace('_minus_', ' − ')}", v["accuracy"]) for k, v in summary["contrasts"].items()]
    _forest(axes[0], entries, "paired accuracy difference (16 test points per split)", log=False)
    _forest(axes[1], [(m, summary["vs_exact"][m]["one_minus_r"]) for m in MODELS if m != "exact"], "1 − Pearson r vs exact decision values", log=True)
    _forest(axes[2], [(m, summary["vs_exact"][m]["one_minus_alignment"]) for m in MODELS if m != "exact"], "1 − alignment vs exact (training block)", log=True)
    figure.suptitle("50 repeated splits (5×10), 512 shots binomial; cluster-bootstrap 95% CIs over repeats (descriptive); repairs change the data", fontsize=9)
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def _forest(axis, entries, xlabel, *, log: bool) -> None:
    for index, (label, stats) in enumerate(entries):
        axis.errorbar(
            stats["mean"], index,
            xerr=[[stats["mean"] - stats["ci95_low"]], [stats["ci95_high"] - stats["mean"]]],
            fmt="o", color="black" if not stats["excludes_zero"] else "#d62728", capsize=3,
        )
    axis.set_yticks(range(len(entries)), [e[0] for e in entries], fontsize=8)
    axis.invert_yaxis()
    if log:
        axis.set_xscale("log")
    else:
        axis.axvline(0.0, color="grey", ls="--", lw=1)
    axis.set_xlabel(xlabel)


def write_artifacts(results_dir: Path) -> dict[str, Any]:
    result = run_repeated_comparison()
    report = {
        "description": "Paired repeated-split comparison of exact, finite-shot (raw/clipped/Higham) and RBF kernels.",
        "settings": {
            "dataset": "make_dataset(seed=20260928), 80 points",
            "splits": "RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=20260928)",
            "shots": SHOTS,
            "raw_rng": "default_rng([20260928, split, 512, 3]), one binomial draw per split",
            "classifier": "SVC(kernel='precomputed', C=1.0)",
            "bootstrap": "cluster bootstrap over the 10 repeats, 10000 resamples, default_rng([20260928, 4]), percentile 95%",
            "bootstrap_caveat": "all splits reuse the same 80 points; CIs describe split variability on this data set, not generalisation; descriptive only",
            "repairs_change_the_data": True,
            "transductive_models": ["clipped", "higham_trans"],
            "inductive_models": ["higham_ind (training block repaired, raw test-to-train block)"],
        },
        **result,
    }
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / RESULT_FILENAME).write_text(json.dumps(report, indent=2) + "\n")
    save_forest_plot(report["summary"], results_dir / PLOT_FILENAME)
    return report
