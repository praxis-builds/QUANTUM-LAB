import numpy as np
import pytest

from praxis_quantum_lab.kernel_concentration import (
    concentration_stats,
    layered_feature_map,
    layered_kernel,
    product_formula_kernel,
    run_concentration_sweep,
)
from praxis_quantum_lab.kernel_spectrum import exact_kernel, feature_map_q, make_subset_features


@pytest.mark.parametrize("q", [1, 2, 3, 4])
def test_single_layer_unit_bandwidth_reproduces_existing_map(q):
    features = make_subset_features(8, 0)
    assert layered_feature_map(features[0], q) == feature_map_q(features[0], q)
    np.testing.assert_allclose(layered_kernel(features, q), exact_kernel(features, q), atol=1e-12)


@pytest.mark.parametrize("q", [2, 3, 5])
def test_final_cz_chain_cancels_for_one_layer(q):
    features = make_subset_features(8, 1)
    np.testing.assert_allclose(layered_kernel(features, q, alpha=0.3), product_formula_kernel(features, q, alpha=0.3), atol=1e-12)


def test_two_layers_break_the_product_formula():
    features = make_subset_features(8, 1)
    difference = np.abs(layered_kernel(features, 3, layers=2) - product_formula_kernel(features, 3))
    assert difference.max() > 1e-3


def test_concentration_stats_hand_made():
    kernel = np.array([[1.0, 0.2, 0.4], [0.2, 1.0, 0.6], [0.4, 0.6, 1.0]])
    stats = concentration_stats(kernel)
    assert stats["mean"] == pytest.approx(0.4)
    assert stats["variance"] == pytest.approx(np.var([0.2, 0.4, 0.6]))
    assert stats["median"] == pytest.approx(0.4)
    assert stats["shots_to_resolve_spread"] == pytest.approx(0.4 * 0.6 / np.var([0.2, 0.4, 0.6]))
    assert stats["shots_relative_resolution_at_median"] == pytest.approx(0.6 / 0.4)


def test_sweep_rows_and_validation():
    rows = run_concentration_sweep(qubit_counts=(1, 2), layer_counts=(1,), bandwidths=(1.0,))
    assert [r["qubits"] for r in rows] == [1, 2]
    assert all(r["product_formula_max_abs_error"] < 1e-12 for r in rows)
    with pytest.raises(ValueError):
        layered_feature_map(np.array([0.1, 0.2]), 2, layers=0)
