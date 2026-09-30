import pytest

from _lessons import load_lesson


def test_lesson_29_simulated_randomness_is_reproducible_and_testable(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    result = load_lesson("29").main()
    assert result["identical_same_seed"] and not result["identical_other_seed"]  # same seed, same bits
    assert result["agreement_other_seed"] == pytest.approx(0.5, abs=0.03)
    assert result["shifted_mid_circuit"] == 1.0  # the per-shot seed rule, shown directly
    tests = result["tests"]
    assert tests["Aer H|0> bits"]["pass"] and tests["NumPy PCG64 (seed 1)"]["pass"]
    assert not tests["Aer biased coin, P(1) = 0.8"]["pass"] and not tests["alternating 0101..."]["pass"]
    vn = result["von_neumann"]
    assert abs(vn["output_ones"] - 0.5) < 0.02 and vn["tests"]["pass"]
    assert vn["yield_per_pair"] == pytest.approx(vn["expected_yield"], abs=0.01)
    assert result["correlated_output"] == [0]
