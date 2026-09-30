"""Noise and quantum error correction on toy codes (shared by lessons 21-25).

Conventions: Qiskit qubit order; data qubits first, then syndrome ancillas. Noise that plays the
role of "the channel" is attached to `id` gates, so it hits exactly where the circuit places them.
"""

from __future__ import annotations

from math import comb

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error, pauli_error

from _common import SEED

BASIS = ["u", "cx"]
SEED_STRIDE = 10**7


def run_seed(index: int) -> int:
    """Seed for the index-th independent Aer run.

    Measured in this lab (Aer 0.17.2): with noise or mid-circuit measurement, Aer seeds shot i of a
    run as seed_simulator + i. Two runs whose seeds differ by less than their shot count therefore
    reuse the same random numbers (shot i of seed s = shot i - 1 of seed s + 1). Runs meant to be
    independent get seeds SEED_STRIDE apart, far more than any shot count used here.
    """
    return SEED + index * SEED_STRIDE


def per_gate_noise(p: float, *, qubits_1q: set[int] | None = None, pairs_2q: set[tuple[int, int]] | None = None) -> NoiseModel:
    """Depolarizing error of strength p after EVERY u and cx gate (the circuit must be transpiled
    to BASIS first). Optionally restrict it to some qubits / qubit pairs.

    The lab's local_noise_model (qiskit_experiments.py) only adds noise to h and cx; after
    transpiling, most gates are u gates, so lesson 21 needs this per-gate version.
    """
    model = NoiseModel(basis_gates=BASIS)
    if p == 0:
        return model
    one, two = depolarizing_error(p, 1), depolarizing_error(p, 2)
    if qubits_1q is None and pairs_2q is None:
        model.add_all_qubit_quantum_error(one, ["u"])
        model.add_all_qubit_quantum_error(two, ["cx"])
        return model
    for q in qubits_1q or ():
        model.add_quantum_error(one, ["u"], [q])
    for a, b in pairs_2q or ():
        model.add_quantum_error(two, ["cx"], [a, b])
    return model


def to_basis(circuit: QuantumCircuit, seed: int) -> QuantumCircuit:
    return transpile(circuit, basis_gates=BASIS, optimization_level=1, seed_transpiler=seed)


def gate_count(circuit: QuantumCircuit) -> int:
    ops = circuit.count_ops()
    return int(ops.get("u", 0) + ops.get("cx", 0))


# ------------------------------------------------------------------ toy codes
#
# Logical states are prepared on data qubit 0 and read back from it after decoding. The six
# Pauli eigenstates below are enough to detect ANY logical Pauli error: X flips the Z-basis
# states, Z flips the X-basis states, Y flips both, and all of them are stabilizer states, so
# Aer's fast stabilizer method can run every circuit here.

INPUT_STATES = ("0", "1", "+", "-", "+i", "-i")
EXPECTED_BIT = {"0": 0, "1": 1, "+": 0, "-": 1, "+i": 0, "-i": 1}


def prepare(circuit: QuantumCircuit, qubit, state: str) -> None:
    if state in ("1", "-"):
        circuit.x(qubit)
    if state in ("+", "-", "+i", "-i"):
        circuit.h(qubit)
    if state == "+i":
        circuit.s(qubit)
    if state == "-i":
        circuit.sdg(qubit)


def measure_in_basis(circuit: QuantumCircuit, qubit, state: str, clbit) -> None:
    """Rotate the basis of `state` onto Z, then measure: the result is EXPECTED_BIT[state] if the
    qubit is still in that state."""
    if state in ("+i", "-i"):
        circuit.sdg(qubit)
    if state in ("+", "-", "+i", "-i"):
        circuit.h(qubit)
    circuit.measure(qubit, clbit)


def inject(circuit: QuantumCircuit, errors: list[tuple[int, str]]) -> None:
    """Apply chosen Pauli errors, e.g. [(1, "x"), (4, "z")]."""
    for qubit, pauli in errors:
        getattr(circuit, pauli)(qubit)


def channel(circuit: QuantumCircuit, qubits) -> None:
    """Mark the moment the noisy channel acts: an id gate on each data qubit (noise models attach
    errors to 'id', so the rest of the circuit stays perfect)."""
    for qubit in qubits:
        circuit.id(qubit)


def bit_flip_round(circuit: QuantumCircuit, data: list, ancillas: list, syndrome: ClassicalRegister) -> None:
    """Measure Z_a Z_b and Z_b Z_c onto two ancillas, then flip the qubit the syndrome points to.
    syndrome bit 0 = parity(a, b), bit 1 = parity(b, c): 01 -> a, 11 -> b, 10 -> c."""
    a, b, c = data
    circuit.cx(a, ancillas[0])
    circuit.cx(b, ancillas[0])
    circuit.cx(b, ancillas[1])
    circuit.cx(c, ancillas[1])
    circuit.measure(ancillas[0], syndrome[0])
    circuit.measure(ancillas[1], syndrome[1])
    for value, target in ((0b01, a), (0b11, b), (0b10, c)):
        with circuit.if_test((syndrome, value)):
            circuit.x(target)


def bit_flip_code(state: str, errors: list[tuple[int, str]] = (), *, correct: bool = True) -> QuantumCircuit:
    """3-qubit bit-flip code: encode |psi> as a|000> + b|111>, channel, syndrome + correction, decode."""
    data, anc = QuantumRegister(3, "data"), QuantumRegister(2, "anc")
    syndrome, out = ClassicalRegister(2, "syndrome"), ClassicalRegister(1, "out")
    circuit = QuantumCircuit(data, anc, syndrome, out)
    prepare(circuit, data[0], state)
    circuit.cx(data[0], data[1])
    circuit.cx(data[0], data[2])
    channel(circuit, data)
    inject(circuit, list(errors))
    if correct:
        bit_flip_round(circuit, list(data), list(anc), syndrome)
    circuit.cx(data[0], data[2])
    circuit.cx(data[0], data[1])
    measure_in_basis(circuit, data[0], state, out[0])
    return circuit


def phase_flip_code(state: str, errors: list[tuple[int, str]] = (), *, correct: bool = True) -> QuantumCircuit:
    """3-qubit phase-flip code: the bit-flip code in the Hadamard basis (a|+++> + b|--->).
    Z errors look like X errors after H, so the syndrome round is the bit-flip round between H layers."""
    data, anc = QuantumRegister(3, "data"), QuantumRegister(2, "anc")
    syndrome, out = ClassicalRegister(2, "syndrome"), ClassicalRegister(1, "out")
    circuit = QuantumCircuit(data, anc, syndrome, out)
    prepare(circuit, data[0], state)
    circuit.cx(data[0], data[1])
    circuit.cx(data[0], data[2])
    circuit.h(data)
    channel(circuit, data)
    inject(circuit, list(errors))
    if correct:
        circuit.h(data)
        bit_flip_round(circuit, list(data), list(anc), syndrome)
        circuit.h(data)
    circuit.h(data)
    circuit.cx(data[0], data[2])
    circuit.cx(data[0], data[1])
    measure_in_basis(circuit, data[0], state, out[0])
    return circuit


def shor9_code(state: str, errors: list[tuple[int, str]] = (), *, correct: bool = True,
               ry_angle: float | None = None, save_state: bool = False) -> QuantumCircuit:
    """Shor's 9-qubit code: a phase-flip code whose three qubits are each a bit-flip block.
    Corrections: a bit-flip round inside each block (6 ancillas), then the X-parities of blocks
    1+2 and 2+3 (2 ancillas) locate a phase-flipped block, fixed by one Z on that block.
    With ry_angle, the input is RY(angle)|0> instead (not a stabilizer state: use the
    statevector method) and the output is measured in Z. With save_state, the final state vector
    is saved instead of measuring the output (for exact checks when the syndromes are deterministic)."""
    data, anc = QuantumRegister(9, "data"), QuantumRegister(8, "anc")
    block_syndromes = [ClassicalRegister(2, f"block{b}") for b in range(3)]
    phase, out = ClassicalRegister(2, "phase"), ClassicalRegister(1, "out")
    circuit = QuantumCircuit(data, anc, *block_syndromes, phase, out)
    blocks = [[data[3 * b], data[3 * b + 1], data[3 * b + 2]] for b in range(3)]
    if ry_angle is None:
        prepare(circuit, data[0], state)
    else:
        circuit.ry(ry_angle, data[0])
    circuit.cx(data[0], data[3])
    circuit.cx(data[0], data[6])
    circuit.h([data[0], data[3], data[6]])
    for block in blocks:
        circuit.cx(block[0], block[1])
        circuit.cx(block[0], block[2])
    channel(circuit, data)
    inject(circuit, list(errors))
    if correct:
        for b, block in enumerate(blocks):
            bit_flip_round(circuit, block, [anc[2 * b], anc[2 * b + 1]], block_syndromes[b])
        for bit, (first, second) in enumerate(((0, 1), (1, 2))):
            ancilla = anc[6 + bit]
            circuit.h(ancilla)
            for qubit in blocks[first] + blocks[second]:
                circuit.cx(ancilla, qubit)  # measures X on all six qubits of the two blocks
            circuit.h(ancilla)
            circuit.measure(ancilla, phase[bit])
        for value, block in ((0b01, 0), (0b11, 1), (0b10, 2)):
            with circuit.if_test((phase, value)):
                circuit.z(blocks[block][0])
    for block in blocks:
        circuit.cx(block[0], block[2])
        circuit.cx(block[0], block[1])
    circuit.h([data[0], data[3], data[6]])
    circuit.cx(data[0], data[6])
    circuit.cx(data[0], data[3])
    if save_state:
        circuit.save_statevector()
    else:
        measure_in_basis(circuit, data[0], "0" if ry_angle is not None else state, out[0])
    return circuit


def logical_error_rate(circuit: QuantumCircuit, state: str, *, shots: int, seed: int, noise: NoiseModel | None = None) -> float:
    """Fraction of shots whose decoded qubit is NOT back in `state` (stabilizer simulation)."""
    simulator = AerSimulator(method="stabilizer", noise_model=noise)
    memory = simulator.run(circuit, shots=shots, seed_simulator=seed, memory=True).result().get_memory()
    return sum(int(bits.split()[0]) != EXPECTED_BIT[state] for bits in memory) / shots


def pauli_channel_noise(p: float, pauli: str) -> NoiseModel:
    """Each data qubit suffers `pauli` with probability p at the channel (the id gates)."""
    model = NoiseModel()
    if p > 0:
        model.add_all_qubit_quantum_error(pauli_error([(pauli.upper(), p), ("I", 1 - p)]), ["id"])
    return model


def depolarizing_channel_noise(p: float) -> NoiseModel:
    """Each data qubit suffers X, Y or Z, each with probability p/3, at the channel."""
    model = NoiseModel()
    if p > 0:
        model.add_all_qubit_quantum_error(pauli_error([("X", p / 3), ("Y", p / 3), ("Z", p / 3), ("I", 1 - p)]), ["id"])
    return model


def repetition_logical_error(d: int, p: float) -> float:
    """Exact: majority vote over d copies fails when more than d/2 of them flip."""
    return sum(comb(d, k) * p**k * (1 - p) ** (d - k) for k in range(d // 2 + 1, d + 1))
