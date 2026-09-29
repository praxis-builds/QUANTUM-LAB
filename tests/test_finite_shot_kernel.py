import numpy as np
import pytest

from praxis_quantum_lab.finite_shot_kernel import (
    DEFAULT_SEED,
    FINITE_SHOT_RESULT_FILENAME,
    compute_uncompute_circuit,
    estimate_compute_uncompute_probability,
    exact_compute_uncompute_probability,
    run_finite_shot_kernel_experiment,
    training_kernel_diagnostics,
    write_finite_shot_result,
)
from praxis_quantum_lab.kernel_experiment import (
    feature_statevectors,
    fidelity_quantum_kernel,
    make_dataset,
)


def test_compute_uncompute_exact_probabilities_match_existing_kernel() -> None:
    features, _ = make_dataset(dataset_size=24, seed=42)
    features = features[[0, 3, 8, 14]]
    states = feature_statevectors(features)
    exact_kernel = fidelity_quantum_kernel(states, states)
    for i, j in ((0, 0), (0, 1), (1, 3), (3, 2)):
        assert np.isclose(
            exact_compute_uncompute_probability(features[i], features[j]),
            exact_kernel[i, j],
            atol=1e-12,
        )
    circuit = compute_uncompute_circuit(features[0], features[1])
    assert circuit.num_qubits == 2
    assert circuit.num_clbits == 2
    assert circuit.count_ops()["measure"] == 2


def test_aer_probability_is_valid_and_fixed_seed_reproduces() -> None:
    features, _ = make_dataset(dataset_size=24, seed=11)
    x, z = features[0], features[1]
    estimate_a = estimate_compute_uncompute_probability(x, z, shots=128, seed=991)
    estimate_b = estimate_compute_uncompute_probability(x, z, shots=128, seed=991)
    assert 0.0 <= estimate_a <= 1.0
    assert np.isclose(estimate_a * 128, round(estimate_a * 128))
    assert estimate_a == estimate_b


def test_training_kernel_diagnostics_check_symmetry_and_raw_eigenvalue() -> None:
    symmetric = np.array([[1.0, 0.8], [0.8, 1.0]])
    assert training_kernel_diagnostics(symmetric)["positive_semidefinite_within_tolerance"]
    indefinite = np.array([[1.0, 1.2], [1.2, 1.0]])
    report = training_kernel_diagnostics(indefinite)
    assert report["symmetry_max_abs_error"] == 0.0
    assert report["minimum_eigenvalue"] < 0.0
    assert not report["positive_semidefinite_within_tolerance"]
    assert report["diagonal_values"] == [1.0, 1.0]


def test_small_fixed_split_experiment_reflects_training_triangle_and_exact_diagonal() -> None:
    report = run_finite_shot_kernel_experiment(
        sample_size=20,
        seed=DEFAULT_SEED,
        shot_budgets=(64,),
        shot_seeds=(101,),
    )
    assert report["metadata"]["train_size"] == 14
    assert report["metadata"]["test_size"] == 6
    shot = report["shot_budgets"][0]
    replicate = shot["replicates"][0]
    diag = replicate["training_kernel_diagnostics"]
    assert diag["symmetry_max_abs_error"] == 0.0
    assert diag["diagonal_values"] == [1.0] * 14
    assert np.isfinite(diag["minimum_eigenvalue"])
    assert diag["positive_semidefinite_within_tolerance"] == (
        diag["minimum_eigenvalue"] >= -diag["psd_tolerance"]
    )
    assert replicate["kernel_errors"]["training_unique_off_diagonal"]["entries_compared"] == 91
    assert replicate["kernel_errors"]["test_to_training"]["entries_compared"] == 84
    assert shot["summary"]["replicate_count"] == 1


def test_finite_shot_result_writer_refuses_to_overwrite(tmp_path) -> None:
    existing = tmp_path / FINITE_SHOT_RESULT_FILENAME
    existing.write_text("keep this", encoding="utf-8")
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        write_finite_shot_result({"test": True}, tmp_path)
    assert existing.read_text(encoding="utf-8") == "keep this"
