import numpy as np
import pytest

from _lessons import load_lesson


def test_lesson_02_hh_returns_zero_and_classical_coin_does_not(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    result = load_lesson("02").main()
    np.testing.assert_allclose(result["amplitudes_after_hh"], [1.0, 0.0], atol=1e-12)  # H.H returns |0>
    np.testing.assert_allclose(result["amplitudes_after_h"], [2**-0.5, 2**-0.5], atol=1e-12)
    assert result["amplitude_one_total"] == pytest.approx(0.0, abs=1e-12)
    assert result["counts_hh"] == {"0": 2000}
    assert abs(result["counts_h"]["0"] - 1000) < 100
    assert result["classical_after_two"] == pytest.approx([0.5, 0.5])
