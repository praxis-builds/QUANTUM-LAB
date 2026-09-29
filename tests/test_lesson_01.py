import numpy as np
import pytest

from _lessons import load_lesson


def test_lesson_01_key_numbers(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    result = load_lesson("01").main()
    assert result["probabilities"] == pytest.approx([0.7, 0.3])
    assert (tmp_path / "01_one_qubit_convergence.png").exists()
    # more shots -> smaller typical error, and the 10000-shot estimate is close
    errors = result["mean_error"]
    assert errors[10000] < errors[1000] < errors[100] < errors[10] < errors[1]
    assert abs(result["estimates"][10000] - 0.3) < 0.02
    # error scales like 1/sqrt(shots): 100x the shots -> about 10x smaller
    assert errors[100] / errors[10000] == pytest.approx(10, rel=0.35)
