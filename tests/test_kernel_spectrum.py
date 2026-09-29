import numpy as np
import pytest

from praxis_quantum_lab.kernel_experiment import feature_statevectors, fidelity_quantum_kernel
from praxis_quantum_lab.kernel_spectrum import (
    aer_versus_binomial,
    exact_kernel,
    exact_rank,
    make_subset_features,
    sample_kernel_binomial,
    sampling_rng,
    spectrum_row,
)


@pytest.mark.parametrize("q", [1, 2, 3])
def test_exact_rank_respects_bound(q):
    features = make_subset_features(24, 0)
    kernel = exact_kernel(features, q)
    assert exact_rank(kernel, q) <= min(24, 4**q)
    assert np.linalg.eigvalsh(kernel).min() > -1e-12


def test_two_qubit_map_reproduces_existing_kernel():
    features = make_subset_features(16, 1)
    states = feature_statevectors(features)
    np.testing.assert_allclose(exact_kernel(features, 2), fidelity_quantum_kernel(states, states), atol=1e-12)


def test_binomial_sampling_is_seed_deterministic():
    kernel = exact_kernel(make_subset_features(16, 0), 2)
    first = sample_kernel_binomial(kernel, 128, sampling_rng(2, 16, 128, 0))
    second = sample_kernel_binomial(kernel, 128, sampling_rng(2, 16, 128, 0))
    other = sample_kernel_binomial(kernel, 128, sampling_rng(2, 16, 128, 1))
    np.testing.assert_array_equal(first, second)
    assert not np.array_equal(first, other)
    np.testing.assert_array_equal(first, first.T)
    np.testing.assert_array_equal(np.diag(first), np.ones(16))


def test_rank_deficient_kernel_is_indefinite_at_low_shots():
    kernel = exact_kernel(make_subset_features(40, 0), 2)
    for offset in range(3):
        row = spectrum_row(kernel, 2, 128, sampling_rng(2, 40, 128, offset))
        assert row["nullity"] == 24
        assert not row["psd"]
        assert row["negative_eigenvalue_count"] > 0


def test_aer_matches_binomial_model_statistically():
    check = aer_versus_binomial(sample_size=20, shots=512)
    for name in ("aer", "binomial"):
        assert abs(check[f"{name}_z_mean"]) < 0.25
        assert 0.6 < check[f"{name}_z_variance"] < 1.5
