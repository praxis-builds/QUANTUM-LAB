import math

from _lessons import load_lesson


def test_lesson_28_distillation(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    lesson = load_lesson("28")
    result = lesson.main()
    assert result["linear"]
    rows = result["rows"]
    for name in ("noise 0.01", "noise 0.03", "noise 0.05"):
        row = rows[name]
        assert row["status"] == "key" and row["keys_equal"] and row["residual_errors"] == 0
        assert 0 < row["m"] == row["n"] - row["leaked"] - math.ceil(row["n"] * lesson.binary_entropy(row["q_bound"])) - lesson.SAFETY
        assert row["fraction"] < row["asymptotic_fraction"]  # never beats the Shor-Preskill limit
        assert row["q_bound"] > row["q_est"]
    for name in ("noise 0.12", "Eve, every qubit"):
        assert rows[name]["status"].startswith("ABORT") and rows[name]["m"] == 0
    assert rows["Eve, every qubit"]["q_est"] > 0.2
    assert lesson.shor_preskill_rate(0.11) < 0.001 < lesson.shor_preskill_rate(0.109)  # the 11% threshold
    assert (tmp_path / "28_key_rate.png").exists()
