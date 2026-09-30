import pytest

from _lessons import load_lesson


def test_lesson_21_noise_breaks_bigger_circuits_sooner(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    lesson = load_lesson("21")
    result = lesson.main()
    gates, results = result["gates"], result["results"]
    assert gates["Grover n=3"] < gates["Grover n=4"] < gates["Shor N=15"] < gates["Grover n=5"]
    for name, row in results.items():
        norm = row["normalised"]
        assert norm[1e-3] > norm[1e-2] > norm[3e-2] - 0.05  # success falls as p grows
        assert norm[3e-2] < 0.3
    # Within Grover, bigger circuits break sooner.
    for p in (1e-3, 3e-3, 1e-2):
        assert results["Grover n=3"]["normalised"][p] > results["Grover n=4"]["normalised"][p] > results["Grover n=5"]["normalised"][p]
    # Across algorithms, size is not everything: Shor-15 outlasts Grover n=4 despite having more gates.
    assert results["Shor N=15"]["normalised"][1e-2] > results["Grover n=4"]["normalised"][1e-2] + 0.15
    where = result["where"]
    assert where["work"]["success"] > where["counting"]["success"] + 0.1  # counting-register errors hurt most
    assert result["n21_gates"] > 10_000
    assert result["n21_estimates"][1e-3] < 1e-6
    assert (tmp_path / "21_why_errors_matter.png").exists()
