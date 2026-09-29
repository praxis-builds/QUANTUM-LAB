import numpy as np
import pytest

from praxis_quantum_lab.density_matrices import (
    PAULI_X,
    amplitude_damping_channel,
    apply_local_kraus_channel,
    bit_flip_channel,
    depolarizing_channel,
    expand_single_qubit_operator,
    kraus_completeness,
    measurement_probabilities_from_density_matrix,
    pure_state_to_density_matrix,
    validate_density_matrix,
    validate_kraus_operators,
)
from praxis_quantum_lab.density_matrix_noise import (
    aer_density_matrix_after_local_channel,
    bell_state_density_matrix,
)


def test_pure_state_density_matrix_is_hermitian_trace_one_and_positive() -> None:
    density_matrix = pure_state_to_density_matrix(np.array([1, 1j]) / np.sqrt(2))
    validated = validate_density_matrix(density_matrix)
    assert np.allclose(validated, validated.conjugate().T)
    assert np.isclose(np.trace(validated), 1.0)
    assert np.all(np.linalg.eigvalsh(validated) >= -1e-12)


def test_invalid_density_matrices_and_kraus_inputs_are_rejected() -> None:
    with pytest.raises(ValueError, match="Hermitian"):
        validate_density_matrix(np.array([[1, 1], [0, 0]], dtype=np.complex128))
    with pytest.raises(ValueError, match="positive semidefinite"):
        validate_density_matrix(np.array([[1.1, 0], [0, -0.1]], dtype=np.complex128))
    with pytest.raises(ValueError, match="not complete"):
        validate_kraus_operators((np.sqrt(0.5) * np.eye(2),))
    with pytest.raises(ValueError, match="between 0 and 1"):
        bit_flip_channel(1.01)
    with pytest.raises(ValueError, match="between 0 and 1"):
        amplitude_damping_channel(-0.01)


def test_channels_are_complete_and_no_noise_preserves_bell_state() -> None:
    bell = bell_state_density_matrix()
    for channel in (bit_flip_channel(0.0), amplitude_damping_channel(0.0), depolarizing_channel(0.0)):
        assert np.allclose(kraus_completeness(channel), np.eye(2))
        assert np.allclose(apply_local_kraus_channel(bell, channel, qubit=0), bell)


def test_known_one_qubit_channel_limits_on_bell_state() -> None:
    bell = bell_state_density_matrix()
    flipped = apply_local_kraus_channel(bell, bit_flip_channel(1.0), qubit=0)
    damped = apply_local_kraus_channel(bell, amplitude_damping_channel(1.0), qubit=0)
    depolarized = apply_local_kraus_channel(bell, depolarizing_channel(1.0), qubit=0)

    assert np.allclose(
        measurement_probabilities_from_density_matrix(flipped), [0.0, 0.5, 0.5, 0.0]
    )
    assert np.allclose(
        measurement_probabilities_from_density_matrix(damped), [0.5, 0.0, 0.5, 0.0]
    )
    assert np.allclose(
        measurement_probabilities_from_density_matrix(depolarized), [0.25, 0.25, 0.25, 0.25]
    )


def test_qubit_zero_is_rightmost_bit_in_qiskit_little_endian_order() -> None:
    zero_zero = np.array([1, 0, 0, 0], dtype=np.complex128)
    x_on_q0 = expand_single_qubit_operator(PAULI_X, qubit=0, num_qubits=2)
    x_on_q1 = expand_single_qubit_operator(PAULI_X, qubit=1, num_qubits=2)
    assert np.allclose(x_on_q0 @ zero_zero, [0, 1, 0, 0])  # |00> -> |01>
    assert np.allclose(x_on_q1 @ zero_zero, [0, 0, 1, 0])  # |00> -> |10>


def test_custom_density_matrix_agrees_with_aer_for_same_kraus_channel() -> None:
    bell = bell_state_density_matrix()
    channel = depolarizing_channel(0.30)
    custom = apply_local_kraus_channel(bell, channel, qubit=0)
    aer = aer_density_matrix_after_local_channel(channel, qubit=0)
    # Both use IEEE double precision; 1e-10 is comfortably above round-off.
    assert np.allclose(custom, aer, atol=1e-10)
