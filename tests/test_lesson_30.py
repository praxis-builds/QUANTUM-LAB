from _lessons import load_lesson


def test_lesson_30_shor_break_ecc_bounds_and_mosca(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    lesson = load_lesson("30")
    result = lesson.main()
    assert result["plain"] == "HIDE" and result["factors"] == (3, 7) and result["d"] == 5
    assert result["curves"] == {"P-256": 2330, "P-384": 3484, "P-521": 4719}
    verdicts = result["verdicts"]
    assert verdicts["web session keys"] == {10: False, 15: False, 20: False}
    assert verdicts["customer records"] == {10: True, 15: False, 20: False}  # 10 + 5 > 15 is false
    assert all(verdicts["health / legal archives"].values())
    assert "FIPS 203" in result["replacements"]["RSA / ECDH / DH key exchange"]
