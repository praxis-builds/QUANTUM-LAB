import pytest

from _lessons import load_lesson

SIFT_TOLERANCE = 0.02  # stated: sifting rate within 0.5 +- 0.02 on 20,000 qubits


def test_lesson_26_sifting_and_qber(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    result = load_lesson("26").main()
    assert result["sift_rate"] == pytest.approx(0.5, abs=SIFT_TOLERANCE)
    assert result["ideal_qber"] == 0.0
    for p, row in result["noisy"].items():
        assert abs(row["qber"] - p) <= 4 * row["sigma"], p
