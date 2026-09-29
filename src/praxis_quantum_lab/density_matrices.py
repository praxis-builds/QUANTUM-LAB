"""Small density-matrix and Kraus-channel tools for the two-qubit lab.

Basis convention
----------------
Matrices use the same computational-basis indexing as Qiskit Statevector:
for ``n`` qubits, index ``i`` is written ``|q[n-1] ... q[0]>``.  Qubit 0 is
therefore the least-significant (rightmost) bit.  On two qubits,
``expand_single_qubit_operator(X, qubit=0)`` is ``I ⊗ X`` and maps |00> to
|01>; targeting qubit 1 is ``X ⊗ I`` and maps |00> to |10>.

The module deliberately targets the small systems used in this lab.  It makes
the channel equation visible instead of abstracting it behind a simulator:
``rho_prime = sum_i K_i rho K_i^dagger``.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .complex_math import is_power_of_two
from .state_vectors import PAULI_X, PAULI_Y, PAULI_Z, validate_state

ComplexMatrix = NDArray[np.complex128]
DEFAULT_ATOL = 1e-10


def pure_state_to_density_matrix(state: ArrayLike) -> ComplexMatrix:
    """Convert a normalized ket |psi> into rho = |psi><psi|."""
    vector = validate_state(state)
    return np.outer(vector, vector.conjugate())


def validate_density_matrix(
    density_matrix: ArrayLike, *, atol: float = DEFAULT_ATOL
) -> ComplexMatrix:
    """Validate a physical finite-dimensional density matrix.

    A valid density matrix is square with a power-of-two dimension, Hermitian,
    trace one, and positive semidefinite up to numerical tolerance.
    """
    matrix = np.asarray(density_matrix, dtype=np.complex128)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("A density matrix must be square.")
    if not is_power_of_two(matrix.shape[0]):
        raise ValueError("Density-matrix dimension must be a power of two.")
    if not np.allclose(matrix, matrix.conjugate().T, atol=atol):
        raise ValueError("A density matrix must be Hermitian.")
    if not np.isclose(np.trace(matrix), 1.0, atol=atol):
        raise ValueError("A density matrix must have trace one.")
    eigenvalues = np.linalg.eigvalsh(matrix)
    if np.min(eigenvalues) < -atol:
        raise ValueError("A density matrix must be positive semidefinite.")
    return matrix


def validate_channel_parameter(value: float, *, name: str = "probability") -> float:
    """Validate the [0, 1] strength convention used by the supplied channels."""
    parameter = float(value)
    if not np.isfinite(parameter) or not 0.0 <= parameter <= 1.0:
        raise ValueError(f"{name} must be finite and between 0 and 1 inclusive.")
    return parameter


def kraus_completeness(kraus_operators: Iterable[ArrayLike]) -> ComplexMatrix:
    """Return sum_i K_i^dagger K_i, which must equal identity for a channel."""
    operators = tuple(np.asarray(operator, dtype=np.complex128) for operator in kraus_operators)
    if not operators:
        raise ValueError("A Kraus channel needs at least one operator.")
    first_shape = operators[0].shape
    if len(first_shape) != 2 or first_shape[0] != first_shape[1]:
        raise ValueError("Each Kraus operator must be square.")
    if any(operator.shape != first_shape for operator in operators):
        raise ValueError("All Kraus operators must have the same square shape.")
    return sum((operator.conjugate().T @ operator for operator in operators), start=np.zeros(first_shape, dtype=np.complex128))


def validate_kraus_operators(
    kraus_operators: Iterable[ArrayLike], *, atol: float = DEFAULT_ATOL
) -> tuple[ComplexMatrix, ...]:
    """Validate a trace-preserving Kraus representation and return copied arrays."""
    operators = tuple(np.asarray(operator, dtype=np.complex128) for operator in kraus_operators)
    completeness = kraus_completeness(operators)
    identity = np.eye(completeness.shape[0], dtype=np.complex128)
    if not np.allclose(completeness, identity, atol=atol):
        raise ValueError("Kraus operators are not complete: sum K†K must equal identity.")
    return operators


def bit_flip_channel(probability: float) -> tuple[ComplexMatrix, ...]:
    """Return E(rho)=(1-p)rho+p XrhoX for p in [0, 1]."""
    probability = validate_channel_parameter(probability)
    identity = np.eye(2, dtype=np.complex128)
    return validate_kraus_operators(
        (np.sqrt(1.0 - probability) * identity, np.sqrt(probability) * PAULI_X)
    )


def amplitude_damping_channel(gamma: float) -> tuple[ComplexMatrix, ...]:
    """Return amplitude damping with |1> -> |0> probability gamma in [0, 1]."""
    gamma = validate_channel_parameter(gamma, name="gamma")
    keep = np.array([[1.0, 0.0], [0.0, np.sqrt(1.0 - gamma)]], dtype=np.complex128)
    decay = np.array([[0.0, np.sqrt(gamma)], [0.0, 0.0]], dtype=np.complex128)
    return validate_kraus_operators((keep, decay))


def depolarizing_channel(probability: float) -> tuple[ComplexMatrix, ...]:
    """Return E(rho)=(1-p)rho+p I/2 for a one-qubit p in [0, 1].

    This ``p`` is the probability of replacing the qubit by the maximally
    mixed state, not Aer's separately named depolarizing-error parameter.  The
    experiment inserts these exact Kraus operators into Aer, so both paths use
    the same convention.
    """
    probability = validate_channel_parameter(probability)
    identity = np.eye(2, dtype=np.complex128)
    return validate_kraus_operators(
        (
            np.sqrt(1.0 - 0.75 * probability) * identity,
            np.sqrt(0.25 * probability) * PAULI_X,
            np.sqrt(0.25 * probability) * PAULI_Y,
            np.sqrt(0.25 * probability) * PAULI_Z,
        )
    )


def apply_kraus_channel(
    density_matrix: ArrayLike, kraus_operators: Iterable[ArrayLike]
) -> ComplexMatrix:
    """Apply rho_prime = sum_i K_i rho K_i^dagger to a full-system matrix."""
    matrix = validate_density_matrix(density_matrix)
    operators = validate_kraus_operators(kraus_operators)
    if operators[0].shape != matrix.shape:
        raise ValueError("Full-system Kraus operators must match the density-matrix shape.")
    evolved = sum(
        (operator @ matrix @ operator.conjugate().T for operator in operators),
        start=np.zeros_like(matrix),
    )
    return validate_density_matrix(evolved)


def expand_single_qubit_operator(
    operator: ArrayLike, *, qubit: int, num_qubits: int
) -> ComplexMatrix:
    """Embed a 2x2 operator using Qiskit's little-endian qubit numbering.

    The implementation assigns matrix entries by bit position instead of using
    an ambiguous tensor-product order.  It is intentionally small-system code,
    suitable for the one- and two-qubit lessons in this repository.
    """
    local = np.asarray(operator, dtype=np.complex128)
    if local.shape != (2, 2):
        raise ValueError("A local single-qubit operator must have shape (2, 2).")
    if not isinstance(num_qubits, int) or num_qubits < 1:
        raise ValueError("num_qubits must be a positive integer.")
    if not isinstance(qubit, int) or not 0 <= qubit < num_qubits:
        raise ValueError("qubit must be an integer in the range [0, num_qubits).")

    dimension = 2**num_qubits
    expanded = np.zeros((dimension, dimension), dtype=np.complex128)
    mask = 1 << qubit
    for column in range(dimension):
        input_bit = (column >> qubit) & 1
        column_without_target = column & ~mask
        for output_bit in (0, 1):
            row = column_without_target | (output_bit << qubit)
            expanded[row, column] = local[output_bit, input_bit]
    return expanded


def apply_local_kraus_channel(
    density_matrix: ArrayLike,
    kraus_operators: Iterable[ArrayLike],
    *,
    qubit: int,
) -> ComplexMatrix:
    """Apply a complete one-qubit channel to one qubit of a small system."""
    matrix = validate_density_matrix(density_matrix)
    num_qubits = int(np.log2(matrix.shape[0]))
    local_operators = validate_kraus_operators(kraus_operators)
    if local_operators[0].shape != (2, 2):
        raise ValueError("apply_local_kraus_channel requires 2x2 local Kraus operators.")
    full_operators = tuple(
        expand_single_qubit_operator(operator, qubit=qubit, num_qubits=num_qubits)
        for operator in local_operators
    )
    return apply_kraus_channel(matrix, full_operators)


def measurement_probabilities_from_density_matrix(
    density_matrix: ArrayLike,
) -> NDArray[np.float64]:
    """Return computational-basis probabilities from the diagonal of rho."""
    matrix = validate_density_matrix(density_matrix)
    probabilities = np.real(np.diag(matrix)).astype(np.float64)
    return probabilities / probabilities.sum()
