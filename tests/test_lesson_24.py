import pytest

from _lessons import load_lesson


def test_lesson_24_shor_code_corrects_all_single_qubit_paulis(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    result = load_lesson("24").main()
    assert len(result["checks"]) == 27 and all(result["checks"].values()) and result["no_error"]
    assert result["syndromes"][(4, "x")] == "00 00 11 00"
    assert result["syndromes"][(4, "z")] == "11 00 00 00"
    assert result["syndromes"][(4, "y")] == "11 00 11 00"
    ry = result["ry"]
    for label, fidelity in ry.items():
        if label == "Y0 without correction":
            assert fidelity == pytest.approx(0.0, abs=1e-9)
        else:
            assert fidelity == pytest.approx(1.0, abs=1e-9), label
    two = result["two"]
    assert two["X on 0 and X on 3 (different blocks)"] and two["X on 2 and Z on 7"]
    assert not two["X on 0 and X on 1 (same block)"] and not two["Z on 0 and Z on 3 (different blocks)"]
    sweep = result["sweep"]
    assert all(sweep[p]["encoded"] < sweep[p]["bare"] for p in (0.001, 0.003, 0.01, 0.03))
    assert all(sweep[p]["encoded"] > sweep[p]["bare"] for p in (0.1, 0.2, 0.3))  # crossover: nine targets
    assert (tmp_path / "24_shor_nine_qubit_code.png").exists()
