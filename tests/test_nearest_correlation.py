import numpy as np
import pytest

from praxis_quantum_lab.finite_shot_psd import repair_kernel_psd
from praxis_quantum_lab.nearest_correlation import (
    higham_nearest_correlation,
    project_psd,
    project_unit_diagonal,
)


def _random_indefinite_correlation_like(rng: np.random.Generator, size: int) -> np.ndarray:
    upper = rng.uniform(-0.2, 1.0, size=(size, size))
    matrix = np.triu(upper, 1)
    matrix = matrix + matrix.T + np.eye(size)
    assert np.linalg.eigvalsh(matrix).min() < -1e-3
    return matrix


def test_known_three_by_three_example():
    # Higham (2002) example: nearest correlation matrix to this indefinite matrix.
    source = np.array([[1.0, 1.0, 0.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0]])
    repaired, iterations = higham_nearest_correlation(source)
    expected = np.array(
        [[1.0, 0.7607, 0.1573], [0.7607, 1.0, 0.7607], [0.1573, 0.7607, 1.0]]
    )
    np.testing.assert_allclose(repaired, expected, atol=1e-4)
    assert 1 < iterations < 20_000


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_output_is_psd_unit_diagonal_and_nearer_than_clipping(seed):
    source = _random_indefinite_correlation_like(np.random.default_rng(seed), 12)
    original = source.copy()
    repaired, _ = higham_nearest_correlation(source)
    np.testing.assert_array_equal(source, original)
    assert np.linalg.eigvalsh(repaired).min() >= -1e-10
    np.testing.assert_array_equal(np.diag(repaired), np.ones(12))
    np.testing.assert_allclose(repaired, repaired.T, atol=1e-14)
    clipped = repair_kernel_psd(source)
    assert np.linalg.norm(repaired - source) <= np.linalg.norm(clipped - source) + 1e-8


def test_correlation_matrix_is_a_fixed_point():
    rng = np.random.default_rng(3)
    factors = rng.normal(size=(6, 3))
    covariance = factors @ factors.T + 0.1 * np.eye(6)
    scale = 1 / np.sqrt(np.diag(covariance))
    correlation = covariance * scale[:, None] * scale[None, :]
    repaired, iterations = higham_nearest_correlation(correlation)
    np.testing.assert_allclose(repaired, correlation, atol=1e-9)
    assert iterations <= 3


def test_projections():
    matrix = np.array([[2.0, 0.0], [0.0, -1.0]])
    np.testing.assert_allclose(project_psd(matrix), [[2.0, 0.0], [0.0, 0.0]])
    np.testing.assert_array_equal(np.diag(project_unit_diagonal(matrix)), [1.0, 1.0])


def test_rejects_bad_input():
    with pytest.raises(ValueError):
        higham_nearest_correlation(np.array([[1.0, 0.2], [0.3, 1.0]]))
    with pytest.raises(ValueError):
        higham_nearest_correlation(np.ones((2, 3)))
    with pytest.raises(RuntimeError):
        higham_nearest_correlation(np.array([[1.0, 1.0, 0.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0]]), max_iterations=2)
