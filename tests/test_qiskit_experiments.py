import numpy as np

from praxis_quantum_lab.qiskit_experiments import (
    exact_probabilities,
    one_qubit_superposition_circuit,
    two_qubit_entanglement_circuit,
)


def test_qiskit_superposition_has_exact_equal_probabilities() -> None:
    probabilities = exact_probabilities(one_qubit_superposition_circuit())
    assert np.isclose(probabilities["0"], 0.5)
    assert np.isclose(probabilities["1"], 0.5)


def test_qiskit_bell_state_has_only_correlated_outcomes() -> None:
    probabilities = exact_probabilities(two_qubit_entanglement_circuit())
    assert np.isclose(probabilities["00"], 0.5)
    assert np.isclose(probabilities["11"], 0.5)
    assert set(probabilities) == {"00", "11"}
