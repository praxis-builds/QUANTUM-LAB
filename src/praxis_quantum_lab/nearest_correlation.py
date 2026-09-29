"""Higham (2002) nearest correlation matrix by alternating projections.

Dykstra-corrected alternating projections between the PSD cone and the
unit-diagonal affine set, in the unweighted Frobenius norm.  The result is a
repaired matrix: it is not the measured data.
"""

from __future__ import annotations

import numpy as np

from praxis_quantum_lab.finite_shot_kernel import PSD_TOLERANCE

DEFAULT_TOLERANCE = 1e-10
DEFAULT_MAX_ITERATIONS = 20_000


def project_psd(matrix: np.ndarray) -> np.ndarray:
    """Frobenius projection of a symmetric matrix onto the PSD cone."""
    eigenvalues, eigenvectors = np.linalg.eigh((matrix + matrix.T) / 2.0)
    projected = (eigenvectors * np.maximum(eigenvalues, 0.0)) @ eigenvectors.T
    return (projected + projected.T) / 2.0


def project_unit_diagonal(matrix: np.ndarray) -> np.ndarray:
    """Frobenius projection onto symmetric matrices with unit diagonal."""
    projected = np.array(matrix, dtype=np.float64, copy=True)
    np.fill_diagonal(projected, 1.0)
    return projected


def higham_nearest_correlation(
    matrix: np.ndarray,
    *,
    tolerance: float = DEFAULT_TOLERANCE,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> tuple[np.ndarray, int]:
    """Return (nearest correlation matrix, iterations used).

    Stops when the relative changes of both iterates and their mutual distance
    fall below ``tolerance`` and the unit-diagonal iterate has minimum
    eigenvalue >= -PSD_TOLERANCE.  Raises if that does not happen within
    ``max_iterations``.  The input is never mutated.
    """
    source = np.asarray(matrix, dtype=np.float64)
    if source.ndim != 2 or source.shape[0] != source.shape[1] or source.size == 0:
        raise ValueError("matrix must be a non-empty square matrix.")
    if not np.isfinite(source).all():
        raise ValueError("matrix must contain only finite values.")
    if not np.allclose(source, source.T, atol=PSD_TOLERANCE, rtol=0.0):
        raise ValueError("matrix must be symmetric within tolerance.")
    if tolerance <= 0 or max_iterations < 1:
        raise ValueError("tolerance and max_iterations must be positive.")

    correction = np.zeros_like(source)
    unit_diagonal = (source + source.T) / 2.0
    psd = unit_diagonal
    for iteration in range(1, max_iterations + 1):
        previous_psd, previous_unit = psd, unit_diagonal
        shifted = unit_diagonal - correction
        psd = project_psd(shifted)
        correction = psd - shifted
        unit_diagonal = project_unit_diagonal(psd)
        scale = max(np.linalg.norm(unit_diagonal), 1.0)
        change = max(
            np.linalg.norm(psd - previous_psd) / scale,
            np.linalg.norm(unit_diagonal - previous_unit) / scale,
            np.linalg.norm(unit_diagonal - psd) / scale,
        )
        if change < tolerance and np.linalg.eigvalsh(unit_diagonal).min() >= -PSD_TOLERANCE:
            return unit_diagonal, iteration
    raise RuntimeError(f"Higham projection did not converge in {max_iterations} iterations.")
