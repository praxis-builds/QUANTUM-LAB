"""Claims in the lesson texts that the full review found wrong or unsourced (docs/REVIEW-FINDINGS.md 16-18)."""

from __future__ import annotations

import pytest

from _lessons import LESSONS


def text(name: str) -> str:
    return (LESSONS / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("name", ["14_shor_15.md", "15_shor_21.md"])
def test_beauregard_cost_matches_the_paper(name):
    page = text(name)
    # Abstract of arXiv:quant-ph/0205095: "2n+3 qubits and O(n^3 lg(n)) elementary quantum gates in a depth of O(n^3)"
    assert "O(n³ log n)" in page and "depth O(n³)" in page and "quant-ph/0205095" in page
    assert "O(n³) gates" not in page


def test_lesson_21_describes_qiskits_depolarizing_channel():
    from qiskit_aer.noise import depolarizing_error

    page = text("21_why_errors_matter.md")
    assert "hit by a random Pauli error" not in page
    assert "3p/4" in page and "15p/16" in page
    # the numbers the page now states, checked against the channel the lesson simulates (_qec.py)
    for qubits, error_weight in ((1, 3 / 4), (2, 15 / 16)):
        channel = depolarizing_error(0.1, qubits)
        assert 1 - max(channel.probabilities) == pytest.approx(0.1 * error_weight)


def test_lesson_21_gate_error_figure_is_labelled_not_cited():
    page = text("21_why_errors_matter.md")
    assert "a typical error rate for today's best two-qubit gates" not in page
    assert "order of magnitude" in page
