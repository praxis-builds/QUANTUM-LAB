import numpy as np
import pytest

from praxis_quantum_lab.bell_noise_analytics import (
    analytical_bell_density_matrix,
    analytical_bell_fidelity,
    analytical_bell_probabilities,
)
from praxis_quantum_lab.density_matrices import validate_density_matrix
from praxis_quantum_lab.density_matrix_noise import (
    ANALYTICAL_RESULT_FILENAME,
    DEFAULT_STRENGTHS,
    run_analytical_bell_noise_validation,
    write_analytical_validation_artifacts,
)


def test_analytical_probabilities_and_fidelities_follow_project_channel_conventions() -> None:
    assert analytical_bell_probabilities("bit_flip", 0.30) == {
        "00": 0.35,
        "01": 0.15,
        "10": 0.15,
        "11": 0.35,
    }
    assert analytical_bell_probabilities("amplitude_damping", 1.0) == {
        "00": 0.5,
        "01": 0.0,
        "10": 0.5,
        "11": 0.0,
    }
    assert analytical_bell_probabilities("depolarizing", 1.0) == {
        "00": 0.25,
        "01": 0.25,
        "10": 0.25,
        "11": 0.25,
    }
    assert np.isclose(analytical_bell_fidelity("bit_flip", 1.0), 0.0)
    assert np.isclose(analytical_bell_fidelity("amplitude_damping", 1.0), 0.25)
    assert np.isclose(analytical_bell_fidelity("depolarizing", 1.0), 0.25)


def test_analytical_density_matrices_are_valid_at_channel_limits() -> None:
    for channel_name in ("bit_flip", "amplitude_damping", "depolarizing"):
        for strength in (0.0, 1.0):
            validated = validate_density_matrix(
                analytical_bell_density_matrix(channel_name, strength)
            )
            assert np.isclose(np.trace(validated), 1.0)


def test_analytical_reference_matches_custom_and_aer_across_existing_sweep() -> None:
    report = run_analytical_bell_noise_validation(strengths=DEFAULT_STRENGTHS)
    for channel in report["channels"].values():
        for case in channel["cases"]:
            assert case["analytical_to_custom_frobenius_error"] <= 1e-10
            assert case["analytical_to_aer_frobenius_error"] <= 1e-10
            assert case["analytical_to_custom_probability_max_error"] <= 1e-10
            assert np.isclose(
                case["analytical_initial_bell_fidelity"],
                case["custom_initial_bell_fidelity"],
                atol=1e-10,
            )
            assert np.isclose(
                case["analytical_initial_bell_fidelity"],
                case["aer_initial_bell_fidelity"],
                atol=1e-10,
            )


def test_analytical_writer_refuses_to_replace_existing_file(tmp_path) -> None:
    (tmp_path / ANALYTICAL_RESULT_FILENAME).write_text("existing result", encoding="utf-8")
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        write_analytical_validation_artifacts({"channels": {}}, tmp_path)
