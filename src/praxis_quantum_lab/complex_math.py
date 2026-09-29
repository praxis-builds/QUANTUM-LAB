"""The minimal complex-number operations used by the state-vector lessons.

Quantum amplitudes are complex numbers.  Their squared magnitudes—not the
amplitudes themselves—become measurement probabilities.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray


def as_complex_vector(values: ArrayLike) -> NDArray[np.complex128]:
    """Return a one-dimensional vector with an explicit complex dtype."""
    vector = np.asarray(values, dtype=np.complex128)
    if vector.ndim != 1:
        raise ValueError("A quantum state must be a one-dimensional vector.")
    if vector.size == 0:
        raise ValueError("A quantum state cannot be empty.")
    return vector


def magnitude_squared(value: complex | NDArray[np.complex128]) -> np.ndarray:
    """Compute |z|² using complex conjugation, the probability rule's core."""
    return np.real(np.conjugate(value) * value)


def is_power_of_two(value: int) -> bool:
    """Whether a state length can represent an integral number of qubits."""
    return value > 0 and (value & (value - 1)) == 0
