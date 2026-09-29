import numpy as np
import pytest

from praxis_quantum_lab.kernel_experiment import make_dataset
from praxis_quantum_lab.repair_comparison import clipping_step_distances
from praxis_quantum_lab.repeated_model_comparison import (
    cluster_bootstrap_ci,
    evaluate_split,
    run_repeated_comparison,
    split_kernels,
    split_rng,
)


def _small_split():
    features, labels = make_dataset(seed=20260928)
    order = np.argsort(labels, kind="stable")
    train = np.concatenate((order[:30], order[-30:]))
    test = np.concatenate((order[30:40], order[-40:-30]))
    return features[train], features[test], labels[train], labels[test]


def test_inductive_higham_leaves_test_block_raw_and_repairs_train_block():
    x_train, x_test, _, _ = _small_split()
    kernels = split_kernels(x_train, x_test, split_rng(0))
    np.testing.assert_array_equal(kernels["higham_ind"][1], kernels["raw"][1])
    assert np.linalg.eigvalsh(kernels["higham_ind"][0]).min() >= -1e-10
    np.testing.assert_array_equal(np.diag(kernels["higham_ind"][0]), 1.0)
    assert not np.array_equal(kernels["higham_trans"][1], kernels["raw"][1])
    assert kernels["exact"][0].shape == (60, 60) and kernels["exact"][1].shape == (20, 60)


def test_split_kernels_are_seed_deterministic():
    x_train, x_test, _, _ = _small_split()
    first = split_kernels(x_train, x_test, split_rng(3))
    second = split_kernels(x_train, x_test, split_rng(3))
    for name in first:
        np.testing.assert_array_equal(first[name][0], second[name][0])


def test_evaluate_split_reference_values():
    x_train, x_test, y_train, y_test = _small_split()
    metrics = evaluate_split(split_kernels(x_train, x_test, split_rng(0)), y_train, y_test)
    assert metrics["exact"]["r_vs_exact"] == pytest.approx(1.0)
    assert metrics["exact"]["alignment_vs_exact"] == pytest.approx(1.0)
    assert metrics["rbf"]["r_vs_rbf"] == pytest.approx(1.0)
    assert 0.0 <= metrics["raw"]["accuracy"] <= 1.0


def test_cluster_bootstrap_ci_properties():
    rng = np.random.default_rng(0)
    values = np.repeat(np.arange(10, dtype=float), 5)
    clusters = np.repeat(np.arange(10), 5)
    first = cluster_bootstrap_ci(values, clusters, resamples=2000, rng=np.random.default_rng(1))
    second = cluster_bootstrap_ci(values, clusters, resamples=2000, rng=np.random.default_rng(1))
    assert first == second
    assert first["mean"] == pytest.approx(4.5)
    assert first["ci95_low"] < 4.5 < first["ci95_high"]
    assert first["excludes_zero"]
    constant = cluster_bootstrap_ci(np.zeros(50), clusters, resamples=100, rng=rng)
    assert constant["ci95_low"] == constant["ci95_high"] == 0.0 and not constant["excludes_zero"]
    with pytest.raises(ValueError):
        cluster_bootstrap_ci(np.zeros(3), np.zeros(4), rng=rng)


def test_small_repeated_run_structure():
    report = run_repeated_comparison(n_splits=2, n_repeats=2)
    assert len(report["rows"]) == 4
    assert {"raw", "clipped", "higham_trans", "higham_ind", "rbf"} == set(report["summary"]["vs_exact"])


def test_clipping_step_projection_never_farther_than_raw():
    rng = np.random.default_rng(5)
    factors = rng.normal(size=(12, 3))
    covariance = factors @ factors.T + 0.05 * np.eye(12)
    scale = 1 / np.sqrt(np.diag(covariance))
    exact = covariance * scale[:, None] * scale[None, :]
    noise = np.triu(rng.normal(scale=0.08, size=(12, 12)), 1)
    raw = exact + noise + noise.T
    result = clipping_step_distances(raw, exact)
    assert result["projection_only_to_exact"] <= result["raw_to_exact"] + 1e-12
    assert result["projection_mean_diagonal"] >= 1.0 - 1e-12
