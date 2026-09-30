from _lessons import load_lesson


def test_lesson_16_toy_rsa_round_trip_and_attack(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    lesson = load_lesson("16")
    result = lesson.main()
    key = result["key"]
    assert key == {"N": 21, "e": 5, "d": 5, "phi": 12}
    assert result["round_trip"]
    assert all(lesson.decrypt(lesson.encrypt([m], 5, 21), 5, 21) == [m] for m in range(21))
    assert result["cipher"] == [7, 8, 12, 16]
    assert result["fixed_points"] == [0, 1, 6, 7, 8, 13, 14, 15, 20]  # (1 + gcd(4, 2)) * (1 + gcd(4, 6)) = 9
    assert result["identity_e"] == [7]
    # The attack uses only (N, e): factors come from quantum period finding with a = 2.
    assert result["quantum_path"][-1]["factors"] == (3, 7)
    assert result["quantum_path"][-1]["candidate"] == 6
    assert result["recovered_d"] == key["d"]
    assert result["recovered"] == lesson.MESSAGE == "HIDE"
    assert result["attack"]["factors"] == (3, 7)
    assert result["trial_division"] == (3, 7, 2)
