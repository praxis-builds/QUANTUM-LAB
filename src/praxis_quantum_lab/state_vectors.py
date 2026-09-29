"""State-vector foundations implemented with NumPy rather than a quantum SDK.

Convention: basis states are ordered |0>, |1> for one qubit.  For several
qubits, ``tensor_product(a, b)`` produces the usual Kronecker product a ⊗ b.
This module intentionally keeps the linear algebra visible for study.
"""

from __future__ import annotations

from collections import Counter
from math import log2
from typing import Iterable

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .complex_math import as_complex_vector, is_power_of_two, magnitude_squared

ComplexVector = NDArray[np.complex128]
ComplexMatrix = NDArray[np.complex128]

HADAMARD: ComplexMatrix = np.array([[1, 1], [1, -1]], dtype=np.complex128) / np.sqrt(2)
PAULI_X: ComplexMatrix = np.array([[0, 1], [1, 0]], dtype=np.complex128)
PAULI_Y: ComplexMatrix = np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
PAULI_Z: ComplexMatrix = np.array([[1, 0], [0, -1]], dtype=np.complex128)


def basis_state(bit: int) -> ComplexVector:
    """Return the computational-basis state |0> or |1>."""
    if bit not in (0, 1):
        raise ValueError("A single-qubit basis-state label must be 0 or 1.")
    return np.array([1, 0], dtype=np.complex128) if bit == 0 else np.array([0, 1], dtype=np.complex128)


def norm_squared(state: ArrayLike) -> float:
    """Return ⟨ψ|ψ⟩, which must be one for a valid state vector."""
    vector = as_complex_vector(state)
    return float(np.sum(magnitude_squared(vector)))


def normalize(state: ArrayLike) -> ComplexVector:
    """Scale a nonzero vector so its total probability is exactly one."""
    vector = as_complex_vector(state)
    squared_norm = norm_squared(vector)
    if np.isclose(squared_norm, 0.0):
        raise ValueError("The zero vector cannot be normalized into a quantum state.")
    return vector / np.sqrt(squared_norm)


def validate_state(state: ArrayLike, *, atol: float = 1e-10) -> ComplexVector:
    """Validate a normalized state whose dimension is 2ⁿ for some integer n."""
    vector = as_complex_vector(state)
    if not is_power_of_two(vector.size):
        raise ValueError("State-vector dimension must be a power of two.")
    if not np.isclose(norm_squared(vector), 1.0, atol=atol):
        raise ValueError("State vector is not normalized; call normalize first.")
    return vector


def measurement_probabilities(state: ArrayLike) -> NDArray[np.float64]:
    """Apply the Born rule: P(i) = |amplitude_i|²."""
    vector = validate_state(state)
    probabilities = np.asarray(magnitude_squared(vector), dtype=np.float64)
    # A final normalization guards only against floating-point round-off.
    return probabilities / probabilities.sum()


def apply_single_qubit_gate(gate: ArrayLike, state: ArrayLike) -> ComplexVector:
    """Multiply a 2×2 unitary-like gate by a one-qubit state vector."""
    matrix = np.asarray(gate, dtype=np.complex128)
    vector = validate_state(state)
    if matrix.shape != (2, 2) or vector.shape != (2,):
        raise ValueError("This educational helper accepts one 2×2 gate and one qubit.")
    return matrix @ vector


def tensor_product(*states: ArrayLike) -> ComplexVector:
    """Combine one or more state vectors with the Kronecker product ⊗."""
    if not states:
        raise ValueError("Provide at least one state vector for a tensor product.")
    product = validate_state(states[0])
    for state in states[1:]:
        product = np.kron(product, validate_state(state))
    return np.asarray(product, dtype=np.complex128)


def qubit_count(state: ArrayLike) -> int:
    """Return n for a valid 2ⁿ-dimensional state vector."""
    vector = validate_state(state)
    return int(log2(vector.size))


def sample_measurements(
    state: ArrayLike,
    *,
    shots: int,
    seed: int | None = None,
) -> Counter[str]:
    """Sample computational-basis measurements with a deterministic RNG seed.

    The returned strings are conventional most-significant-bit-first binary
    labels, e.g. ``"00"`` and ``"11"`` for a two-qubit Bell state.
    """
    if shots <= 0:
        raise ValueError("shots must be a positive integer.")
    probabilities = measurement_probabilities(state)
    width = qubit_count(state)
    generator = np.random.default_rng(seed)
    outcomes = generator.choice(len(probabilities), size=shots, p=probabilities)
    return Counter(format(int(index), f"0{width}b") for index in outcomes)


def state_from_amplitudes(amplitudes: Iterable[complex]) -> ComplexVector:
    """Convenience constructor that makes normalization explicit in examples."""
    return normalize(np.fromiter(amplitudes, dtype=np.complex128))
