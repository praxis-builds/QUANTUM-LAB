import pytest

from _lessons import load_lesson


def test_lesson_17_optimum_over_rotation_and_unknown_m(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    lesson = load_lesson("17")
    result = lesson.main()
    for n, row in result["optimum"].items():
        assert row["p"] > 0.9 and row["p"] == pytest.approx(row["formula"], abs=1e-9)
        assert row["p_double"] < 0.3  # over-rotation
    assert [result["optimum"][n]["k"] for n in range(2, 9)] == [1, 2, 3, 4, 6, 8, 12]
    assert result["counts"]["0101"] > 900
    rows = result["unknown"]["rows"]
    assert rows[4]["p_at_k1"] < 0.05 and rows[8]["p_at_k1"] > 0.99  # periodic: a wrong k is a lottery
    assert rows[1]["bbht"] > rows[2]["bbht"] > rows[4]["bbht"] > rows[8]["bbht"]
    assert all(row["bbht"] < row["classical"] for row in rows.values())
    assert (tmp_path / "17_grover_iterations.png").exists()
