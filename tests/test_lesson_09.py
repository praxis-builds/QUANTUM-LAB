import pytest

from _lessons import load_lesson


def test_lesson_09_returns_s_with_probability_one(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    lesson = load_lesson("09")
    result = lesson.main()
    for s in lesson.SECRETS:
        assert result["runs"][s]["p_secret"] == pytest.approx(1.0, abs=1e-12)
        assert result["runs"][s]["counts"] == {s: lesson.SHOTS}
        assert result["classical"][s] == {"found": s, "queries": len(s)}
