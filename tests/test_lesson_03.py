import numpy as np
import pytest

from _lessons import load_lesson


def test_lesson_03_phase_is_invisible_until_h(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    result = load_lesson("03").main()
    np.testing.assert_allclose(result["plus"], [2**-0.5, 2**-0.5], atol=1e-12)
    np.testing.assert_allclose(result["minus"], [2**-0.5, -(2**-0.5)], atol=1e-12)
    for sign in "+-":
        assert abs(result["direct"][sign]["0"] - 1000) < 100  # both look 50/50
    assert result["after_h"]["+"] == {"0": 2000}
    assert result["after_h"]["-"] == {"1": 2000}
    np.testing.assert_allclose(result["sweep_measured"], result["sweep_predicted"], atol=0.05)
    assert (tmp_path / "03_phase_sweep.png").exists()
