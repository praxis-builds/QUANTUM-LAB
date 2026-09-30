"""Read-only repair comparison for the Kernel Observatory.

Everything here is deterministic post-processing of saved files; nothing is sampled
and nothing is written. The saved raw finite-shot matrices come from
``results/finite_shot_kernel_psd_repair.json`` (which also holds the clipped
matrices). Higham matrices were never saved, so they are recomputed from the raw
matrices with the same function used in docs/higham-vs-clipping.md, and the
distances are cross-checked against ``results/higham_vs_clipping.json``. If the
two disagree, the build fails closed rather than showing inconsistent numbers.
Both repairs change the data and are transductive (they use test inputs, not labels).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

MAX_FILE_BYTES = 8 * 1024 * 1024
CONSISTENCY_TOLERANCE = 1e-8


def _read_json(path: Path) -> Any:
    with Path(path).open("rb") as source:
        data = source.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"{Path(path).name} exceeds the size limit.")
    return json.loads(data)


def _finite(value: object) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def load_saved_distances(path: Path) -> dict[tuple[int, int], dict[str, float]]:
    """Schema-checked distances to exact from the milestone-2 Higham-vs-clipping result."""
    try:
        rows = _read_json(path)["rows"]
        if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
            raise ValueError("Invalid rows.")
        out: dict[tuple[int, int], dict[str, float]] = {}
        for row in rows:
            key = (row["shots"], row["replicate"])
            if type(key[0]) is not int or type(key[1]) is not int or key in out:
                raise ValueError("Invalid or duplicate row key.")
            distances = {name: row[name]["distance_to_exact"] for name in ("raw", "clipped", "higham")}
            if not all(_finite(value) and value >= 0 for value in distances.values()):
                raise ValueError("Invalid distance.")
            out[key] = distances
        return out
    except (KeyError, TypeError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Invalid Higham-vs-clipping result schema.") from error


def _matrix(value: object, size: int) -> np.ndarray:
    if not isinstance(value, list) or len(value) != size or any(
        not isinstance(row, list) or len(row) != size or not all(_finite(v) for v in row) for row in value
    ):
        raise ValueError("Invalid saved matrix.")
    return np.asarray(value, dtype=np.float64)


def build_kernel_repairs(psd_path: Path, distances_path: Path) -> dict[str, Any]:
    """Recompute Higham matrices and spectra; verify distances against the saved result."""
    from .finite_shot_kernel import training_kernel_diagnostics
    from .nearest_correlation import higham_nearest_correlation
    from .repair_comparison import fixed_split_data

    try:
        report = _read_json(psd_path)
        metadata = report["metadata"]
        size = metadata["sample_size"]
        if type(size) is not int or not 1 <= size <= 200:
            raise ValueError("Invalid matrix size.")
        budgets = report["shot_budgets"]
    except (KeyError, TypeError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Invalid saved PSD report schema.") from error
    saved_distances = load_saved_distances(distances_path)

    data = fixed_split_data()
    if data["source_indices"] != metadata.get("stratified_subset_source_indices_in_train_then_test_order"):
        raise ValueError("The saved report does not use the fixed split this view reconstructs.")
    exact = data["exact_full"]
    if exact.shape != (size, size):
        raise ValueError("Exact kernel size mismatch.")

    entries = []
    try:
        for budget in budgets:
            for replicate in budget["replicates"]:
                key = (budget["shots"], replicate["replicate"])
                raw = _matrix(replicate["raw_sampled_kernel_matrix"], size)
                clipped = _matrix(replicate["psd_repaired_kernel_matrix"], size)
                higham, iterations = higham_nearest_correlation(raw)
                distances = {
                    "raw": float(np.linalg.norm(raw - exact)),
                    "clipped": float(np.linalg.norm(clipped - exact)),
                    "higham": float(np.linalg.norm(higham - exact)),
                }
                saved = saved_distances.get(key)
                if saved is None or any(abs(distances[k] - saved[k]) > CONSISTENCY_TOLERANCE for k in distances):
                    raise ValueError(f"Distances for {key} disagree with results/higham_vs_clipping.json.")
                diagnostics = training_kernel_diagnostics(higham)
                entries.append({
                    "shots": key[0],
                    "replicate": key[1],
                    "shot_seed": replicate["shot_seed"],
                    "higham_matrix": higham.tolist(),
                    "higham_iterations": int(iterations),
                    "higham_diagnostics": {
                        **diagnostics,
                        "frobenius_distance_from_raw": float(np.linalg.norm(higham - raw)),
                    },
                    "eigenvalues": {
                        "raw": np.linalg.eigvalsh(raw).tolist(),
                        "clipped": np.linalg.eigvalsh(clipped).tolist(),
                        "higham": np.linalg.eigvalsh(higham).tolist(),
                    },
                    "distance_to_exact": distances,
                })
    except (KeyError, TypeError) as error:
        raise ValueError("Invalid saved PSD report schema.") from error
    if len(entries) != len(saved_distances):
        raise ValueError("The two saved results cover different matrices.")
    return {
        "description": "Raw, clipped and Higham kernels compared with the exact kernel on the same 40 inputs.",
        "exact_eigenvalues": np.linalg.eigvalsh(exact).tolist(),
        "sources": {
            "raw_and_clipped": "results/finite_shot_kernel_psd_repair.json (saved)",
            "higham": "recomputed from the saved raw matrices (deterministic; not sampled)",
            "distances_checked_against": "results/higham_vs_clipping.json",
        },
        "repairs_change_the_data": True,
        "evaluation_scope": "transductive: repairs use the full 40x40 matrix including test inputs, never test labels",
        "entries": entries,
    }
