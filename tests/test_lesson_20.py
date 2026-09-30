import math

import pytest

from _lessons import load_lesson


def test_lesson_20_grover_arithmetic(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    lesson = load_lesson("20")
    result = lesson.main()
    calls = result["calls"]
    assert calls["AES-128 key"] == pytest.approx(64 + math.log2(math.pi / 4))
    assert calls["AES-256 key"] == pytest.approx(128 + math.log2(math.pi / 4))
    assert calls["SHA-256 preimage"] == calls["AES-256 key"]
    # sqrt(p) parallelism: 2^20 machines cut the depth by 2^10 and raise total work by 2^10.
    depth0, total0 = result["parallel"][0]
    depth20, total20 = result["parallel"][20]
    assert depth0 - depth20 == pytest.approx(10) and total20 - total0 == pytest.approx(10)
    assert result["machines_for_2_40"] == pytest.approx(128 - 2 * (40 - math.log2(math.pi / 4)))
    assert list(result["nist"]["AES-128 key"].values()) == [130, 106, 74]  # 2^170 / MAXDEPTH
