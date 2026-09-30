import pytest

from _lessons import load_lesson


def test_lesson_08_constant_gives_all_zeros_and_balanced_never(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    result = load_lesson("08").main()
    assert len(result["n2"]) == 8  # 2 constant + all 6 balanced for n = 2
    for table, run in result["n2"].items():
        if run["kind"] == "constant":
            assert run["p_00"] == pytest.approx(1.0, abs=1e-12)
            assert run["counts"] == {"00": 1000}
        else:
            assert run["p_00"] == pytest.approx(0.0, abs=1e-12)
            assert "00" not in run["counts"]
    for n, size in result["sizes"].items():
        assert size["min_p_constant"] == pytest.approx(1.0, abs=1e-12)
        assert size["max_p_balanced"] == pytest.approx(0.0, abs=1e-12)
        assert size["classical_worst_case"] == 2 ** (n - 1) + 1
    assert [result["sizes"][n]["balanced_checked"] for n in (1, 2, 3, 4)] == [2, 6, 70, 50]
    for k, error in result["random_tester"].items():
        assert error["simulated"] == pytest.approx(error["exact"], abs=0.02)
    assert result["random_tester"][3]["exact"] == pytest.approx(0.2)
