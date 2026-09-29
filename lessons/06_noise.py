"""Lesson 06: noise. Add the repo's depolarizing channel to lesson 05's Grover circuit."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from qiskit import QuantumCircuit

from qiskit.quantum_info import Kraus, Operator
from qiskit_aer import AerSimulator

from _common import heading, out_dir
from _grover import Layer, circuit_from_layers, grover_layers, stage_boundaries
from praxis_quantum_lab.density_matrices import (
    apply_local_kraus_channel,
    depolarizing_channel,
    measurement_probabilities_from_density_matrix,
    pure_state_to_density_matrix,
)

MARKED = "10"
STRENGTHS = (0.0, 0.01, 0.02, 0.05, 0.10, 0.20, 0.30, 0.50, 0.75, 1.00)
CHECK_STRENGTH = 0.10


def layer_unitary(layer: Layer) -> np.ndarray:
    """4x4 matrix of one gate layer (Qiskit basis order |q1 q0>)."""
    return Operator(circuit_from_layers([layer])).data


def noisy_density_matrix(p: float, layer_count: int | None = None) -> np.ndarray:
    """Run the Grover layers; after EVERY layer each qubit suffers depolarizing noise of strength p.

    Depolarizing noise (the repo's depolarizing_channel): with probability p the qubit is
    replaced by a completely random one, otherwise it is left alone.
    """
    layers = grover_layers(MARKED)[:layer_count]
    rho = pure_state_to_density_matrix(np.array([1, 0, 0, 0], dtype=np.complex128))
    channel = depolarizing_channel(p)
    for layer in layers:
        unitary = layer_unitary(layer)
        rho = unitary @ rho @ unitary.conj().T
        for qubit in (0, 1):
            rho = apply_local_kraus_channel(rho, channel, qubit=qubit)
    return rho


def success_probability(p: float) -> float:
    rho = noisy_density_matrix(p)
    return float(measurement_probabilities_from_density_matrix(rho)[int(MARKED, 2)])


def coherence(rho: np.ndarray) -> float:
    """Sum of the sizes of the off-diagonal entries: how much interference is still possible."""
    return float(np.abs(rho - np.diag(np.diag(rho))).sum())


def aer_success_probability(p: float) -> float:
    """The same noisy circuit on local Aer, using the identical Kraus operators."""
    circuit = QuantumCircuit(2)
    kraus = Kraus(list(depolarizing_channel(p)))
    for layer in grover_layers(MARKED):
        for gate, qubits in layer[1]:
            getattr(circuit, gate)(*qubits)
        for qubit in (0, 1):
            circuit.append(kraus.to_instruction(), [qubit])
    circuit.save_density_matrix()
    result = AerSimulator(method="density_matrix").run(circuit).result()
    rho = np.asarray(result.data(0)["density_matrix"], dtype=np.complex128)
    return float(np.real(rho[int(MARKED, 2), int(MARKED, 2)]))


def main() -> dict:
    layer_count = len(grover_layers(MARKED))
    oracle_layers = stage_boundaries(MARKED)["oracle"]
    heading(f"Step 1: success probability vs noise strength (marked |{MARKED}>, {layer_count} layers, noise after each layer on each qubit)")
    success = {}
    ideal_coherence = coherence(noisy_density_matrix(0.0, oracle_layers))
    coherence_ratio = {}
    for p in STRENGTHS:
        success[p] = success_probability(p)
        coherence_ratio[p] = coherence(noisy_density_matrix(p, oracle_layers)) / ideal_coherence
        print(f"noise p = {p:4.2f} per layer per qubit: P(find marked) = {success[p]:.4f}   interference left before diffusion: {coherence_ratio[p]:.3f}")
    print("A single random classical guess succeeds with probability 0.25. Fully random noise (p = 1) lands exactly there.")

    heading("Step 2: does the repo's exact-Kraus route agree with Aer?")
    numpy_value = success_probability(CHECK_STRENGTH)
    aer_value = aer_success_probability(CHECK_STRENGTH)
    print(f"p = {CHECK_STRENGTH}: density-matrix code = {numpy_value:.9f}, local Aer density-matrix run = {aer_value:.9f}")
    print(f"difference = {abs(numpy_value - aer_value):.2e}")

    figure, (left, right) = plt.subplots(1, 2, figsize=(10, 4))
    left.plot(list(success), list(success.values()), "o-", label="Grover with noise")
    left.axhline(0.25, color="k", ls="--", label="one random guess (0.25)")
    left.set_xlabel("noise strength p (per layer, per qubit)")
    left.set_ylabel("probability of finding the marked item")
    left.legend()
    right.plot(list(coherence_ratio), list(coherence_ratio.values()), "o-", color="tab:red")
    right.set_xlabel("noise strength p (per layer, per qubit)")
    right.set_ylabel("interference left before the diffusion step")
    figure.tight_layout()
    path = out_dir() / "06_noise_success.png"
    figure.savefig(path, dpi=130)
    plt.close(figure)
    print(f"\nsaved plot: {Path(path)}")
    return {
        "success": success,
        "coherence_ratio": coherence_ratio,
        "numpy_value": numpy_value,
        "aer_value": aer_value,
        "layers": layer_count,
    }


if __name__ == "__main__":
    main()
