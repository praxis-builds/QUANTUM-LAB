"""Quantum Fourier transform and phase estimation (shared by lessons 11-12).

Ordering and sign, stated once because they are a classic trap:
- A basis state |j> is labelled by the integer j = sum of bit_k << k (qubit 0 is the lowest bit),
  exactly as in Qiskit and the rest of this lab.
- The QFT maps |j> to (1/sqrt(N)) sum_k e^{+2 pi i j k / N} |k>, with N = 2**n.
- numpy.fft.fft uses e^{-2 pi i j k / N} and no 1/sqrt(N). So the QFT matrix is
  numpy.fft.ifft(..., norm="ortho") (the + sign), which equals sqrt(N) * ifft, not fft.
- Without the final swaps, the circuit's output qubits come out in reverse order.
"""

from __future__ import annotations

import math

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector


def qft_circuit(n: int, *, swaps: bool = True) -> QuantumCircuit:
    """H on the top qubit, then controlled phases pi/2, pi/4, ... from each lower qubit; repeat downwards.

    The circuit writes the frequency bits into the qubits in reverse order; the swaps put them back.
    """
    circuit = QuantumCircuit(n, name="QFT")
    for target in reversed(range(n)):
        circuit.h(target)
        for control in reversed(range(target)):
            circuit.cp(math.pi / 2 ** (target - control), control, target)
    if swaps:
        for k in range(n // 2):
            circuit.swap(k, n - 1 - k)
    return circuit


def dft_matrix(n: int) -> np.ndarray:
    """F[k, j] = e^{+2 pi i j k / N} / sqrt(N): column j is the QFT of |j>."""
    return np.fft.ifft(np.eye(2**n), axis=0, norm="ortho")


def bit_reversal(n: int) -> np.ndarray:
    """Permutation matrix sending |j> to |j with its n bits reversed>."""
    size = 2**n
    matrix = np.zeros((size, size))
    for j in range(size):
        matrix[int(format(j, f"0{n}b")[::-1], 2), j] = 1.0
    return matrix


def periodic_state(n: int, period: int, shift: int = 0) -> np.ndarray:
    """Equal amplitudes on shift, shift + period, shift + 2*period, ... (all below 2**n)."""
    state = np.zeros(2**n, dtype=complex)
    state[shift::period] = 1.0
    return state / np.linalg.norm(state)


def qpe_circuit(phase: float, counting: int, *, measure: bool = False) -> QuantumCircuit:
    """Estimate the phase of U = P(2 pi phase) on its eigenstate |1>.

    Counting qubits 0..t-1 start in |+>; the target (qubit t) starts in |1>. Counting qubit k
    controls U^(2^k) = P(2 pi phase 2^k), which kicks the phase e^{2 pi i phase 2^k} back onto it.
    The inverse QFT turns those phases into the integer m ~ phase * 2^t.
    """
    t = counting
    circuit = QuantumCircuit(t + 1, t if measure else 0)
    circuit.x(t)
    circuit.h(range(t))
    for k in range(t):
        circuit.cp(2 * math.pi * phase * 2**k, k, t)
    circuit.compose(qft_circuit(t).inverse(), qubits=range(t), inplace=True)
    if measure:
        circuit.measure(range(t), range(t))
    return circuit


def qpe_distribution(phase: float, counting: int) -> np.ndarray:
    """Exact probability of each readout m = 0 .. 2^t - 1 (the target qubit is traced out)."""
    return Statevector(qpe_circuit(phase, counting)).probabilities(list(range(counting)))


def phase_error(m: int, counting: int, phase: float) -> float:
    """Distance from m / 2^t to the true phase, measured around the circle (phases wrap at 1)."""
    gap = abs(m / 2**counting - phase) % 1.0
    return min(gap, 1.0 - gap)
