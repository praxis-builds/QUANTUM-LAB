import pytest

from _lessons import load_lesson


def test_lesson_18_oracle_truth_table_marks_exactly_the_matching_keys():
    """Full truth table: for EVERY plaintext (secret key fixed), the 1-pair oracle flips the sign of
    exactly the keys that encrypt P to C, and returns its work qubits to 0 (asserted inside)."""
    lesson = load_lesson("18")
    for p in range(16):
        pair = [(p, lesson.encrypt(lesson.SECRET_KEY, p))]
        table = lesson.oracle_truth_table(pair)
        assert {k for k, sign in table.items() if sign == -1} == set(lesson.matching_keys(pair)), p
        assert set(table.values()) <= {1, -1}


def test_lesson_18_cipher_facts():
    lesson = load_lesson("18")
    assert sorted(lesson.SBOX) == list(range(16))
    # The brief's cipher S(P ^ k) is a bijection in k: one pair always fits exactly one key.
    for p in range(16):
        assert sorted(lesson.SBOX[p ^ k] for k in range(16)) == list(range(16))
    counts = {len(lesson.matching_keys([(p, lesson.encrypt(lesson.SECRET_KEY, p))])) for p in range(16)}
    assert counts == {1, 2}  # the whitened cipher can leave a false positive


def test_lesson_18_grover_finds_the_key(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    lesson = load_lesson("18")
    result = lesson.main()
    (p1, c1), (p2, c2) = result["pairs"]
    assert lesson.matching_keys([(p1, c1)]) == sorted([lesson.SECRET_KEY, 0b0100])
    assert lesson.matching_keys(result["pairs"]) == [lesson.SECRET_KEY]
    assert {k for k, s in result["tables"]["pairs 1+2"].items() if s == -1} == {lesson.SECRET_KEY}
    one, two = result["one_pair"], result["two_pairs"]
    assert one["M"] == 2 and one["iterations"] == 2 and one["p_any_match"] > 0.9
    assert one["p_secret"] == pytest.approx(0.5, abs=0.05)  # half the successes are the false positive
    assert two["M"] == 1 and two["iterations"] == 3 and two["qubits"] == 12
    assert two["p_secret"] > 0.9  # seeded: Grover finds the key
    assert max(two["counts"], key=two["counts"].get) == format(lesson.SECRET_KEY, "04b")
    assert result["classical_mean"] == pytest.approx(8.5, abs=0.2)
