import numpy as np

from praxis_quantum_lab.kernel_experiment import (
    fidelity_quantum_kernel,
    quantum_feature_map,
)


def test_feature_map_is_a_shallow_two_qubit_circuit() -> None:
    circuit = quantum_feature_map(np.array([0.2, -0.1]))
    assert circuit.num_qubits == 2
    assert circuit.depth() > 0


def test_fidelity_kernel_has_unit_diagonal_and_is_symmetric() -> None:
    states = np.array([[1, 0], [0, 1]], dtype=np.complex128)
    kernel = fidelity_quantum_kernel(states, states)
    assert np.allclose(np.diag(kernel), 1.0)
    assert np.allclose(kernel, kernel.T)
