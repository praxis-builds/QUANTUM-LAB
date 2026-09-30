import pytest

from _lessons import load_lesson

# Stated threshold: per-run P(run gives r) >= 0.25 on 2000 seeded shots for r = 6 (theory 0.322).
PER_RUN_THRESHOLD_R6 = 0.25


def test_lesson_15_shor_factors_21(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    lesson = load_lesson("15")
    result = lesson.main()
    assert result["qubits"] == 15
    assert result["growth"][15]["total"] == 12 and result["growth"][21]["total"] == 15
    per_a = result["per_a"]
    assert {a for a, row in per_a.items() if row["factors"] == (3, 7)} == {2, 8, 10, 11, 13, 19}
    assert {a: row["reason"] for a, row in per_a.items() if row["factors"] is None} == {
        4: "r is odd", 16: "r is odd",
        5: "a^(r/2) = -1 (mod N)", 17: "a^(r/2) = -1 (mod N)", 20: "a^(r/2) = -1 (mod N)",
    }
    for row in per_a.values():
        if row["r"] == 6:
            assert row["exact"] == pytest.approx(0.322, abs=0.001)
            assert row["sampled"] >= PER_RUN_THRESHOLD_R6
        assert row["sampled"] == pytest.approx(row["exact"], abs=0.05)
    assert result["summary"]["found"] == lesson.REPEATS  # 3 x 7 in every seeded repeat
    assert result["summary"]["max_quantum_runs"] <= 15
    candidates = {row["m"]: row["candidate"] for row in result["readout"]}
    assert candidates[171] == 6 and candidates[853] == 6 and candidates[512] == 2
