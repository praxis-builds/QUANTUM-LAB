from collections import Counter

import numpy as np
import pytest

from praxis_quantum_lab.state_vectors import (
    HADAMARD,
    PAULI_X,
    PAULI_Y,
    PAULI_Z,
    apply_single_qubit_gate,
    basis_state,
    measurement_probabilities,
    norm_squared,
    normalize,
    sample_measurements,
    tensor_product,
)


def test_normalization_makes_total_probability_one() -> None:
    state = normalize([3 + 4j, 0])
    assert np.isclose(norm_squared(state), 1.0)


def test_measurement_probabilities_sum_to_one() -> None:
    state = normalize([1 + 1j, 2 - 1j])
    probabilities = measurement_probabilities(state)
    assert np.isclose(probabilities.sum(), 1.0)
    assert np.all(probabilities >= 0)


def test_standard_single_qubit_gate_behavior() -> None:
    zero = basis_state(0)
    plus = apply_single_qubit_gate(HADAMARD, zero)

    assert np.allclose(apply_single_qubit_gate(PAULI_X, zero), basis_state(1))
    assert np.allclose(apply_single_qubit_gate(PAULI_Y, zero), np.array([0, 1j]))
    assert np.allclose(apply_single_qubit_gate(PAULI_Z, plus), np.array([1, -1]) / np.sqrt(2))


def test_tensor_product_has_expected_multi_qubit_dimension() -> None:
    two_qubit_state = tensor_product(basis_state(0), basis_state(1))
    assert two_qubit_state.shape == (4,)
    assert np.allclose(two_qubit_state, np.array([0, 1, 0, 0], dtype=np.complex128))


def test_seeded_measurements_are_deterministic() -> None:
    plus = apply_single_qubit_gate(HADAMARD, basis_state(0))
    first = sample_measurements(plus, shots=200, seed=7)
    second = sample_measurements(plus, shots=200, seed=7)
    assert first == second
    assert first == Counter({"0": first["0"], "1": first["1"]})


def test_zero_vector_cannot_be_normalized() -> None:
    with pytest.raises(ValueError, match="zero vector"):
        normalize([0, 0])
