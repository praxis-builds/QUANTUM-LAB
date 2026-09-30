import pytest

from _lessons import load_lesson


def test_lesson_11_qft_is_the_dft_finds_periods_and_inverts(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    result = load_lesson("11").main()
    checks = result["checks"]
    for same in ("QFT vs DFT (+ sign, 1/sqrt N)", "QFT vs conjugate of that fft", "QFT vs Qiskit's library QFTGate",
                 "circuit without swaps vs bit-reversed DFT"):
        assert checks[same] < 1e-12, same
    for different in ("QFT vs numpy fft, norm='ortho' (- sign)", "circuit without swaps vs DFT"):
        assert checks[different] > 0.5, different
    assert result["peaks"] == {
        "period 2 (0,2,4,6)": [0, 4],
        "period 2 shifted (1,3,5,7)": [0, 4],
        "period 4 (0,4)": [0, 2, 4, 6],
    }
    shifted = result["outputs"]["period 2 shifted (1,3,5,7)"]
    assert shifted[4] == pytest.approx(-(2**-0.5))  # a shift changes only the phase of a peak
    assert result["restore_error"] < 1e-12 and result["identity_error"] < 1e-12
    assert set(result["counts"]) == {"000", "100"} and sum(result["counts"].values()) == 2000
    assert result["classical_power"] == pytest.approx([0.5, 0, 0, 0, 0.5, 0, 0, 0])
    assert (tmp_path / "11_qft_peaks.png").exists()
