import numpy as np
import pytest

from praxis_quantum_lab.finite_shot_psd import (
    PSD_REPAIR_PLOT_FILENAME,
    PSD_REPAIR_RESULT_FILENAME,
    estimate_full_kernel_matrix,
    repair_kernel_psd,
    write_psd_repair_artifacts,
)


def test_spectral_repair_is_symmetric_psd_unit_diagonal_and_preserves_raw() -> None:
    raw = np.array(
        [[1.0, 0.9, 0.9], [0.9, 1.0, -0.9], [0.9, -0.9, 1.0]],
        dtype=np.float64,
    )
    original = raw.copy()
    repaired = repair_kernel_psd(raw)
    assert np.array_equal(raw, original)
    assert np.allclose(repaired, repaired.T, atol=1e-12)
    assert np.allclose(np.diag(repaired), 1.0, atol=1e-12)
    assert np.linalg.eigvalsh(repaired).min() >= -1e-10
    assert np.linalg.norm(repaired - raw, ord="fro") > 0.0


def test_repair_rejects_nonsymmetric_or_non_unit_diagonal_inputs() -> None:
    with pytest.raises(ValueError, match="symmetric"):
        repair_kernel_psd(np.array([[1.0, 0.2], [0.4, 1.0]]))
    with pytest.raises(ValueError, match="unit diagonal"):
        repair_kernel_psd(np.array([[1.0, 0.2], [0.2, 0.8]]))


def test_all_pair_shot_kernel_reproduces_with_fixed_seed() -> None:
    points = np.array([[-0.3, 0.4], [0.1, -0.2], [0.8, 0.5]])
    first = estimate_full_kernel_matrix(points, shots=128, seed=771)
    second = estimate_full_kernel_matrix(points, shots=128, seed=771)
    assert np.array_equal(first, second)
    assert np.allclose(first, first.T)
    assert np.array_equal(np.diag(first), np.ones(3))


def test_psd_repair_writer_refuses_to_overwrite_either_artifact(tmp_path) -> None:
    existing_plot = tmp_path / PSD_REPAIR_PLOT_FILENAME
    existing_plot.write_bytes(b"preserve")
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        write_psd_repair_artifacts({}, tmp_path)
    assert existing_plot.read_bytes() == b"preserve"
    assert not (tmp_path / PSD_REPAIR_RESULT_FILENAME).exists()
