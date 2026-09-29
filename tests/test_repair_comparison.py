import json
from pathlib import Path

import numpy as np

from praxis_quantum_lab.repair_comparison import (
    distance_row,
    fixed_split_data,
    load_saved_raw_kernels,
    repair_both,
)

SAVED = Path(__file__).resolve().parents[1] / "results" / "finite_shot_kernel_psd_repair.json"


def test_fixed_split_matches_saved_study_order():
    data = fixed_split_data()
    saved = json.loads(SAVED.read_text())["metadata"]
    assert data["source_indices"] == saved["stratified_subset_source_indices_in_train_then_test_order"]
    assert data["exact_full"].shape == (40, 40)
    assert len(data["x_train"]) == 28 and len(data["x_test"]) == 12


def test_loads_fifteen_raw_matrices_read_only():
    before = SAVED.read_bytes()
    kernels = load_saved_raw_kernels(SAVED)
    assert len(kernels) == 15
    assert sorted({k["shots"] for k in kernels}) == [128, 512, 2048]
    assert all(k["raw"].shape == (40, 40) for k in kernels)
    assert SAVED.read_bytes() == before


def test_repair_both_and_distance_row_on_small_matrix():
    raw = np.array([[1.0, 0.9, 0.1], [0.9, 1.0, 0.9], [0.1, 0.9, 1.0]])
    exact = np.array([[1.0, 0.8, 0.3], [0.8, 1.0, 0.8], [0.3, 0.8, 1.0]])
    row = distance_row(raw, exact, repair_both(raw))
    assert row["raw"]["lambda_min"] < 0
    assert row["higham"]["lambda_min"] >= -1e-10
    assert row["clipped"]["lambda_min"] >= -1e-10
    assert row["higham"]["distance_to_raw"] <= row["clipped"]["distance_to_raw"] + 1e-8
    # exact is a correlation matrix, so the projection cannot move away from it
    assert row["higham"]["distance_to_exact"] < row["raw"]["distance_to_exact"]
    assert row["higham"]["iterations"] >= 1 and row["clipped"]["iterations"] == 1
