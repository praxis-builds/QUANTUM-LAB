"""First-order prediction of which kernel eigenvalues finite-shot noise turns negative.

For an exact eigenpair (lambda_k, u_k) the first-order sampled eigenvalue is
lambda_k + u_k^T E u_k, where E has zero diagonal and independent upper-triangle
entries of variance K_ij (1 - K_ij) / shots.  Predictions use the exact kernel
only; sampled kernels are drawn from the binomial model and never repaired.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from praxis_quantum_lab.finite_shot_kernel import PSD_TOLERANCE
from praxis_quantum_lab.kernel_experiment import DEFAULT_SEED
from praxis_quantum_lab.kernel_spectrum import exact_kernel, make_subset_features

QUBIT_COUNTS = (2, 3)
SAMPLE_SIZES = tuple(range(8, 17))
SHOT_BUDGETS = (128, 512, 2048, 8192)
SUBSETS = (0, 1, 2, 3, 4)
DRAWS_PER_KERNEL = 200
RESULT_FILENAME = "eigenvalue_negativity_prediction.json"
PLOT_FILENAME = "eigenvalue_negativity_calibration.png"

_erfc = np.frompyfunc(math.erfc, 1, 1)


def normal_cdf(values: np.ndarray | float) -> np.ndarray:
    """Standard normal CDF via math.erfc (no SciPy dependency)."""
    array = np.asarray(values, dtype=np.float64)
    return (0.5 * _erfc(-array / math.sqrt(2.0))).astype(np.float64)


def wilson_interval(successes: int, trials: int, *, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if trials < 1 or not 0 <= successes <= trials:
        raise ValueError("need 0 <= successes <= trials and trials >= 1.")
    p = successes / trials
    denominator = 1.0 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denominator
    half = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denominator
    return max(0.0, centre - half), min(1.0, centre + half)


def eigenvalue_noise_scales(kernel: np.ndarray, shots: int) -> tuple[np.ndarray, np.ndarray]:
    """Return ascending exact eigenvalues and s_k = sd(u_k^T E u_k)."""
    if not isinstance(shots, int) or shots < 1:
        raise ValueError("shots must be a positive integer.")
    matrix = np.asarray(kernel, dtype=np.float64)
    eigenvalues, eigenvectors = np.linalg.eigh(matrix)
    variances = np.clip(matrix * (1.0 - matrix), 0.0, None) / shots
    np.fill_diagonal(variances, 0.0)
    squared = eigenvectors**2
    # 4 * sum_{i<j} = 2 * sum_{i != j} because the variance matrix is symmetric.
    scales = np.sqrt(2.0 * np.einsum("ik,ij,jk->k", squared, variances, squared))
    return eigenvalues, scales


def predict_negativity(kernel: np.ndarray, shots: int) -> dict[str, Any]:
    """First-order N_hat and P(PSD); P(PSD) assumes independent eigenvalue terms."""
    eigenvalues, scales = eigenvalue_noise_scales(kernel, shots)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(scales > 0, eigenvalues / scales, np.where(eigenvalues < -PSD_TOLERANCE, -np.inf, np.inf))
    p_negative = normal_cdf(-z)
    near_zero = int(np.sum(np.abs(eigenvalues) < 3.0 * scales))
    spacing = float((eigenvalues[1] - eigenvalues[0]) / scales[0]) if scales[0] > 0 else math.inf
    return {
        "eigenvalues": eigenvalues,
        "scales": scales,
        "p_negative": p_negative,
        "predicted_negative_count": float(p_negative.sum()),
        "predicted_psd_probability": float(np.prod(1.0 - p_negative)),
        "bottom_spacing_over_s": spacing,
        "min_lambda_over_s": float(np.min(z)),
        "eigenvalues_within_3s_of_zero": near_zero,
    }


def second_order_shifts(kernel: np.ndarray, shots: int) -> np.ndarray:
    """Expected second-order eigenvalue shifts E[sum_{j!=k} (u_j^T E u_k)^2 / (lambda_k - lambda_j)].

    Post-hoc diagnostic (not part of the pre-registered first-order model).
    Exactly degenerate pairs are skipped.
    """
    if not isinstance(shots, int) or shots < 1:
        raise ValueError("shots must be a positive integer.")
    matrix = np.asarray(kernel, dtype=np.float64)
    eigenvalues, eigenvectors = np.linalg.eigh(matrix)
    variances = np.clip(matrix * (1.0 - matrix), 0.0, None) / shots
    np.fill_diagonal(variances, 0.0)
    squared = eigenvectors**2
    products = eigenvectors[:, :, np.newaxis] * eigenvectors[:, np.newaxis, :]
    # Var(u_j^T E u_k) for every pair (j, k); the diagonal equals s_k^2.
    coupling = squared.T @ variances @ squared + np.einsum("ajk,ab,bjk->jk", products, variances, products)
    gaps = eigenvalues[:, np.newaxis] - eigenvalues[np.newaxis, :]
    with np.errstate(divide="ignore", invalid="ignore"):
        terms = np.where(gaps != 0.0, coupling / gaps, 0.0)
    return terms.sum(axis=1)


def predict_negativity_second_order(kernel: np.ndarray, shots: int) -> dict[str, float]:
    """Post-hoc: first-order Gaussian around lambda_k + second-order mean shift."""
    eigenvalues, scales = eigenvalue_noise_scales(kernel, shots)
    shifted = eigenvalues + second_order_shifts(kernel, shots)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(scales > 0, shifted / scales, np.where(shifted < -PSD_TOLERANCE, -np.inf, np.inf))
    p_negative = normal_cdf(-z)
    return {
        "predicted_negative_count": float(p_negative.sum()),
        "predicted_psd_probability": float(np.prod(1.0 - p_negative)),
    }


def sample_kernels_binomial(
    kernel: np.ndarray, shots: int, draws: int, rng: np.random.Generator
) -> np.ndarray:
    """Draw a (draws, n, n) stack of symmetric unit-diagonal binomial kernels."""
    size = kernel.shape[0]
    upper = np.triu_indices(size, k=1)
    values = rng.binomial(shots, np.clip(kernel[upper], 0.0, 1.0), size=(draws, upper[0].size)) / shots
    stack = np.broadcast_to(np.eye(size), (draws, size, size)).copy()
    stack[:, upper[0], upper[1]] = values
    stack[:, upper[1], upper[0]] = values
    return stack


def observe_negativity(
    kernel: np.ndarray, shots: int, draws: int, rng: np.random.Generator
) -> dict[str, Any]:
    eigenvalues = np.linalg.eigvalsh(sample_kernels_binomial(kernel, shots, draws, rng))
    negatives = (eigenvalues < -PSD_TOLERANCE).sum(axis=1)
    psd_count = int(np.sum(negatives == 0))
    low, high = wilson_interval(psd_count, draws)
    return {
        "draws": draws,
        "observed_psd_count": psd_count,
        "observed_psd_rate": psd_count / draws,
        "observed_psd_wilson95": [low, high],
        "observed_mean_negative_count": float(negatives.mean()),
    }


def negativity_rng(q: int, n: int, shots: int, subset: int) -> np.random.Generator:
    return np.random.default_rng([DEFAULT_SEED, q, n, shots, subset, 1])


def run_negativity_sweep(
    *,
    qubit_counts: tuple[int, ...] = QUBIT_COUNTS,
    sample_sizes: tuple[int, ...] = SAMPLE_SIZES,
    shot_budgets: tuple[int, ...] = SHOT_BUDGETS,
    subsets: tuple[int, ...] = SUBSETS,
    draws: int = DRAWS_PER_KERNEL,
) -> list[dict[str, Any]]:
    """One row per exact kernel and shot count: prediction versus 200 sampled draws."""
    rows: list[dict[str, Any]] = []
    for q in qubit_counts:
        for n in sample_sizes:
            for subset in subsets:
                kernel = exact_kernel(make_subset_features(n, subset), q)
                for shots in shot_budgets:
                    prediction = predict_negativity(kernel, shots)
                    post_hoc = predict_negativity_second_order(kernel, shots)
                    observed = observe_negativity(kernel, shots, draws, negativity_rng(q, n, shots, subset))
                    low, high = observed["observed_psd_wilson95"]
                    rows.append(
                        {
                            "qubits": q,
                            "n": n,
                            "shots": shots,
                            "subset": subset,
                            "lambda_min_exact": float(prediction["eigenvalues"][0]),
                            "bottom_spacing_over_s": prediction["bottom_spacing_over_s"],
                            "min_lambda_over_s": prediction["min_lambda_over_s"],
                            "eigenvalues_within_3s_of_zero": prediction["eigenvalues_within_3s_of_zero"],
                            "predicted_negative_count": prediction["predicted_negative_count"],
                            "predicted_psd_probability": prediction["predicted_psd_probability"],
                            **observed,
                            "psd_prediction_inside_wilson95": bool(
                                low <= prediction["predicted_psd_probability"] <= high
                            ),
                            "post_hoc_second_order_negative_count": post_hoc["predicted_negative_count"],
                            "post_hoc_second_order_psd_probability": post_hoc["predicted_psd_probability"],
                        }
                    )
    return rows


def summarize_by_config(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = sorted({(r["qubits"], r["n"], r["shots"]) for r in rows})
    out = []
    for q, n, shots in keys:
        group = [r for r in rows if (r["qubits"], r["n"], r["shots"]) == (q, n, shots)]
        mean = lambda field: float(np.mean([r[field] for r in group]))  # noqa: E731
        out.append(
            {
                "qubits": q,
                "n": n,
                "shots": shots,
                "kernels": len(group),
                "predicted_negative_count_mean": mean("predicted_negative_count"),
                "observed_negative_count_mean": mean("observed_mean_negative_count"),
                "predicted_psd_probability_mean": mean("predicted_psd_probability"),
                "observed_psd_rate_mean": mean("observed_psd_rate"),
                "kernels_with_psd_prediction_inside_wilson95": int(
                    sum(r["psd_prediction_inside_wilson95"] for r in group)
                ),
            }
        )
    return out


SPACING_BIN_EDGES = (0.0, 0.5, 1.0, 2.0, 4.0, math.inf)


def summarize_by_spacing(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Gap between observed and predicted, binned by bottom spacing relative to s_1."""
    out = []
    for low, high in zip(SPACING_BIN_EDGES[:-1], SPACING_BIN_EDGES[1:]):
        group = [r for r in rows if low <= r["bottom_spacing_over_s"] < high]
        if not group:
            continue
        gap = [r["observed_mean_negative_count"] - r["predicted_negative_count"] for r in group]
        psd_gap = [r["observed_psd_rate"] - r["predicted_psd_probability"] for r in group]
        gap_2 = [r["observed_mean_negative_count"] - r["post_hoc_second_order_negative_count"] for r in group]
        psd_gap_2 = [r["observed_psd_rate"] - r["post_hoc_second_order_psd_probability"] for r in group]
        out.append(
            {
                "spacing_over_s_range": [low, high if math.isfinite(high) else None],
                "kernel_rows": len(group),
                "mean_negative_gap_observed_minus_predicted": float(np.mean(gap)),
                "mean_abs_negative_gap": float(np.mean(np.abs(gap))),
                "mean_psd_gap_observed_minus_predicted": float(np.mean(psd_gap)),
                "fraction_psd_prediction_inside_wilson95": float(
                    np.mean([r["psd_prediction_inside_wilson95"] for r in group])
                ),
                "post_hoc_second_order_mean_negative_gap": float(np.mean(gap_2)),
                "post_hoc_second_order_mean_psd_gap": float(np.mean(psd_gap_2)),
                "post_hoc_second_order_fraction_inside_wilson95": float(
                    np.mean(
                        [
                            r["observed_psd_wilson95"][0]
                            <= r["post_hoc_second_order_psd_probability"]
                            <= r["observed_psd_wilson95"][1]
                            for r in group
                        ]
                    )
                ),
            }
        )
    return out


def save_calibration_plot(rows: list[dict[str, Any]], path: Path) -> None:
    figure, (left, right, extra) = plt.subplots(1, 3, figsize=(17, 5.2))
    colors = {2: "#1f77b4", 3: "#d62728"}
    for q in sorted({r["qubits"] for r in rows}):
        group = [r for r in rows if r["qubits"] == q]
        predicted = np.array([r["predicted_psd_probability"] for r in group])
        observed = np.array([r["observed_psd_rate"] for r in group])
        bounds = np.array([r["observed_psd_wilson95"] for r in group])
        left.errorbar(
            predicted, observed, yerr=[observed - bounds[:, 0], bounds[:, 1] - observed],
            fmt="o", ms=2.5, elinewidth=0.6, alpha=0.6, color=colors.get(q), label=f"q={q}",
        )
        right.scatter(
            [r["predicted_negative_count"] for r in group],
            [r["observed_mean_negative_count"] for r in group],
            s=8, alpha=0.6, color=colors.get(q), label=f"q={q}",
        )
        extra.errorbar(
            [r["post_hoc_second_order_psd_probability"] for r in group], observed,
            yerr=[observed - bounds[:, 0], bounds[:, 1] - observed],
            fmt="o", ms=2.5, elinewidth=0.6, alpha=0.6, color=colors.get(q), label=f"q={q}",
        )
    left.plot([0, 1], [0, 1], "k--", lw=1, label="y = x")
    left.set_xlabel("predicted P(PSD) (first order, independence)")
    left.set_ylabel("observed PSD rate (200 draws, Wilson 95%)")
    left.set_title("PSD calibration, one point per exact kernel × shots")
    top = max(max(r["predicted_negative_count"] for r in rows), max(r["observed_mean_negative_count"] for r in rows))
    right.plot([0, top], [0, top], "k--", lw=1, label="y = x")
    right.set_xlabel("predicted negative count N̂")
    right.set_ylabel("observed mean negative count")
    right.set_title("Negative eigenvalue count")
    extra.plot([0, 1], [0, 1], "k--", lw=1, label="y = x")
    extra.set_xlabel("P(PSD) with second-order mean shift (post hoc)")
    extra.set_ylabel("observed PSD rate (200 draws, Wilson 95%)")
    extra.set_title("Post-hoc second-order calibration")
    for axis in (left, right, extra):
        axis.legend(fontsize=8)
    figure.suptitle("Binomial finite-shot model, n = 8–16, q ∈ {2, 3}; raw kernels, no repair", fontsize=10)
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def write_artifacts(results_dir: Path) -> dict[str, Any]:
    rows = run_negativity_sweep()
    report = {
        "description": "First-order per-eigenvalue negativity prediction versus binomial finite-shot sampling (raw, unrepaired).",
        "settings": {
            "qubit_counts": list(QUBIT_COUNTS),
            "sample_sizes": list(SAMPLE_SIZES),
            "shot_budgets": list(SHOT_BUDGETS),
            "subsets": list(SUBSETS),
            "draws_per_kernel": DRAWS_PER_KERNEL,
            "base_seed": DEFAULT_SEED,
            "rng": "default_rng([base_seed, q, n, shots, subset, 1])",
            "negative_threshold": -PSD_TOLERANCE,
            "psd_probability_assumption": "independent first-order eigenvalue terms",
            "repair_applied": False,
        },
        "by_config": summarize_by_config(rows),
        "by_bottom_spacing": summarize_by_spacing(rows),
        "rows": rows,
    }
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / RESULT_FILENAME).write_text(json.dumps(report, indent=2) + "\n")
    save_calibration_plot(rows, results_dir / PLOT_FILENAME)
    return report


# --- Milestone 3: frozen second-order model on unseen configurations ---------

OOS_QUBIT_SAMPLE_SIZES = ((2, tuple(range(8, 15))), (3, tuple(range(8, 21))))
OOS_SHOT_BUDGETS = (256, 1024, 4096)
OOS_SUBSETS = tuple(range(5, 15))
OOS_RESULT_FILENAME = "second_order_negativity_test.json"
OOS_PLOT_FILENAME = "second_order_negativity_test.png"
DEGENERACY_RATIO = 0.5


def degeneracy_flag(kernel: np.ndarray, shots: int, *, ratio: float = DEGENERACY_RATIO) -> bool:
    """True if some pair k != j has |lambda_k - lambda_j| < ratio * s_k."""
    eigenvalues, scales = eigenvalue_noise_scales(kernel, shots)
    gaps = np.abs(eigenvalues[:, np.newaxis] - eigenvalues[np.newaxis, :])
    np.fill_diagonal(gaps, np.inf)
    return bool(np.any(gaps < ratio * scales[:, np.newaxis]))


def out_of_sample_rng(q: int, n: int, shots: int, subset: int) -> np.random.Generator:
    return np.random.default_rng([DEFAULT_SEED, q, n, shots, subset, 2])


def run_out_of_sample_sweep(
    *,
    qubit_sample_sizes: tuple[tuple[int, tuple[int, ...]], ...] = OOS_QUBIT_SAMPLE_SIZES,
    shot_budgets: tuple[int, ...] = OOS_SHOT_BUDGETS,
    subsets: tuple[int, ...] = OOS_SUBSETS,
    draws: int = DRAWS_PER_KERNEL,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for q, sample_sizes in qubit_sample_sizes:
        for n in sample_sizes:
            for subset in subsets:
                kernel = exact_kernel(make_subset_features(n, subset), q)
                for shots in shot_budgets:
                    first = predict_negativity(kernel, shots)
                    second = predict_negativity_second_order(kernel, shots)
                    observed = observe_negativity(kernel, shots, draws, out_of_sample_rng(q, n, shots, subset))
                    flagged = degeneracy_flag(kernel, shots)
                    rows.append(
                        {
                            "qubits": q,
                            "n": n,
                            "shots": shots,
                            "subset": subset,
                            "flagged_near_degenerate": flagged,
                            "bottom_spacing_over_s": first["bottom_spacing_over_s"],
                            "target_set": bool(not flagged and first["bottom_spacing_over_s"] >= 0.5),
                            "first_order_negative_count": first["predicted_negative_count"],
                            "first_order_psd_probability": first["predicted_psd_probability"],
                            "second_order_negative_count": second["predicted_negative_count"],
                            "second_order_psd_probability": second["predicted_psd_probability"],
                            **observed,
                        }
                    )
    return rows


def _inside(row: dict[str, Any], probability: float) -> bool:
    low, high = row["observed_psd_wilson95"]
    return bool(low <= probability <= high)


def summarize_out_of_sample(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def block(group: list[dict[str, Any]]) -> dict[str, Any]:
        if not group:
            return {"rows": 0}
        out: dict[str, Any] = {"rows": len(group)}
        for order in ("first_order", "second_order"):
            out[f"{order}_mean_abs_psd_gap"] = float(
                np.mean([abs(r["observed_psd_rate"] - r[f"{order}_psd_probability"]) for r in group])
            )
            out[f"{order}_inside_wilson95_share"] = float(
                np.mean([_inside(r, r[f"{order}_psd_probability"]) for r in group])
            )
            out[f"{order}_mean_abs_negative_gap"] = float(
                np.mean([abs(r["observed_mean_negative_count"] - r[f"{order}_negative_count"]) for r in group])
            )
        with_negatives = [r for r in group if r["first_order_negative_count"] >= 0.5]
        out["first_order_underpredicts_share_where_nhat_ge_half"] = (
            float(np.mean([r["observed_mean_negative_count"] >= r["first_order_negative_count"] for r in with_negatives]))
            if with_negatives
            else None
        )
        return out

    target = block([r for r in rows if r["target_set"]])
    ratio = target["first_order_mean_abs_psd_gap"] / target["second_order_mean_abs_psd_gap"] if target["rows"] else None
    targets = {
        "T1_second_order_mean_abs_psd_gap_le_0.08": bool(target["rows"] and target["second_order_mean_abs_psd_gap"] <= 0.08),
        "T2_second_order_inside_wilson_ge_0.54": bool(target["rows"] and target["second_order_inside_wilson95_share"] >= 0.54),
        "T3_first_over_second_psd_gap_ratio_ge_2": bool(ratio is not None and ratio >= 2.0),
        "T4_second_order_mean_abs_negative_gap_le_0.12": bool(target["rows"] and target["second_order_mean_abs_negative_gap"] <= 0.12),
    }
    return {
        "target_set": {**target, "first_over_second_psd_gap_ratio": ratio},
        "flagged": block([r for r in rows if r["flagged_near_degenerate"]]),
        "unflagged_spacing_below_half": block(
            [r for r in rows if not r["flagged_near_degenerate"] and not r["target_set"]]
        ),
        "targets": targets,
    }


def save_out_of_sample_plot(rows: list[dict[str, Any]], path: Path) -> None:
    figure, axes = plt.subplots(1, 3, figsize=(17, 5.2))
    panels = (
        (axes[0], "first_order_psd_probability", "target set: first order"),
        (axes[1], "second_order_psd_probability", "target set: second order (frozen)"),
        (axes[2], "second_order_psd_probability", "flagged near-degenerate: second order"),
    )
    for index, (axis, field, title) in enumerate(panels):
        group = [r for r in rows if (r["flagged_near_degenerate"] if index == 2 else r["target_set"])]
        for q, color in ((2, "#1f77b4"), (3, "#d62728")):
            sub = [r for r in group if r["qubits"] == q]
            if not sub:
                continue
            observed = np.array([r["observed_psd_rate"] for r in sub])
            bounds = np.array([r["observed_psd_wilson95"] for r in sub])
            axis.errorbar(
                [r[field] for r in sub], observed, yerr=[observed - bounds[:, 0], bounds[:, 1] - observed],
                fmt="o", ms=2.5, elinewidth=0.6, alpha=0.6, color=color, label=f"q={q} ({len(sub)})",
            )
        axis.plot([0, 1], [0, 1], "k--", lw=1)
        axis.set_xlabel("predicted P(PSD)")
        axis.set_ylabel("observed PSD rate (200 draws, Wilson 95%)")
        axis.set_title(title)
        axis.legend(fontsize=8)
    figure.suptitle("Out-of-sample: subsets 5-14, shots 256/1024/4096; raw binomial kernels, no repair", fontsize=10)
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def write_out_of_sample_artifacts(results_dir: Path) -> dict[str, Any]:
    rows = run_out_of_sample_sweep()
    report = {
        "description": "Pre-registered out-of-sample test of the frozen second-order negativity model.",
        "settings": {
            "qubit_sample_sizes": {str(q): list(ns) for q, ns in OOS_QUBIT_SAMPLE_SIZES},
            "shot_budgets": list(OOS_SHOT_BUDGETS),
            "subsets": list(OOS_SUBSETS),
            "draws_per_kernel": DRAWS_PER_KERNEL,
            "rng": "default_rng([20260928, q, n, shots, subset, 2])",
            "degeneracy_flag": "some pair k != j with |lambda_k - lambda_j| < 0.5 * s_k",
            "target_set": "not flagged and bottom spacing / s_1 >= 0.5",
            "repair_applied": False,
        },
        "summary": summarize_out_of_sample(rows),
        "rows": rows,
    }
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / OOS_RESULT_FILENAME).write_text(json.dumps(report, indent=2) + "\n")
    save_out_of_sample_plot(rows, results_dir / OOS_PLOT_FILENAME)
    return report
