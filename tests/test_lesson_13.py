import pytest

from _lessons import load_lesson


def test_lesson_13_period_gives_factors_and_failures_are_explained(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    result = load_lesson("13").main()
    rows15, rows21 = result["rows15"], result["rows21"]
    assert [a for a, row in rows15.items() if row["kind"] == "fail"] == [14]
    assert all(row["factors"] in ((3, 5), (5, 3)) for row in rows15.values() if row["kind"] != "fail")
    assert {a for a, row in rows21.items() if row["kind"] == "fail"} == {4, 5, 16, 17, 20}
    assert {a for a, row in rows21.items() if row["kind"] == "lucky"} == {3, 6, 7, 9, 12, 14, 15, 18}
    assert result["retry"][15]["p_success"] == pytest.approx(12 / 13)
    assert result["retry"][21]["p_success"] == pytest.approx(14 / 19)
    assert result["retry"][21]["mean_tries"] == pytest.approx(19 / 14, abs=0.03)
