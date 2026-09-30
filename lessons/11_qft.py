"""Lesson 11: the quantum Fourier transform turns a repeating pattern into sharp peaks."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import QFTGate
from qiskit.quantum_info import Operator, Statevector

from _common import SEED, heading, out_dir
from _qft import bit_reversal, dft_matrix, periodic_state, qft_circuit
from praxis_quantum_lab.qiskit_experiments import ideal_counts

N_QUBITS = 3
SHOTS = 2000
INPUTS = {  # name: (period, shift) over the 8 basis states
    "period 2 (0,2,4,6)": (2, 0),
    "period 2 shifted (1,3,5,7)": (2, 1),
    "period 4 (0,4)": (4, 0),
}


def ket(index: int) -> str:
    return f"|{index:0{N_QUBITS}b}>"


def show(label: str, vector: np.ndarray) -> None:
    parts = [f"{ket(i)} {v.real:+.3f}{v.imag:+.3f}i" for i, v in enumerate(vector) if abs(v) > 1e-9]
    print(f"{label:<30} " + ", ".join(parts))


def max_gap(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.max(np.abs(a - b)))


def plot(inputs: dict, outputs: dict):
    figure, axes = plt.subplots(2, len(inputs), figsize=(12, 5), sharey=True)
    labels = [format(i, f"0{N_QUBITS}b") for i in range(2**N_QUBITS)]
    for column, name in enumerate(inputs):
        axes[0, column].bar(labels, np.abs(inputs[name]) ** 2, color="tab:blue")
        axes[0, column].set_title(f"input: {name}", fontsize=9)
        axes[1, column].bar(labels, np.abs(outputs[name]) ** 2, color="tab:orange")
        axes[1, column].set_title("after QFT", fontsize=9)
    axes[0, 0].set_ylabel("probability")
    axes[1, 0].set_ylabel("probability")
    figure.tight_layout()
    path = out_dir() / "11_qft_peaks.png"
    figure.savefig(path, dpi=130)
    plt.close(figure)
    return path


def main() -> dict:
    heading("Step 1: the 3-qubit QFT from H, controlled-phase (CP) and one SWAP")
    circuit = qft_circuit(N_QUBITS)
    print(circuit.draw("text"))
    gates = [(instruction.operation.name, [circuit.find_bit(q).index for q in instruction.qubits]) for instruction in circuit.data]

    heading("Step 2: is it the DFT? Sign, normalisation and qubit order (the trap)")
    unitary = Operator(circuit).data
    checks = {
        "QFT vs DFT (+ sign, 1/sqrt N)": max_gap(unitary, dft_matrix(N_QUBITS)),
        "QFT vs numpy fft, norm='ortho' (- sign)": max_gap(unitary, np.fft.fft(np.eye(2**N_QUBITS), axis=0, norm="ortho")),
        "QFT vs conjugate of that fft": max_gap(unitary, np.fft.fft(np.eye(2**N_QUBITS), axis=0, norm="ortho").conj()),
        "QFT vs Qiskit's library QFTGate": max_gap(unitary, Operator(QFTGate(N_QUBITS)).data),
        "circuit without swaps vs DFT": max_gap(Operator(qft_circuit(N_QUBITS, swaps=False)).data, dft_matrix(N_QUBITS)),
        "circuit without swaps vs bit-reversed DFT": max_gap(
            Operator(qft_circuit(N_QUBITS, swaps=False)).data, bit_reversal(N_QUBITS) @ dft_matrix(N_QUBITS)
        ),
    }
    for name, gap in checks.items():
        print(f"{name:<44} max entry gap {gap:.2e}   {'SAME' if gap < 1e-10 else 'DIFFERENT'}")
    print("Index = Qiskit integer (q0 is the lowest bit). The QFT uses e^{+2 pi i jk/N}: it is")
    print("numpy's ifft with norm='ortho' (= sqrt(N) * ifft), NOT fft. Drop the swaps and the output")
    print("bits come out reversed.")

    heading("Step 3: periodic inputs over 8 states")
    inputs, outputs, peaks = {}, {}, {}
    for name, (period, shift) in INPUTS.items():
        inputs[name] = periodic_state(N_QUBITS, period, shift)
        outputs[name] = Statevector(inputs[name]).evolve(circuit).data
        peaks[name] = [i for i, v in enumerate(outputs[name]) if abs(v) ** 2 > 1e-9]
        show(f"in:  {name}", inputs[name])
        show("out: after QFT", outputs[name])
    print("Period r over N = 8 states -> peaks at multiples of N/r. A shift moves no peak; it only")
    print("changes the peaks' phases (compare the signs of |100> in the first two outputs).")

    heading("Step 4: the inverse QFT undoes it")
    inverse = qft_circuit(N_QUBITS).inverse()
    restore_error = max(max_gap(Statevector(outputs[name]).evolve(inverse).data, inputs[name]) for name in INPUTS)
    identity_error = max_gap(Operator(inverse).data @ unitary, np.eye(2**N_QUBITS))
    print(f"max |QFT^-1 QFT psi - psi| over the three inputs = {restore_error:.2e}")
    print(f"max |QFT^-1 QFT - I|                            = {identity_error:.2e}")

    heading(f"Step 5: the period-2 case measured on local Aer ({SHOTS} shots)")
    measured = QuantumCircuit(N_QUBITS, N_QUBITS)
    measured.h([1, 2])  # equal mix of |000>, |010>, |100>, |110> = 0, 2, 4, 6
    measured.compose(circuit, inplace=True)
    measured.measure(range(N_QUBITS), range(N_QUBITS))
    counts = ideal_counts(measured, shots=SHOTS, seed=SEED)
    print(f"counts = {counts}")

    heading("Step 6: the classical baseline")
    classical = np.abs(np.fft.fft(periodic_state(N_QUBITS, 2), norm="ortho")) ** 2
    print(f"numpy fft of the period-2 list: power = {np.round(classical, 3).tolist()}")
    print("Same peaks, from the classical FFT on 8 numbers in O(N log N) steps. The quantum circuit")
    print("needed the 8 amplitudes loaded first, and each shot returns ONE peak index, not the")
    print("spectrum. The QFT is not a faster FFT for your data; its use is inside algorithms.")
    path = plot(inputs, outputs)
    print(f"\nSaved {path}")
    return {
        "gates": gates, "checks": checks, "peaks": peaks,
        "outputs": {name: value.tolist() for name, value in outputs.items()},
        "restore_error": restore_error, "identity_error": identity_error,
        "counts": counts, "classical_power": classical.tolist(),
    }


if __name__ == "__main__":
    main()
