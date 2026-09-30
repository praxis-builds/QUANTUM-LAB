"""QFT and phase-estimation helpers (lessons/_qft.py): ordering, sign, inverse, readout."""

from __future__ import annotations

import math
import sys

import numpy as np
import pytest
from qiskit.circuit.library import QFTGate
from qiskit.quantum_info import Operator

from _lessons import LESSONS

if str(LESSONS) not in sys.path:
    sys.path.insert(0, str(LESSONS))

import _qft as qft  # noqa: E402


@pytest.mark.parametrize("n", [1, 2, 3, 4])
def test_qft_unitary_is_the_dft_with_documented_ordering(n):
    """Index = Qiskit integer (qubit 0 lowest); F[k, j] = e^{+2 pi i jk/N} / sqrt(N)."""
    size = 2**n
    unitary = Operator(qft.qft_circuit(n)).data
    j, k = np.meshgrid(np.arange(size), np.arange(size))
    np.testing.assert_allclose(unitary, np.exp(2j * np.pi * j * k / size) / np.sqrt(size), atol=1e-12)
    np.testing.assert_allclose(unitary, qft.dft_matrix(n), atol=1e-12)
    np.testing.assert_allclose(unitary, np.sqrt(size) * np.fft.ifft(np.eye(size), axis=0), atol=1e-12)
    np.testing.assert_allclose(unitary, Operator(QFTGate(n)).data, atol=1e-12)  # Qiskit's own QFT


@pytest.mark.parametrize("n", [2, 3, 4])
def test_the_sign_and_order_traps_are_real(n):
    unitary = Operator(qft.qft_circuit(n)).data
    fft = np.fft.fft(np.eye(2**n), axis=0, norm="ortho")
    assert np.max(np.abs(unitary - fft)) > 0.1  # numpy's fft has the opposite sign ...
    np.testing.assert_allclose(unitary, fft.conj(), atol=1e-12)  # ... so the QFT is its conjugate
    no_swaps = Operator(qft.qft_circuit(n, swaps=False)).data
    assert np.max(np.abs(no_swaps - unitary)) > 0.1
    np.testing.assert_allclose(no_swaps, qft.bit_reversal(n) @ qft.dft_matrix(n), atol=1e-12)


@pytest.mark.parametrize("n", [1, 2, 3, 4])
def test_inverse_qft_times_qft_is_identity(n):
    circuit = qft.qft_circuit(n)
    product = Operator(circuit.inverse()).data @ Operator(circuit).data
    np.testing.assert_allclose(product, np.eye(2**n), atol=1e-12)


def test_qpe_is_exact_for_representable_phases():
    for phase, counting in ((1 / 8, 3), (1 / 4, 2), (1 / 4, 3), (3 / 8, 3), (5 / 16, 4), (0.0, 3)):
        probabilities = qft.qpe_distribution(phase, counting)
        assert probabilities[round(phase * 2**counting)] == pytest.approx(1.0, abs=1e-12)


def test_phase_error_wraps_around_the_circle():
    assert qft.phase_error(0, 3, 0.95) == pytest.approx(0.05)
    assert qft.phase_error(3, 3, 1 / 3) == pytest.approx(3 / 8 - 1 / 3)
    assert math.isclose(qft.phase_error(4, 3, 0.5), 0.0)
