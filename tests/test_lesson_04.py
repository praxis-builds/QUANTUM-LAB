import pytest

from _lessons import load_lesson


def test_lesson_04_bell_correlation_and_cz_cancellation(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    result = load_lesson("04").main()
    assert result["results"]["bell"]["p_same"] == 1.0
    assert result["results"]["product"]["p_same"] == pytest.approx(0.5, abs=0.05)
    for name in ("product", "bell"):
        assert result["results"][name]["p_q0_is_1"] == pytest.approx(0.5, abs=0.05)
        assert result["results"][name]["p_q1_is_1"] == pytest.approx(0.5, abs=0.05)
    assert result["purities"]["product"] == pytest.approx(1.0)
    assert result["purities"]["bell"] == pytest.approx(0.5)
    assert result["purity_with_cz"] < 0.99  # the lab's map entangles ...
    assert result["kernel_with_cz"] == pytest.approx(result["kernel_without_cz"], abs=1e-12)  # ... but the kernel ignores it
