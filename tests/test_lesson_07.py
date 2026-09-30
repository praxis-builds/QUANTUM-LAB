from _lessons import load_lesson


def test_lesson_07_oracle_writes_f_and_kickback_writes_its_phase(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    lesson = load_lesson("07")
    result = lesson.main()
    for name, table in lesson.FUNCTIONS.items():
        assert result["flips"][name] == {f"x={x}": f"y={table[x]}" for x in (0, 1)}
        assert result["signs"][name] == [(-1) ** table[x] for x in (0, 1)]
        assert result["target_bloch"][name] == [-1.0, 0.0, 0.0]  # the output qubit stays |->
        expected = "0" if table[0] == table[1] else "1"
        assert result["counts"][name] == {expected: lesson.SHOTS}
