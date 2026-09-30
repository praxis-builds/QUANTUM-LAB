"""Lesson 23: the phase-flip code, and why each 3-qubit code is blind to the other's errors."""

from __future__ import annotations

from qiskit_aer import AerSimulator

from _common import SEED, heading
from _qec import INPUT_STATES, bit_flip_code, logical_error_rate, pauli_channel_noise, phase_flip_code, run_seed

CODES = {"bit-flip code": bit_flip_code, "phase-flip code": phase_flip_code}
P = 0.1
SHOTS = 4000


def survivors(code, errors) -> list[str]:
    return [s for s in INPUT_STATES if logical_error_rate(code(s, errors), s, shots=1, seed=SEED) == 0]


def syndrome(code, errors) -> str:
    result = AerSimulator(method="stabilizer").run(code("0", errors), shots=1, seed_simulator=SEED, memory=True).result()
    return result.get_memory()[0].split()[1]


def odd_flips(p: float) -> float:
    """An uncorrectable error type flips the logical qubit when an odd number of the 3 qubits are hit."""
    return (1 - (1 - 2 * p) ** 3) / 2


def main() -> dict:
    heading("Step 1: the phase-flip code corrects every single Z error")
    single = {}
    for qubit in range(3):
        kept = survivors(phase_flip_code, [(qubit, "z")])
        single[qubit] = {"syndrome": syndrome(phase_flip_code, [(qubit, "z")]), "survivors": kept}
        print(f"Z on data qubit {qubit}: syndrome {single[qubit]['syndrome']} -> intact inputs {kept}")
    print("Same syndromes as the bit-flip code: after H, a Z looks exactly like an X.")

    heading("Step 2: each code against each single error type (which of the 6 inputs survive?)")
    table = {}
    for name, code in CODES.items():
        for pauli in "xzy":
            kept = [survivors(code, [(q, pauli)]) for q in range(3)]
            same = all(k == kept[0] for k in kept)
            table[(name, pauli)] = kept[0] if same else kept
            label = "all 6" if kept[0] == list(INPUT_STATES) else f"only {kept[0]}"
            print(f"{name:<15} + single {pauli.upper()}: {label}{'' if same else ' (differs by qubit)'}")
    print("Each code's blind spot becomes a LOGICAL Z: basis states |0>, |1> survive, every")
    print("superposition flips. Y = X and Z at once; the code fixes one half and not the other.")

    heading(f"Step 3: random errors, p = {P} per qubit ({SHOTS} seeded shots)")
    rates = {}
    for c, (name, code) in enumerate(CODES.items()):
        for k, (pauli, state) in enumerate((("x", "0"), ("x", "+"), ("z", "0"), ("z", "+"))):
            rate = logical_error_rate(code(state), state, shots=SHOTS, seed=run_seed(1 + 4 * c + k), noise=pauli_channel_noise(P, pauli))
            rates[(name, pauli, state)] = rate
    for name in CODES:
        print(f"{name:<15}: X noise -> |0> {rates[(name, 'x', '0')]:.4f}, |+> {rates[(name, 'x', '+')]:.4f};   "
              f"Z noise -> |0> {rates[(name, 'z', '0')]:.4f}, |+> {rates[(name, 'z', '+')]:.4f}")
    print(f"formulas: designed-for error 3p^2 - 2p^3 = {3 * P**2 - 2 * P**3:.4f};  blind spot (odd number hit) = "
          f"{odd_flips(P):.4f};  unprotected = {P:.4f}")
    print("The blind spot is WORSE than no code: three qubits offer three targets instead of one.")
    return {"single": single, "table": table, "rates": rates, "odd_formula": odd_flips(P), "designed_formula": 3 * P**2 - 2 * P**3}


if __name__ == "__main__":
    main()
