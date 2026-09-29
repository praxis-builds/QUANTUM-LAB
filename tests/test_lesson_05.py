import pytest

from _lessons import load_lesson


def test_lesson_05_grover_success_is_one_and_classical_is_2_25(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    result = load_lesson("05").main()
    for item, probability in result["success"].items():
        assert probability == pytest.approx(1.0, abs=1e-12), item
    assert result["counts"] == {"10": 2000}
    assert result["stages"]["prepare"] == pytest.approx([0.5, 0.5, 0.5, 0.5])
    assert result["stages"]["oracle"] == pytest.approx([0.5, 0.5, -0.5, 0.5])  # only the marked sign flips
    assert result["classical_exact"] == 2.25
    assert result["classical_simulated"] == pytest.approx(2.25, abs=0.02)
