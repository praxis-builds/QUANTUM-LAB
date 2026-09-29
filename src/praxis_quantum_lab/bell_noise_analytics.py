"""Analytical Bell-state references for this lab's exact channel conventions.

The reference intentionally does not call ``apply_local_kraus_channel``.  It
builds the channel outputs from the channel definitions documented in
``density_matrices.py`` for a Bell state with noise on Qiskit qubit 0.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .density_matrices import ComplexMatrix, validate_channel_parameter


def _ket(entries: list[complex]) -> np.ndarray:
    return np.asarray(entries, dtype=np.complex128) / np.sqrt(2)


PHI_PLUS = _ket([1, 0, 0, 1])
PHI_MINUS = _ket([1, 0, 0, -1])
PSI_PLUS = _ket([0, 1, 1, 0])
PSI_MINUS = _ket([0, 1, -1, 0])
KET_00 = np.array([1, 0, 0, 0], dtype=np.complex128)
KET_10 = np.array([0, 0, 1, 0], dtype=np.complex128)


def _projector(vector: np.ndarray) -> ComplexMatrix:
    return np.outer(vector, vector.conjugate())


RHO_PHI_PLUS = _projector(PHI_PLUS)
RHO_PHI_MINUS = _projector(PHI_MINUS)
RHO_PSI_PLUS = _projector(PSI_PLUS)
RHO_PSI_MINUS = _projector(PSI_MINUS)


def analytical_bell_density_matrix(channel_name: str, strength: float) -> ComplexMatrix:
    """Return the closed-form Bell output for this project's channel operators.

    ``channel_name`` is one of ``bit_flip``, ``amplitude_damping``, or
    ``depolarizing``.  All formulas assume the project's target qubit 0,
    which is the rightmost bit in ``|q1 q0>``.
    """
    if channel_name == "bit_flip":
        probability = validate_channel_parameter(strength)
        # (1-p)|Phi+><Phi+| + p|Psi+><Psi+|
        return (1.0 - probability) * RHO_PHI_PLUS + probability * RHO_PSI_PLUS
    if channel_name == "amplitude_damping":
        gamma = validate_channel_parameter(strength, name="gamma")
        # K0|Phi+> = (|00> + sqrt(1-gamma)|11>)/sqrt(2),
        # K1|Phi+> = sqrt(gamma)|10>/sqrt(2).
        no_jump = np.array([1.0, 0.0, 0.0, np.sqrt(1.0 - gamma)], dtype=np.complex128)
        no_jump /= np.sqrt(2)
        return _projector(no_jump) + (gamma / 2.0) * _projector(KET_10)
    if channel_name == "depolarizing":
        probability = validate_channel_parameter(strength)
        # The actual Kraus weights are I: 1-3p/4 and X,Y,Z: p/4 each.
        return (
            (1.0 - 0.75 * probability) * RHO_PHI_PLUS
            + 0.25 * probability * RHO_PHI_MINUS
            + 0.25 * probability * RHO_PSI_PLUS
            + 0.25 * probability * RHO_PSI_MINUS
        )
    raise ValueError(f"Unsupported analytical Bell channel: {channel_name}")


def analytical_bell_probabilities(channel_name: str, strength: float) -> dict[str, float]:
    """Return closed-form computational-basis probabilities in |q1 q0> order."""
    parameter = validate_channel_parameter(
        strength, name="gamma" if channel_name == "amplitude_damping" else "probability"
    )
    if channel_name == "bit_flip":
        return {
            "00": (1.0 - parameter) / 2.0,
            "01": parameter / 2.0,
            "10": parameter / 2.0,
            "11": (1.0 - parameter) / 2.0,
        }
    if channel_name == "amplitude_damping":
        return {
            "00": 0.5,
            "01": 0.0,
            "10": parameter / 2.0,
            "11": (1.0 - parameter) / 2.0,
        }
    if channel_name == "depolarizing":
        return {
            "00": 0.5 - parameter / 4.0,
            "01": parameter / 4.0,
            "10": parameter / 4.0,
            "11": 0.5 - parameter / 4.0,
        }
    raise ValueError(f"Unsupported analytical Bell channel: {channel_name}")


def analytical_bell_fidelity(channel_name: str, strength: float) -> float:
    """Return F(Phi+, rho) = <Phi+|rho|Phi+> for the pure Bell reference."""
    parameter = validate_channel_parameter(
        strength, name="gamma" if channel_name == "amplitude_damping" else "probability"
    )
    if channel_name == "bit_flip":
        return 1.0 - parameter
    if channel_name == "amplitude_damping":
        return float(((1.0 + np.sqrt(1.0 - parameter)) ** 2) / 4.0)
    if channel_name == "depolarizing":
        return 1.0 - 0.75 * parameter
    raise ValueError(f"Unsupported analytical Bell channel: {channel_name}")


def analytical_bell_case(channel_name: str, strength: float) -> dict[str, Any]:
    """Bundle independent density, probabilities, and Bell fidelity for a case."""
    density_matrix = analytical_bell_density_matrix(channel_name, strength)
    return {
        "density_matrix": density_matrix,
        "measurement_probabilities": analytical_bell_probabilities(channel_name, strength),
        "initial_bell_fidelity": analytical_bell_fidelity(channel_name, strength),
    }
