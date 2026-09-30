"""Toy error-correcting codes (lessons/_qec.py): what each code fixes and what it cannot."""

from __future__ import annotations

import sys

import pytest

from _lessons import LESSONS

if str(LESSONS) not in sys.path:
    sys.path.insert(0, str(LESSONS))

import _qec as qec  # noqa: E402

CODES = {
    "bit_flip": (qec.bit_flip_code, 3, "x"),
    "phase_flip": (qec.phase_flip_code, 3, "z"),
    "shor9": (qec.shor9_code, 9, "xyz"),
}


def survives(code, state, errors, **kwargs):
    return qec.logical_error_rate(code(state, errors, **kwargs), state, shots=1, seed=1) == 0


@pytest.mark.parametrize("name", CODES)
def test_each_code_corrects_every_single_error_it_is_designed_for(name):
    code, n, fixes = CODES[name]
    for state in qec.INPUT_STATES:
        assert survives(code, state, [])
        for qubit in range(n):
            for pauli in fixes:
                assert survives(code, state, [(qubit, pauli)]), (state, qubit, pauli)


@pytest.mark.parametrize("name,pauli", [("bit_flip", "z"), ("bit_flip", "y"), ("phase_flip", "x"), ("phase_flip", "y")])
def test_codes_fail_on_error_types_they_are_not_designed_for(name, pauli):
    """The uncorrectable part of the error becomes a logical Z: |0> and |1> survive, every
    superposition input (|+>, |->, |+i>, |-i>) is flipped, on whichever qubit the error lands."""
    code, n, _ = CODES[name]
    for qubit in range(n):
        for state in qec.INPUT_STATES:
            assert survives(code, state, [(qubit, pauli)]) == (state in ("0", "1")), (qubit, state)


def test_without_the_correction_round_a_flip_on_the_read_out_qubit_is_a_logical_error():
    # Decoding alone just reads qubit 0 back, so only an error there reaches the output.
    assert not survives(qec.bit_flip_code, "0", [(0, "x")], correct=False)
    assert not survives(qec.phase_flip_code, "0", [(0, "z")], correct=False)
    assert survives(qec.bit_flip_code, "0", [(0, "x")])  # with the correction round it is fixed


def test_bit_flip_code_fails_on_two_flips():
    for pair in ((0, 1), (0, 2), (1, 2)):
        for state in ("0", "1"):
            assert not survives(qec.bit_flip_code, state, [(q, "x") for q in pair])


@pytest.mark.parametrize("d,p,expected", [(3, 0.1, 0.028), (1, 0.3, 0.3), (5, 0.5, 0.5)])
def test_repetition_logical_error_formula(d, p, expected):
    assert qec.repetition_logical_error(d, p) == pytest.approx(expected)
    if d == 3:
        assert qec.repetition_logical_error(3, p) == pytest.approx(3 * p**2 - 2 * p**3)
