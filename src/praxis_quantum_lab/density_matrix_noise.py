"""Bell-state Kraus noise sweeps compared with local Qiskit Aer.

Every case applies the channel only to qubit 0.  In the lab's/Qiskit's
little-endian convention that is the rightmost bit of a displayed two-bit
string.  Both the custom path and Aer use the *same* Kraus matrices, so the
comparison checks representation and ordering rather than noise-model tuning.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Kraus
from qiskit_aer import AerSimulator

from .bell_noise_analytics import PHI_PLUS, analytical_bell_case
from .density_matrices import (
    ComplexMatrix,
    amplitude_damping_channel,
    apply_local_kraus_channel,
    bit_flip_channel,
    depolarizing_channel,
    measurement_probabilities_from_density_matrix,
    pure_state_to_density_matrix,
)

DEFAULT_SEED = 20260928
DEFAULT_STRENGTHS = (0.0, 0.05, 0.15, 0.30, 0.60, 1.00)
RESULT_FILENAME = "density_matrix_bell_noise_sweep.json"
PLOT_FILENAME = "density_matrix_bell_noise_sweep.png"
ANALYTICAL_RESULT_FILENAME = "density_matrix_bell_noise_analytical_validation.json"
ANALYTICAL_PLOT_FILENAME = "density_matrix_bell_noise_analytical_fidelity.png"
ChannelFactory = Callable[[float], tuple[ComplexMatrix, ...]]

CHANNELS: dict[str, tuple[ChannelFactory, str]] = {
    "bit_flip": (
        bit_flip_channel,
        "p in [0, 1]: E(rho) = (1-p)rho + p X rho X.",
    ),
    "amplitude_damping": (
        amplitude_damping_channel,
        "gamma in [0, 1]: gamma is the |1> -> |0> decay probability.",
    ),
    "depolarizing": (
        depolarizing_channel,
        "p in [0, 1]: E(rho) = (1-p)rho + p I/2 on the targeted qubit.",
    ),
}


def bell_state_density_matrix() -> ComplexMatrix:
    """Return rho_Bell for (|00> + |11>)/sqrt(2) in Qiskit basis order."""
    bell_state = np.array([1.0, 0.0, 0.0, 1.0], dtype=np.complex128) / np.sqrt(2)
    return pure_state_to_density_matrix(bell_state)


def aer_density_matrix_after_local_channel(
    kraus_operators: tuple[ComplexMatrix, ...], *, qubit: int = 0
) -> ComplexMatrix:
    """Prepare Bell state, append the exact local Kraus instruction, save rho."""
    circuit = QuantumCircuit(2, name="bell_kraus_noise")
    circuit.h(0)
    circuit.cx(0, 1)
    # Qiskit 2.5 accepts a list as a Kraus set; the local API returns an
    # immutable tuple so callers cannot accidentally alter validated channels.
    circuit.append(Kraus(list(kraus_operators)).to_instruction(), [qubit])
    circuit.save_density_matrix()
    simulator = AerSimulator(method="density_matrix")
    result = simulator.run(circuit).result()
    return np.asarray(result.data(0)["density_matrix"], dtype=np.complex128)


def _complex_matrix_for_json(matrix: ComplexMatrix) -> list[list[list[float]]]:
    """Encode a complex matrix as [real, imag] pairs for portable JSON."""
    return [
        [[float(entry.real), float(entry.imag)] for entry in row]
        for row in np.asarray(matrix, dtype=np.complex128)
    ]


def _complex_matrix_from_json(encoded: list[list[list[float]]]) -> ComplexMatrix:
    """Recover a complex matrix stored as the report's [real, imag] pairs."""
    return np.asarray(
        [[real + 1j * imaginary for real, imaginary in row] for row in encoded],
        dtype=np.complex128,
    )


def initial_bell_fidelity(density_matrix: ComplexMatrix) -> float:
    """Evaluate F(Phi+, rho) for the pure initial Bell-state reference."""
    return float(np.real(np.vdot(PHI_PLUS, density_matrix @ PHI_PLUS)))


def _probability_record(probabilities: np.ndarray) -> dict[str, float]:
    return {
        format(index, "02b"): float(value)
        for index, value in enumerate(np.asarray(probabilities, dtype=np.float64))
    }


def run_bell_noise_sweep(
    *,
    strengths: tuple[float, ...] = DEFAULT_STRENGTHS,
    qubit: int = 0,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """Compare custom and Aer density matrices across all channels/strengths."""
    if not strengths:
        raise ValueError("Provide at least one noise strength.")
    initial_density_matrix = bell_state_density_matrix()
    report: dict[str, Any] = {
        "metadata": {
            "seed": seed,
            "initial_state": "(|00> + |11>)/sqrt(2)",
            "num_qubits": 2,
            "target_qubit": qubit,
            "basis_convention": (
                "Qiskit little-endian: basis index is |q1 q0>; target qubit 0 is "
                "the rightmost displayed bit, so X on q0 maps |00> to |01>."
            ),
            "custom_method": "rho_prime = sum_i K_i rho K_i^dagger",
            "aer_method": "AerSimulator(method='density_matrix') with the same Kraus instruction",
            "comparison_metric": "Frobenius norm ||rho_custom - rho_aer||_F",
            "comparison_tolerance": 1e-10,
        },
        "channels": {},
    }

    for channel_name, (factory, parameter_convention) in CHANNELS.items():
        cases: list[dict[str, Any]] = []
        for strength in strengths:
            kraus_operators = factory(strength)
            custom_density_matrix = apply_local_kraus_channel(
                initial_density_matrix, kraus_operators, qubit=qubit
            )
            aer_density_matrix = aer_density_matrix_after_local_channel(
                kraus_operators, qubit=qubit
            )
            custom_probabilities = measurement_probabilities_from_density_matrix(
                custom_density_matrix
            )
            aer_probabilities = measurement_probabilities_from_density_matrix(
                aer_density_matrix
            )
            cases.append(
                {
                    "strength": float(strength),
                    "kraus_completeness_max_error": float(
                        np.max(
                            np.abs(
                                sum(
                                    (
                                        operator.conjugate().T @ operator
                                        for operator in kraus_operators
                                    ),
                                    start=np.zeros((2, 2), dtype=np.complex128),
                                )
                                - np.eye(2)
                            )
                        )
                    ),
                    "custom_density_matrix": _complex_matrix_for_json(custom_density_matrix),
                    "aer_density_matrix": _complex_matrix_for_json(aer_density_matrix),
                    "frobenius_error": float(
                        np.linalg.norm(custom_density_matrix - aer_density_matrix, ord="fro")
                    ),
                    "custom_measurement_probabilities": _probability_record(custom_probabilities),
                    "aer_measurement_probabilities": _probability_record(aer_probabilities),
                }
            )
        report["channels"][channel_name] = {
            "parameter_convention": parameter_convention,
            "cases": cases,
        }
    return report


def save_noise_sweep_plot(report: dict[str, Any], path: Path) -> None:
    """Save probability-versus-strength plots in the project’s simple Matplotlib style."""
    figure, axes = plt.subplots(1, len(report["channels"]), figsize=(13.2, 3.5), sharey=True)
    for axis, (channel_name, channel_report) in zip(
        np.ravel(axes), report["channels"].items(), strict=True
    ):
        cases = channel_report["cases"]
        strengths = [case["strength"] for case in cases]
        for bitstring in ("00", "01", "10", "11"):
            axis.plot(
                strengths,
                [case["custom_measurement_probabilities"][bitstring] for case in cases],
                marker="o",
                label=bitstring,
            )
        axis.set_title(channel_name.replace("_", " ").title())
        axis.set_xlabel("channel strength")
        axis.set_ylim(-0.02, 1.02)
        axis.grid(alpha=0.25)
    axes[0].set_ylabel("measurement probability")
    axes[-1].legend(title="outcome", bbox_to_anchor=(1.02, 1), loc="upper left")
    figure.tight_layout()
    figure.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure)


def write_noise_sweep_artifacts(
    report: dict[str, Any], output_dir: str | Path = "results"
) -> tuple[Path, Path]:
    """Write new artifacts without replacing a previous sweep result."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / RESULT_FILENAME
    plot_path = destination / PLOT_FILENAME
    existing = [path.name for path in (json_path, plot_path) if path.exists()]
    if existing:
        raise FileExistsError(
            f"Refusing to overwrite existing result artifact(s): {', '.join(existing)}"
        )
    save_noise_sweep_plot(report, plot_path)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return json_path, plot_path


def run_analytical_bell_noise_validation(
    *,
    strengths: tuple[float, ...] = DEFAULT_STRENGTHS,
    qubit: int = 0,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """Compare independent analytical predictions with custom and Aer outputs.

    The analytical expressions are defined only for this sweep's qubit-0
    convention.  A different target would require a separately derived
    amplitude-damping reference because its population moves to |01> instead
    of |10>.
    """
    if qubit != 0:
        raise ValueError("The analytical Bell reference is derived for target qubit 0 only.")
    sweep = run_bell_noise_sweep(strengths=strengths, qubit=qubit, seed=seed)
    report: dict[str, Any] = {
        "metadata": {
            **sweep["metadata"],
            "analytical_reference": (
                "Closed forms derived from this project's Kraus operators for Bell state "
                "noise on Qiskit qubit 0; no custom-channel implementation is called."
            ),
            "fidelity_definition": "F(Phi+, rho) = <Phi+|rho|Phi+> because Phi+ is pure.",
        },
        "channels": {},
    }
    for channel_name, channel_report in sweep["channels"].items():
        cases: list[dict[str, Any]] = []
        for sweep_case in channel_report["cases"]:
            strength = sweep_case["strength"]
            analytical = analytical_bell_case(channel_name, strength)
            custom_density_matrix = _complex_matrix_from_json(
                sweep_case["custom_density_matrix"]
            )
            aer_density_matrix = _complex_matrix_from_json(sweep_case["aer_density_matrix"])
            cases.append(
                {
                    "strength": strength,
                    "analytical_measurement_probabilities": analytical[
                        "measurement_probabilities"
                    ],
                    "custom_measurement_probabilities": sweep_case[
                        "custom_measurement_probabilities"
                    ],
                    "aer_measurement_probabilities": sweep_case["aer_measurement_probabilities"],
                    "analytical_initial_bell_fidelity": analytical["initial_bell_fidelity"],
                    "custom_initial_bell_fidelity": initial_bell_fidelity(custom_density_matrix),
                    "aer_initial_bell_fidelity": initial_bell_fidelity(aer_density_matrix),
                    "analytical_to_custom_frobenius_error": float(
                        np.linalg.norm(
                            analytical["density_matrix"] - custom_density_matrix, ord="fro"
                        )
                    ),
                    "analytical_to_aer_frobenius_error": float(
                        np.linalg.norm(
                            analytical["density_matrix"] - aer_density_matrix, ord="fro"
                        )
                    ),
                    "analytical_to_custom_probability_max_error": float(
                        max(
                            abs(
                                analytical["measurement_probabilities"][bitstring]
                                - sweep_case["custom_measurement_probabilities"][bitstring]
                            )
                            for bitstring in ("00", "01", "10", "11")
                        )
                    ),
                    "analytical_density_matrix": _complex_matrix_for_json(
                        analytical["density_matrix"]
                    ),
                }
            )
        report["channels"][channel_name] = {
            "parameter_convention": channel_report["parameter_convention"],
            "cases": cases,
        }
    return report


def save_analytical_fidelity_plot(report: dict[str, Any], path: Path) -> None:
    """Plot the analytical Bell fidelity alongside custom and Aer calculations."""
    figure, axes = plt.subplots(1, len(report["channels"]), figsize=(13.2, 3.5), sharey=True)
    for axis, (channel_name, channel_report) in zip(
        np.ravel(axes), report["channels"].items(), strict=True
    ):
        cases = channel_report["cases"]
        strengths = [case["strength"] for case in cases]
        axis.plot(
            strengths,
            [case["analytical_initial_bell_fidelity"] for case in cases],
            marker="o",
            label="analytical",
        )
        axis.plot(
            strengths,
            [case["custom_initial_bell_fidelity"] for case in cases],
            marker="x",
            linestyle="--",
            label="custom density",
        )
        axis.plot(
            strengths,
            [case["aer_initial_bell_fidelity"] for case in cases],
            marker="+",
            linestyle=":",
            label="local Aer",
        )
        axis.set_title(channel_name.replace("_", " ").title())
        axis.set_xlabel("channel strength")
        axis.set_ylim(-0.02, 1.02)
        axis.grid(alpha=0.25)
    axes[0].set_ylabel("Bell-state fidelity")
    axes[-1].legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    figure.tight_layout()
    figure.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(figure)


def write_analytical_validation_artifacts(
    report: dict[str, Any], output_dir: str | Path = "results"
) -> tuple[Path, Path]:
    """Save new analytical-validation artifacts without replacing prior results."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / ANALYTICAL_RESULT_FILENAME
    plot_path = destination / ANALYTICAL_PLOT_FILENAME
    existing = [path.name for path in (json_path, plot_path) if path.exists()]
    if existing:
        raise FileExistsError(
            f"Refusing to overwrite existing result artifact(s): {', '.join(existing)}"
        )
    save_analytical_fidelity_plot(report, plot_path)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return json_path, plot_path


def main() -> None:
    """Run the reproducible sweep and save new result artifacts."""
    report = run_bell_noise_sweep()
    json_path, plot_path = write_noise_sweep_artifacts(report)
    errors = [
        case["frobenius_error"]
        for channel in report["channels"].values()
        for case in channel["cases"]
    ]
    print("Bell-state density-matrix noise sweep completed locally.")
    print(f"Maximum custom-versus-Aer Frobenius error: {max(errors):.3e}")
    print(f"Saved {json_path} and {plot_path}.")


if __name__ == "__main__":
    main()
