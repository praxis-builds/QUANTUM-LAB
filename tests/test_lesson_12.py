import math

import pytest

from _lessons import load_lesson


def test_lesson_12_exact_phases_read_out_with_certainty(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    lesson = load_lesson("12")
    result = lesson.main()
    t_gate = result["exact"]["T"]
    assert t_gate["probabilities"][0b001] == pytest.approx(1.0, abs=1e-12)  # T: 001 with probability 1
    assert t_gate["counts"] == {"001": lesson.SHOTS}
    assert result["exact"]["S"]["counts"] == {"010": lesson.SHOTS}
    assert result["angles"] == pytest.approx([0.125, 0.25, 0.5])  # kickback: 2^k x 1/8
    assert result["eigenphases"] == pytest.approx([0.0, 1 / 3])
    assert (tmp_path / "12_phase_estimation.png").exists()

    third = result["third"]
    ts = list(lesson.COUNTING)
    # More counting qubits sharpen the estimate: error of the best estimate halves, and
    # a close estimate becomes more likely ...
    for a, b in zip(ts, ts[1:]):
        assert third[b]["nearest_error"] == pytest.approx(third[a]["nearest_error"] / 2)
        assert third[b]["p_within"] > third[a]["p_within"]
    # ... but the single nearest value does NOT become more likely (the brief predicted it would).
    p_nearest = [third[t]["p_nearest"] for t in ts]
    assert p_nearest == sorted(p_nearest, reverse=True)
    limit = math.sin(math.pi / 3) ** 2 / (math.pi / 3) ** 2
    assert all(4 / math.pi**2 < p < 0.71 for p in p_nearest)
    assert p_nearest[-1] == pytest.approx(limit, abs=0.001)
    assert sum(result["counts_third_t3"].values()) == lesson.SHOTS
    assert max(result["counts_third_t3"], key=result["counts_third_t3"].get) == "011"
