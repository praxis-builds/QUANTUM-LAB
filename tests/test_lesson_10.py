from _lessons import load_lesson


def test_lesson_10_every_y_is_orthogonal_to_s_and_s_is_recovered(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    lesson = load_lesson("10")
    result = lesson.main()
    for s in lesson.SECRETS:
        n = len(s)
        check = result["checks"][s]
        assert set(check["dots"].values()) == {0}  # y . s = 0 mod 2 for every measured y
        assert len(check["counts"]) == 2 ** (n - 1)  # and every orthogonal y does appear
        assert sum(check["counts"].values()) == lesson.CHECK_SHOTS
        assert result["solved"][s]["first"] == s
        assert result["solved"][s]["correct"] == lesson.REPEATS
        assert n - 1 <= result["solved"][s]["mean_runs"] < 2 * n
        classical = result["classical"][s]
        assert classical["max"] <= classical["worst_case"] == 2 ** (n - 1) + 1


def test_lesson_10_every_orthogonal_run_sequence_for_all_small_periods():
    lesson = load_lesson("10")
    for s in ("01", "10", "11", "011", "101", "111", "0011", "1000"):
        n = len(s)
        ys = lesson.measured_runs(s, shots=400, seed=7)
        assert all(bin(y & int(s, 2)).count("1") % 2 == 0 for y in ys)
        found, _ = lesson.simon_solve(ys, n)
        assert found == int(s, 2)
