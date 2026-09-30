import pytest

from _lessons import load_lesson

# Stated threshold: per-run P(run gives r) >= 0.45 on 2000 seeded shots (theory 0.500).
PER_RUN_THRESHOLD = 0.45


def test_lesson_14_shor_factors_15(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    lesson = load_lesson("14")
    result = lesson.main()
    for m, table in result["tables"].items():
        assert all(table[y] == m * y % 15 for y in range(1, 15))
    assert result["peaks"] == pytest.approx({0: 0.25, 64: 0.25, 128: 0.25, 192: 0.25})
    assert result["qubits"] == 12
    for a, row in result["per_a"].items():
        assert row["exact"] == pytest.approx(0.5, abs=1e-9)
        assert row["sampled"] >= PER_RUN_THRESHOLD
        assert set(row["outcomes"]) <= {0, 64, 128, 192} if row["r"] == 4 else set(row["outcomes"]) <= {0, 128}
        assert (row["factors"] == (3, 5)) == (a != 14)
    summary = result["summary"]
    assert summary["found"] == lesson.REPEATS  # 3 x 5 in every seeded repeat
    assert summary["max_quantum_runs"] <= 10
