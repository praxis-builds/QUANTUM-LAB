import math

from _lessons import load_lesson


def test_lesson_25_bigger_codes_help_below_threshold_and_hurt_above(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    lesson = load_lesson("25")
    result = lesson.main()
    table = result["table"]
    for p in lesson.BELOW:
        formulas = [table[d][p]["formula"] for d in lesson.DISTANCES]
        assert formulas == sorted(formulas, reverse=True), p  # d = 1 > 3 > 5 > 7
    for p in lesson.ABOVE:
        formulas = [table[d][p]["formula"] for d in lesson.DISTANCES]
        assert formulas == sorted(formulas), p  # d = 1 < 3 < 5 < 7
    for p in (0.05, 0.1, 0.2, 0.3):  # measured, seeded, clearly separated points
        measured = [table[d][p]["measured"] for d in lesson.DISTANCES]
        assert measured == sorted(measured, reverse=True), p
    for p in (0.6, 0.7):
        measured = [table[d][p]["measured"] for d in lesson.DISTANCES]
        assert measured == sorted(measured), p
    for d in lesson.DISTANCES:
        for p, row in table[d].items():
            sigma = math.sqrt(max(row["formula"] * (1 - row["formula"]), 1e-12) / (2 * lesson.SHOTS))
            assert abs(row["measured"] - row["formula"]) <= 4 * sigma + 2e-4, (d, p)
    assert result["ratios"][0.01][0] > result["ratios"][0.1][0] > 1  # further below threshold, bigger gain
    assert (tmp_path / "25_threshold.png").exists()


def test_run_seeds_are_far_apart():
    load_lesson("22")  # puts lessons/ on sys.path
    import _qec

    seeds = [_qec.run_seed(k) for k in range(100)]
    assert min(b - a for a, b in zip(seeds, seeds[1:])) >= 10**6 > 20_000  # more than any shot count used
    assert max(seeds) < 2**31
