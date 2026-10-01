from _lessons import load_lesson
from _pqc_skip import needs_pqc


@needs_pqc
def test_lesson_32_hybrid_needs_both_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    lesson = load_lesson("32")
    result = lesson.main()
    assert result["keys_match"]
    assert (result["client_hello"], result["server_hello"]) == (32 + 1184, 32 + 1088)
    attacker = result["attacker"]
    assert attacker == {
        "knows X25519 secret (e.g. via Shor), guesses ML-KEM": False,
        "knows ML-KEM secret (hypothetical lattice break), guesses X25519": False,
        "knows both": True,
    }


@needs_pqc
def test_lesson_32_combiner_depends_on_every_input():
    lesson = load_lesson("32")
    a, b, t = b"\x01" * 32, b"\x02" * 32, b"transcript"
    key = lesson.combine(a, b, t)
    assert len(key) == 32 and key == lesson.combine(a, b, t)
    assert key != lesson.combine(b, a, t) and key != lesson.combine(a, b, t + b"!")
