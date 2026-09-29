"""Compare eigenvalue clipping with Higham nearest-correlation repair.

Inputs are the raw finite-shot kernels already saved by the PSD repair study
(read only).  Both repairs change the data and are transductive: they repair
the full 40-point subset kernel, which includes test inputs but not labels.
"""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from praxis_quantum_lab.finite_shot_kernel import _make_fixed_split
from praxis_quantum_lab.finite_shot_psd import PSD_REPAIR_RESULT_FILENAME, repair_kernel_psd
from praxis_quantum_lab.kernel_experiment import DEFAULT_SEED, feature_statevectors, fidelity_quantum_kernel
from praxis_quantum_lab.nearest_correlation import higham_nearest_correlation

SAMPLE_SIZE = 40
TEST_FRACTION = 0.30
RESULT_FILENAME = "higham_vs_clipping.json"
PLOT_FILENAME = "higham_vs_clipping_distances.png"


def fixed_split_data() -> dict[str, Any]:
    """The PSD study's fixed 28/12 split, train rows first, with the exact 40x40 kernel."""
    x_train, x_test, y_train, y_test, indices = _make_fixed_split(
        sample_size=SAMPLE_SIZE, seed=DEFAULT_SEED, test_fraction=TEST_FRACTION
    )
    x_full = np.concatenate((x_train, x_test), axis=0)
    states = feature_statevectors(x_full)
    return {
        "x_train": x_train,
        "x_test": x_test,
        "y_train": y_train,
        "y_test": y_test,
        "source_indices": indices,
        "exact_full": fidelity_quantum_kernel(states, states),
    }


def load_saved_raw_kernels(path: Path) -> list[dict[str, Any]]:
    """Read the 15 raw finite-shot matrices saved by the PSD study (no writes)."""
    report = json.loads(Path(path).read_text())
    kernels = []
    for budget in report["shot_budgets"]:
        for replicate in budget["replicates"]:
            kernels.append(
                {
                    "shots": int(budget["shots"]),
                    "replicate": int(replicate["replicate"]),
                    "shot_seed": int(replicate["shot_seed"]),
                    "raw": np.asarray(replicate["raw_sampled_kernel_matrix"], dtype=np.float64),
                }
            )
    return kernels


def repair_both(raw: np.ndarray) -> dict[str, Any]:
    started = perf_counter()
    clipped = repair_kernel_psd(raw)
    clip_seconds = perf_counter() - started
    started = perf_counter()
    higham, iterations = higham_nearest_correlation(raw)
    higham_seconds = perf_counter() - started
    return {
        "clipped": clipped,
        "higham": higham,
        "higham_iterations": iterations,
        "clip_seconds": clip_seconds,
        "higham_seconds": higham_seconds,
    }


def distance_row(raw: np.ndarray, exact: np.ndarray, repaired: dict[str, Any]) -> dict[str, Any]:
    frob = lambda a, b: float(np.linalg.norm(a - b, ord="fro"))  # noqa: E731
    return {
        "raw": {
            "distance_to_exact": frob(raw, exact),
            "lambda_min": float(np.linalg.eigvalsh(raw).min()),
        },
        "clipped": {
            "distance_to_raw": frob(repaired["clipped"], raw),
            "distance_to_exact": frob(repaired["clipped"], exact),
            "lambda_min": float(np.linalg.eigvalsh(repaired["clipped"]).min()),
            "iterations": 1,
        },
        "higham": {
            "distance_to_raw": frob(repaired["higham"], raw),
            "distance_to_exact": frob(repaired["higham"], exact),
            "lambda_min": float(np.linalg.eigvalsh(repaired["higham"]).min()),
            "iterations": int(repaired["higham_iterations"]),
        },
    }


def run_comparison(saved_path: Path) -> dict[str, Any]:
    exact = fixed_split_data()["exact_full"]
    rows = []
    for item in load_saved_raw_kernels(saved_path):
        repaired = repair_both(item["raw"])
        rows.append(
            {
                "shots": item["shots"],
                "replicate": item["replicate"],
                "shot_seed": item["shot_seed"],
                **distance_row(item["raw"], exact, repaired),
            }
        )
    return {
        "description": "Clipping vs Higham nearest-correlation repair of saved raw finite-shot kernels.",
        "settings": {
            "source": f"results/{PSD_REPAIR_RESULT_FILENAME} (read only)",
            "sample_size": SAMPLE_SIZE,
            "seed": DEFAULT_SEED,
            "test_fraction": TEST_FRACTION,
            "norm": "Frobenius, full 40x40 matrix",
            "repairs_change_the_data": True,
            "evaluation_scope": "transductive: repairs use the full subset kernel including test inputs, never test labels",
            "higham": "Dykstra-corrected alternating projections, PSD cone and unit diagonal, tolerance 1e-10",
            "clipping": "existing repair_kernel_psd: clip negative eigenvalues, rescale to unit diagonal",
        },
        "rows": rows,
    }


def save_distance_plot(report: dict[str, Any], path: Path) -> None:
    rows = report["rows"]
    figure, (left, right) = plt.subplots(1, 2, figsize=(11, 4.5))
    positions = np.arange(len(rows))
    labels = [f"{r['shots']}/{r['replicate']}" for r in rows]
    for key, marker in (("raw", "s"), ("clipped", "o"), ("higham", "^")):
        left.plot(positions, [r[key]["distance_to_exact"] for r in rows], marker, label=key)
    left.set_xticks(positions, labels, rotation=90, fontsize=7)
    left.set_xlabel("shots / replicate")
    left.set_ylabel("‖K − K_exact‖_F")
    left.set_title("Distance to the exact kernel")
    left.legend(fontsize=8)
    ratio = [r["higham"]["distance_to_exact"] / r["clipped"]["distance_to_exact"] for r in rows]
    right.plot(positions, ratio, "k^")
    right.axhline(1.0, color="grey", lw=1, ls="--")
    right.set_xticks(positions, labels, rotation=90, fontsize=7)
    right.set_xlabel("shots / replicate")
    right.set_ylabel("‖Higham − exact‖ / ‖clip − exact‖")
    right.set_title("Below 1: Higham closer to exact")
    figure.suptitle("Both repairs change the data; transductive (test inputs, no labels)", fontsize=9)
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def write_artifacts(results_dir: Path) -> dict[str, Any]:
    report = run_comparison(results_dir / PSD_REPAIR_RESULT_FILENAME)
    (results_dir / RESULT_FILENAME).write_text(json.dumps(report, indent=2) + "\n")
    save_distance_plot(report, results_dir / PLOT_FILENAME)
    return report


CLIPPING_STEP_RESULT_FILENAME = "clipping_step_diagnostic.json"


def clipping_step_distances(raw: np.ndarray, exact: np.ndarray) -> dict[str, float]:
    """Split clipping into its PSD projection and its unit-diagonal rescale (milestone 2, B-P3)."""
    from praxis_quantum_lab.nearest_correlation import project_psd

    projected = project_psd(raw)
    clipped = repair_kernel_psd(raw)
    upper = np.triu_indices(raw.shape[0], k=1)
    frob = lambda a: float(np.linalg.norm(a - exact, ord="fro"))  # noqa: E731
    return {
        "raw_to_exact": frob(raw),
        "projection_only_to_exact": frob(projected),
        "projection_plus_rescale_to_exact": frob(clipped),
        "projection_mean_diagonal": float(np.diag(projected).mean()),
        "exact_mean_offdiagonal": float(exact[upper].mean()),
        "raw_mean_offdiagonal": float(raw[upper].mean()),
        "clipped_mean_offdiagonal": float(clipped[upper].mean()),
    }


def write_clipping_step_diagnostic(results_dir: Path) -> dict[str, Any]:
    exact = fixed_split_data()["exact_full"]
    rows = [
        {"shots": item["shots"], "replicate": item["replicate"], **clipping_step_distances(item["raw"], exact)}
        for item in load_saved_raw_kernels(results_dir / PSD_REPAIR_RESULT_FILENAME)
    ]
    report = {
        "description": "Clipping split into PSD projection and unit-diagonal rescale; distances to the exact kernel.",
        "source": f"results/{PSD_REPAIR_RESULT_FILENAME} (read only)",
        "repairs_change_the_data": True,
        "rows": rows,
    }
    (results_dir / CLIPPING_STEP_RESULT_FILENAME).write_text(json.dumps(report, indent=2) + "\n")
    return report
