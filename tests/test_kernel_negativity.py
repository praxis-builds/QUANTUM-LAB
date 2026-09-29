import math

import numpy as np
import pytest

from praxis_quantum_lab.kernel_negativity import (
    eigenvalue_noise_scales,
    negativity_rng,
    normal_cdf,
    observe_negativity,
    predict_negativity,
    sample_kernels_binomial,
    wilson_interval,
)
from praxis_quantum_lab.kernel_spectrum import exact_kernel, make_subset_features


def test_normal_cdf_known_values():
    np.testing.assert_allclose(normal_cdf([0.0, 1.96, -1.96]), [0.5, 0.9750021, 0.0249979], atol=1e-6)


def test_wilson_interval_known_value_and_edges():
    low, high = wilson_interval(10, 12)
    assert low == pytest.approx(0.5520, abs=1e-3)
    assert high == pytest.approx(0.9530, abs=1e-3)
    assert wilson_interval(0, 200)[0] == 0.0
    assert wilson_interval(200, 200)[1] == 1.0
    with pytest.raises(ValueError):
        wilson_interval(3, 2)


def test_predicted_count_bounded_and_vanishes_with_shots():
    kernel = exact_kernel(make_subset_features(8, 0), 3)
    for shots in (128, 2048):
        prediction = predict_negativity(kernel, shots)
        assert 0.0 <= prediction["predicted_negative_count"] <= 8.0
        assert 0.0 <= prediction["predicted_psd_probability"] <= 1.0
    large = predict_negativity(kernel, 10**9)
    assert large["predicted_negative_count"] < 1e-6
    assert large["predicted_psd_probability"] > 1 - 1e-6


def test_identity_kernel_has_no_noise():
    prediction = predict_negativity(np.eye(5), 128)
    np.testing.assert_array_equal(prediction["scales"], np.zeros(5))
    assert prediction["predicted_negative_count"] == 0.0
    assert prediction["predicted_psd_probability"] == 1.0


def test_noise_scale_matches_monte_carlo():
    kernel = exact_kernel(make_subset_features(8, 1), 2)
    shots = 512
    eigenvalues, scales = eigenvalue_noise_scales(kernel, shots)
    vectors = np.linalg.eigh(kernel)[1]
    stack = sample_kernels_binomial(kernel, shots, 20000, np.random.default_rng(7))
    first_order = np.einsum("ik,dij,jk->dk", vectors, stack - kernel, vectors)
    np.testing.assert_allclose(first_order.std(axis=0), scales, rtol=0.05)
    np.testing.assert_allclose(first_order.mean(axis=0), 0.0, atol=4 * scales.max() / math.sqrt(20000))


def test_sampled_stack_shape_symmetry_and_determinism():
    kernel = exact_kernel(make_subset_features(8, 0), 2)
    first = sample_kernels_binomial(kernel, 128, 5, negativity_rng(2, 8, 128, 0))
    second = sample_kernels_binomial(kernel, 128, 5, negativity_rng(2, 8, 128, 0))
    assert first.shape == (5, 8, 8)
    np.testing.assert_array_equal(first, second)
    np.testing.assert_array_equal(first, np.swapaxes(first, 1, 2))
    np.testing.assert_array_equal(np.diagonal(first, axis1=1, axis2=2), 1.0)


def test_observe_negativity_is_deterministic_and_consistent():
    kernel = exact_kernel(make_subset_features(16, 0), 2)
    first = observe_negativity(kernel, 128, 50, negativity_rng(2, 16, 128, 0))
    second = observe_negativity(kernel, 128, 50, negativity_rng(2, 16, 128, 0))
    assert first == second
    low, high = first["observed_psd_wilson95"]
    assert low <= first["observed_psd_rate"] <= high
    assert first["observed_mean_negative_count"] > 0


def test_second_order_shift_matches_monte_carlo_mean():
    from praxis_quantum_lab.kernel_negativity import second_order_shifts

    kernel = exact_kernel(make_subset_features(8, 0), 3)
    shots = 2048
    shifts = second_order_shifts(kernel, shots)
    eigenvalues, scales = eigenvalue_noise_scales(kernel, shots)
    draws = 20000
    sampled = np.linalg.eigvalsh(sample_kernels_binomial(kernel, shots, draws, np.random.default_rng(11)))
    observed_shift = sampled.mean(axis=0) - eigenvalues
    np.testing.assert_allclose(observed_shift, shifts, atol=4 * scales.max() / math.sqrt(draws) + 1e-12, rtol=0.3)
    assert shifts[0] < 0  # the lowest eigenvalue is pushed down


def test_second_order_prediction_reduces_to_first_order_without_noise():
    from praxis_quantum_lab.kernel_negativity import predict_negativity_second_order, second_order_shifts

    np.testing.assert_array_equal(second_order_shifts(np.eye(4), 128), np.zeros(4))
    assert predict_negativity_second_order(np.eye(4), 128)["predicted_psd_probability"] == 1.0
