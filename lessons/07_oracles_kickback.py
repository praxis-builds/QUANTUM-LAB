"""Lesson 07: oracles and phase kickback. A function's answer can be written into a phase."""

from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from _common import SEED, heading
from _oracles import describe, truth_table_oracle
from praxis_quantum_lab.circuit_playground import bloch_vectors
from praxis_quantum_lab.qiskit_experiments import ideal_counts

SHOTS = 1000
# All four functions from one bit to one bit, as truth tables (f(0), f(1)).
FUNCTIONS = {
    "constant 0": (0, 0),
    "constant 1": (1, 1),
    "identity": (0, 1),
    "NOT": (1, 0),
}


def bit_flip_table(table: tuple[int, int]) -> dict[str, str]:
    """Oracle on |x>|y> with y = 0: the output qubit ends up holding f(x)."""
    rows = {}
    for x in (0, 1):
        circuit = QuantumCircuit(2)
        if x:
            circuit.x(0)
        circuit.compose(truth_table_oracle(table), inplace=True)
        probabilities = Statevector(circuit).probabilities_dict()
        label = max(probabilities, key=probabilities.get)
        rows[f"x={x}"] = f"y={label[0]}"  # label is "q1 q0" = "y x"
    return rows


def kickback_state(table: tuple[int, int]) -> Statevector:
    """Input in |+>, output qubit in |->, then one oracle call."""
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.x(1)
    circuit.h(1)
    circuit.compose(truth_table_oracle(table), inplace=True)
    return Statevector(circuit)


def input_signs(state: Statevector) -> list[int]:
    """With the output in |->, amplitude(x, y=0) = (-1)^f(x) / 2: read off the sign per x."""
    return [int(round(2 * state.data[x].real)) for x in (0, 1)]


def one_query_circuit(table: tuple[int, int]) -> QuantumCircuit:
    """Kickback, then H on the input, then measure only the input."""
    circuit = QuantumCircuit(2, 1)
    circuit.h(0)
    circuit.x(1)
    circuit.h(1)
    circuit.compose(truth_table_oracle(table), inplace=True)
    circuit.h(0)
    circuit.measure(0, 0)
    return circuit


def main() -> dict:
    heading("Step 1: an oracle is a reversible gate |x>|y> -> |x>|y XOR f(x)>")
    flips = {}
    for name, table in FUNCTIONS.items():
        flips[name] = bit_flip_table(table)
        print(f"{name:<11} f = {describe(table)}   with y starting at 0: {flips[name]}")
    print("With the output qubit in |0>, the oracle just writes f(x) into it, like a classical call.")

    heading("Step 2: output qubit in |-> instead (phase kickback)")
    signs, target_bloch = {}, {}
    for name, table in FUNCTIONS.items():
        state = kickback_state(table)
        signs[name] = input_signs(state)
        target_bloch[name] = [round(c, 12) + 0.0 for c in bloch_vectors(state.data, 2)[1]]
        print(f"{name:<11} input signs (x=0, x=1) = {signs[name]}   output qubit Bloch vector = {target_bloch[name]}")
    print("The output qubit stays |-> (Bloch vector (-1, 0, 0)) every time. The answer f(x)")
    print("has moved into the SIGN of the input's |x> amplitude: (-1)^f(x).")

    heading(f"Step 3: one H on the input turns that sign into a measurement ({SHOTS} shots each)")
    counts = {}
    for name, table in FUNCTIONS.items():
        counts[name] = ideal_counts(one_query_circuit(table), shots=SHOTS, seed=SEED)
        kind = "constant" if table[0] == table[1] else "balanced"
        print(f"{name:<11} ({kind}): counts = {counts[name]}")
    print("0 means f(0) = f(1), 1 means f(0) != f(1), after ONE oracle call.")

    heading("Step 4: the classical baseline")
    print("Classically you must ask for f(0) and f(1): 2 calls to know whether they are equal.")
    print("One call cannot do it: it tells you one value and nothing about the other.")
    print("The quantum circuit used 1 call, but it learned ONE bit (equal or not), not f itself.")
    return {"flips": flips, "signs": signs, "target_bloch": target_bloch, "counts": counts}


if __name__ == "__main__":
    main()
