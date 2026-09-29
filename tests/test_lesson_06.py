import pytest

from _lessons import load_lesson


def test_lesson_06_noise_lowers_grover_success_and_matches_aer(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    result = load_lesson("06").main()
    success = result["success"]
    assert success[0.0] == pytest.approx(1.0, abs=1e-12)  # ideal Grover
    strengths = sorted(success)
    values = [success[p] for p in strengths]
    assert all(a >= b - 1e-12 for a, b in zip(values, values[1:]))  # noise never helps
    assert success[1.0] == pytest.approx(0.25, abs=1e-9)  # fully random noise = one random guess
    assert success[0.01] < 0.95
    assert result["coherence_ratio"][0.0] == pytest.approx(1.0)
    assert result["coherence_ratio"][0.5] < 0.05
    assert result["numpy_value"] == pytest.approx(result["aer_value"], abs=1e-9)
    assert (tmp_path / "06_noise_success.png").exists()
