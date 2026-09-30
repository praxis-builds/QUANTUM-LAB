import math

import pytest

from _lessons import load_lesson


def test_lesson_27_intercept_resend_is_caught(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    lesson = load_lesson("27")
    result = lesson.main()
    sigma = math.sqrt(0.25 * 0.75 / result["sifted"])
    assert abs(result["qber"] - 0.25) <= 4 * sigma  # seeded, stated tolerance 4 sigma
    assert result["by_eve_basis"]["right"] == 0.0
    assert result["by_eve_basis"]["wrong"] == pytest.approx(0.5, abs=0.03)
    for k, row in result["detection"].items():
        # P(miss) formula vs simulation: 4 sigma of the trials, plus the pool's own QBER offset
        pool = (1 - result["qber"]) ** k
        tolerance = 4 * math.sqrt(row["formula"] * (1 - row["formula"]) / lesson.TRIALS) + abs(pool - row["formula"])
        assert abs(row["simulated"] - row["formula"]) <= tolerance, k
    assert result["k_needed"] == 49
    for f, row in result["partial"].items():
        assert row["errors_elsewhere"] == 0  # errors only where Eve used the wrong basis
        half_sigma = math.sqrt(0.25 / row["wrong_basis_count"])
        assert abs(row["error_rate_wrong_basis"] - 0.5) <= 4 * half_sigma, f
        assert row["knows"] == pytest.approx(f / 2, abs=0.02)
    assert result["eve_right_overall"] == pytest.approx(0.75, abs=0.02)
    assert (tmp_path / "27_detection.png").exists()
