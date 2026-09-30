import pytest

from _lessons import load_lesson


def test_lesson_23_phase_flip_code_and_blind_spots(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    lesson = load_lesson("23")
    result = lesson.main()
    everything, basis_only = list(lesson.INPUT_STATES), ["0", "1"]
    assert {q: row["syndrome"] for q, row in result["single"].items()} == {0: "01", 1: "11", 2: "10"}
    assert all(row["survivors"] == everything for row in result["single"].values())
    table = result["table"]
    assert table[("bit-flip code", "x")] == everything and table[("phase-flip code", "z")] == everything
    for key in (("bit-flip code", "z"), ("bit-flip code", "y"), ("phase-flip code", "x"), ("phase-flip code", "y")):
        assert table[key] == basis_only, key
    rates = result["rates"]
    # seeded, 4000 shots: designed-for error ~ 3p^2 - 2p^3, blind spot ~ odd-number formula (tolerance 0.02)
    assert rates[("bit-flip code", "x", "0")] == pytest.approx(result["designed_formula"], abs=0.01)
    assert rates[("phase-flip code", "z", "0")] == pytest.approx(result["designed_formula"], abs=0.01)  # 2 Zs -> logical X
    assert rates[("bit-flip code", "z", "+")] == pytest.approx(result["odd_formula"], abs=0.02)
    assert rates[("phase-flip code", "x", "+")] == pytest.approx(result["odd_formula"], abs=0.02)
    assert rates[("bit-flip code", "z", "+")] > lesson.P  # worse than no code
