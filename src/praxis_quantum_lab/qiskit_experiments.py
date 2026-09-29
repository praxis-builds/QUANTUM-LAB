"""Local Qiskit/Aer equivalents of the hand-built state-vector lessons.

No function in this module imports an IBM provider or accesses a network.  The
only backends are Qiskit's exact ``Statevector`` and local ``AerSimulator``.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # Save images on a headless WSL installation.
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

DEFAULT_SEED = 20260928
DEFAULT_SHOTS = 2_048


def one_qubit_superposition_circuit() -> QuantumCircuit:
    """Prepare |+> = H|0>; no measurement is appended."""
    circuit = QuantumCircuit(1, name="one_qubit_superposition")
    circuit.h(0)
    return circuit


def one_qubit_measurement_circuit() -> QuantumCircuit:
    """Prepare |+> and measure it in the computational basis."""
    circuit = QuantumCircuit(1, 1, name="one_qubit_measurement")
    circuit.h(0)
    circuit.measure(0, 0)
    return circuit


def two_qubit_entanglement_circuit() -> QuantumCircuit:
    """Prepare an unmeasured Bell-pair state (|00> + |11>)/√2."""
    circuit = QuantumCircuit(2, name="two_qubit_entanglement")
    circuit.h(0)
    circuit.cx(0, 1)
    return circuit


def bell_state_measurement_circuit() -> QuantumCircuit:
    """Prepare a Bell state and measure both qubits."""
    circuit = QuantumCircuit(2, 2, name="bell_state_measurement")
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure([0, 1], [0, 1])
    return circuit


def _remove_measurements(circuit: QuantumCircuit) -> QuantumCircuit:
    """Return an instruction-only circuit accepted by Statevector.from_instruction."""
    return circuit.remove_final_measurements(inplace=False)


def exact_probabilities(circuit: QuantumCircuit) -> dict[str, float]:
    """Calculate exact probabilities directly from the local statevector simulator."""
    state = Statevector.from_instruction(_remove_measurements(circuit))
    return {key: float(value) for key, value in state.probabilities_dict().items()}


def ideal_counts(
    circuit: QuantumCircuit, *, shots: int = DEFAULT_SHOTS, seed: int = DEFAULT_SEED
) -> dict[str, int]:
    """Sample a measured circuit with Aer, using a deterministic simulator seed."""
    if not circuit.num_clbits:
        raise ValueError("ideal_counts requires a circuit with classical measurement bits.")
    simulator = AerSimulator(method="statevector")
    compiled = transpile(circuit, simulator, seed_transpiler=seed)
    result = simulator.run(compiled, shots=shots, seed_simulator=seed).result()
    return {key: int(value) for key, value in result.get_counts().items()}


def local_noise_model(
    *, single_qubit_error: float = 0.015, two_qubit_error: float = 0.04
) -> NoiseModel:
    """A deliberately small local depolarizing-noise model for a teaching run."""
    noise_model = NoiseModel()
    noise_model.add_all_qubit_quantum_error(
        depolarizing_error(single_qubit_error, 1), ["h"]
    )
    noise_model.add_all_qubit_quantum_error(
        depolarizing_error(two_qubit_error, 2), ["cx"]
    )
    return noise_model


def noisy_counts(
    circuit: QuantumCircuit,
    *,
    shots: int = DEFAULT_SHOTS,
    seed: int = DEFAULT_SEED,
    noise_model: NoiseModel | None = None,
) -> dict[str, int]:
    """Sample a circuit on a local Aer density-matrix simulator with noise."""
    if not circuit.num_clbits:
        raise ValueError("noisy_counts requires a circuit with classical measurement bits.")
    simulator = AerSimulator(
        method="density_matrix", noise_model=noise_model or local_noise_model()
    )
    compiled = transpile(circuit, simulator, seed_transpiler=seed)
    result = simulator.run(compiled, shots=shots, seed_simulator=seed).result()
    return {key: int(value) for key, value in result.get_counts().items()}


def save_histogram(counts: dict[str, int], title: str, path: Path) -> None:
    """Save a small, readable measured-outcome histogram."""
    outcomes = sorted(counts)
    figure, axis = plt.subplots(figsize=(5.2, 3.2))
    axis.bar(outcomes, [counts[outcome] for outcome in outcomes], color="#335c81")
    axis.set_title(title)
    axis.set_xlabel("measured bitstring")
    axis.set_ylabel("shots")
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def run_all_qiskit_examples(
    output_dir: str | Path = "results",
    *,
    shots: int = DEFAULT_SHOTS,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """Execute every Stage 2 experiment and persist a compact local report."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    superposition = one_qubit_superposition_circuit()
    measurement = one_qubit_measurement_circuit()
    entanglement = two_qubit_entanglement_circuit()
    bell_measurement = bell_state_measurement_circuit()

    measured_superposition = ideal_counts(measurement, shots=shots, seed=seed)
    ideal_bell = ideal_counts(bell_measurement, shots=shots, seed=seed)
    noisy_bell = noisy_counts(bell_measurement, shots=shots, seed=seed)

    report: dict[str, Any] = {
        "metadata": {
            "seed": seed,
            "shots": shots,
            "simulators": {
                "exact": "qiskit.quantum_info.Statevector (local, exact)",
                "ideal_samples": "qiskit_aer.AerSimulator(method='statevector')",
                "noisy_samples": "qiskit_aer.AerSimulator(method='density_matrix')",
            },
        },
        "one_qubit_superposition": {
            "circuit": "H on |0> (unmeasured)",
            "expected": {"0": 0.5, "1": 0.5},
            "observed_exact": exact_probabilities(superposition),
            "depth": superposition.depth(),
        },
        "one_qubit_measurement": {
            "circuit": "H on |0>, then a computational-basis measurement",
            "expected": "Approximately equal '0' and '1' counts over many shots.",
            "observed_counts": measured_superposition,
            "depth": measurement.depth(),
        },
        "two_qubit_entanglement": {
            "circuit": "H on qubit 0 followed by CX(0, 1)",
            "expected": {"00": 0.5, "11": 0.5},
            "observed_exact": exact_probabilities(entanglement),
            "depth": entanglement.depth(),
        },
        "bell_state_measurement": {
            "circuit": "H(0), CX(0, 1), measure both qubits",
            "expected": "Only '00' and '11' occur on an ideal simulator.",
            "observed_ideal_counts": ideal_bell,
            "observed_noisy_counts": noisy_bell,
            "depth": bell_measurement.depth(),
            "noise_explanation": (
                "Depolarizing errors applied after H and CX can disturb the Bell state, "
                "so noisy runs can produce '01' and '10' and shift the ideal balance."
            ),
        },
    }

    save_histogram(
        ideal_bell, "Ideal local Aer: Bell-state measurements", destination / "bell_ideal_histogram.png"
    )
    save_histogram(
        noisy_bell, "Noisy local Aer: Bell-state measurements", destination / "bell_noisy_histogram.png"
    )
    (destination / "qiskit_experiments.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    """CLI entry point used by ``praxis-qiskit-experiments``."""
    report = run_all_qiskit_examples()
    bell = report["bell_state_measurement"]
    print("Local Qiskit experiments completed.")
    print(f"Ideal Bell counts: {bell['observed_ideal_counts']}")
    print(f"Noisy Bell counts: {bell['observed_noisy_counts']}")
    print("Saved results/qiskit_experiments.json and Bell histogram PNGs.")


if __name__ == "__main__":
    main()
