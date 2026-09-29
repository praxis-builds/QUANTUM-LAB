import numpy as np
import pytest

from praxis_quantum_lab.kernel_experiment import (
    REPEATED_RESULT_FILENAME,
    run_repeated_classification_experiment,
    training_kernel_diagnostics,
    training_kernel_similarity,
    write_repeated_experiment_artifact,
)


def test_repeated_experiment_records_paired_splits_and_separate_timings() -> None:
    report = run_repeated_classification_experiment(
        dataset_size=24, seed=11, n_splits=2, n_repeats=1, timing_repetitions=1
    )
    assert report["metadata"]["total_evaluated_splits"] == 2
    assert len(report["per_split"]) == 2
    for split in report["per_split"]:
        assert split["classical_rbf_svc"]["accuracy"] >= 0.0
        assert split["quantum_kernel_svc"]["accuracy"] >= 0.0
        assert "train_kernel_construction" in split["classical_rbf_svc"][
            "local_simulator_timing_seconds"
        ]
        assert "svc_fit" in split["quantum_kernel_svc"]["local_simulator_timing_seconds"]
        diagnostics = split["training_kernel_diagnostics"]
        assert diagnostics["scope"].startswith("training data only")
        assert diagnostics["quantum"]["positive_semidefinite_within_tolerance"]
        assert len(diagnostics["classical_rbf"]["diagonal_values"]) == split["train_size"]
    assert "values" in report["aggregate"]["paired_accuracy_difference_quantum_minus_classical"]


def test_kernel_diagnostics_and_similarity_are_label_free_matrix_properties() -> None:
    identity = training_kernel_diagnostics(np.eye(3))
    similar = training_kernel_similarity(np.eye(3), np.eye(3))
    assert identity["symmetry_max_abs_error"] == 0.0
    assert identity["diagonal_values"] == [1.0, 1.0, 1.0]
    assert identity["minimum_eigenvalue"] == 1.0
    assert identity["positive_semidefinite_within_tolerance"]
    assert similar["frobenius_cosine_similarity"] == 1.0
    assert similar["mean_absolute_entry_difference"] == 0.0


def test_repeated_result_writer_refuses_to_replace_existing_file(tmp_path) -> None:
    existing = tmp_path / REPEATED_RESULT_FILENAME
    existing.write_text("existing result", encoding="utf-8")
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        write_repeated_experiment_artifact({"placeholder": True}, tmp_path)
