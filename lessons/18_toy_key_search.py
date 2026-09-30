"""Lesson 18: toy key search. Grover finds a 4-bit key from known plaintext/ciphertext pairs."""

from __future__ import annotations

import math

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from _common import SEED, heading
from _grover_n import flip_if_equal, grover_circuit, optimal_iterations, success_probability
from praxis_quantum_lab.qiskit_experiments import ideal_counts

# PRESENT's 4-bit S-box (Bogdanov et al., 2007): a public, fixed, nonlinear permutation.
SBOX = (0xC, 0x5, 0x6, 0xB, 0x9, 0x0, 0xA, 0xD, 0x3, 0xE, 0xF, 0x8, 0x4, 0x7, 0x1, 0x2)
KEY_BITS = 4
SECRET_KEY = 0b1011
SHOTS = 2000
CLASSICAL_TRIALS = 20_000


def encrypt(key: int, plaintext: int) -> int:
    """Toy cipher: Enc_k(P) = S(P XOR k) XOR k (key added before and after the S-box)."""
    return SBOX[plaintext ^ key] ^ key


def matching_keys(pairs: list[tuple[int, int]]) -> list[int]:
    return [k for k in range(2**KEY_BITS) if all(encrypt(k, p) == c for p, c in pairs)]


def choose_pairs() -> list[tuple[int, int]]:
    """First plaintext whose pair leaves 2 candidate keys, then a second one that leaves only the secret."""
    first = next(p for p in range(16) if len(matching_keys([(p, encrypt(SECRET_KEY, p))])) == 2)
    second = next(p for p in range(16) if p != first and
                  matching_keys([(first, encrypt(SECRET_KEY, first)), (p, encrypt(SECRET_KEY, p))]) == [SECRET_KEY])
    return [(first, encrypt(SECRET_KEY, first)), (second, encrypt(SECRET_KEY, second))]


def compute_cipher(circuit: QuantumCircuit, plaintext: int, out: list[int]) -> None:
    """out XOR= Enc_k(plaintext), with the key k on qubits 0..3, using only public parts of the cipher.

    1. X gates turn k into k XOR P (in place).
    2. The S-box: for every input value x and every 1-bit of S(x), a multi-controlled X that fires
       when the register holds x. This is the S-box's public table, not a table of keys.
    3. X gates undo step 1, then CNOTs add k to the output (the second key addition).
    Every step XORs into `out` or is undone, so running this twice restores `out`: it is its own inverse.
    """
    key = list(range(KEY_BITS))
    flips = [q for q in key if (plaintext >> q) & 1]
    if flips:
        circuit.x(flips)
    for x, s in enumerate(SBOX):
        targets = [out[b] for b in range(KEY_BITS) if (s >> b) & 1]
        if not targets:
            continue
        zeros = [q for q in key if not (x >> q) & 1]
        if zeros:
            circuit.x(zeros)
        for target in targets:
            circuit.mcx(key, target)
        if zeros:
            circuit.x(zeros)
    if flips:
        circuit.x(flips)
    for q in key:
        circuit.cx(q, out[q])


def key_oracle(pairs: list[tuple[int, int]]):
    """Compute Enc_k(P_i) for each pair, flip the sign if every output equals its C_i, uncompute."""
    outs = [list(range(KEY_BITS + 4 * i, KEY_BITS + 4 * (i + 1))) for i in range(len(pairs))]
    target = sum(c << (4 * i) for i, (_, c) in enumerate(pairs))

    def oracle(circuit: QuantumCircuit) -> None:
        for (p, _), out in zip(pairs, outs):
            compute_cipher(circuit, p, out)
        flip_if_equal(circuit, [q for out in outs for q in out], target)
        for (p, _), out in zip(pairs, outs):
            compute_cipher(circuit, p, out)
    return oracle, 4 * len(pairs)


def oracle_truth_table(pairs: list[tuple[int, int]]) -> dict[int, int]:
    """Run the oracle on every key |k>|0...0> (16 exact Aer state-vector runs): the result must be
    +1 or -1 times the same state, i.e. a sign in front and the work qubits back at 0."""
    oracle, extra = key_oracle(pairs)
    width = KEY_BITS + extra
    simulator = AerSimulator(method="statevector")
    body = QuantumCircuit(width)
    oracle(body)
    body = transpile(body, simulator, seed_transpiler=SEED)  # synthesise once, reuse for all 16 inputs
    circuits = []
    for k in range(2**KEY_BITS):
        circuit = QuantumCircuit(width)
        ones = [q for q in range(KEY_BITS) if (k >> q) & 1]
        if ones:
            circuit.x(ones)
        circuit.compose(body, inplace=True)
        circuit.save_statevector()
        circuits.append(circuit)
    result = simulator.run(circuits).result()
    table = {}
    for k in range(2**KEY_BITS):
        amplitude = np.asarray(result.get_statevector(k))[k]
        assert abs(abs(amplitude) - 1) < 1e-9, "the oracle must not leave garbage in the work qubits"
        table[k] = int(round(amplitude.real))
    return table


def classical_trials(pairs: list[tuple[int, int]], rng: np.random.Generator) -> float:
    """Try keys in random order; accept the first key that matches ALL the given pairs."""
    total = 0
    for _ in range(CLASSICAL_TRIALS):
        for tried, k in enumerate(rng.permutation(2**KEY_BITS), start=1):
            if all(encrypt(int(k), p) == c for p, c in pairs):
                total += tried
                break
    return total / CLASSICAL_TRIALS


def run_grover(pairs: list[tuple[int, int]], seed: int) -> dict:
    oracle, extra = key_oracle(pairs)
    M = len(matching_keys(pairs))
    k = optimal_iterations(2**KEY_BITS, M)
    circuit = grover_circuit(KEY_BITS, oracle, k, extra_qubits=extra, measure=True)
    counts = ideal_counts(circuit, shots=SHOTS, seed=seed)
    ops = circuit.count_ops()
    return {"M": M, "iterations": k, "qubits": circuit.num_qubits, "theory": success_probability(k, 2**KEY_BITS, M),
            "counts": dict(sorted(counts.items(), key=lambda item: -item[1])),
            "p_secret": counts.get(format(SECRET_KEY, "04b"), 0) / SHOTS,
            "p_any_match": sum(v for key, v in counts.items() if int(key, 2) in matching_keys(pairs)) / SHOTS,
            "mcx_gates": int(ops.get("mcx", 0))}


def main() -> dict:
    heading("Step 1: the toy cipher Enc_k(P) = S(P XOR k) XOR k, and two known pairs")
    pairs = choose_pairs()
    print(f"secret key = {SECRET_KEY:04b} (the attacker does not know it)")
    for p, c in pairs:
        print(f"known pair: P = {p:04b} -> C = {c:04b};  keys consistent with this pair alone: "
              f"{[format(k, '04b') for k in matching_keys([(p, c)])]}")
    print(f"keys consistent with both pairs: {[format(k, '04b') for k in matching_keys(pairs)]}")
    counts_per_pair = sorted({len(matching_keys([(p, encrypt(SECRET_KEY, p))])) for p in range(16)})
    print(f"(over all 16 plaintexts, one pair leaves {counts_per_pair} candidate keys)")

    heading("Step 2: the reversible oracle marks exactly the matching keys (full truth table)")
    tables = {}
    for label, used in (("pair 1", pairs[:1]), ("pairs 1+2", pairs)):
        tables[label] = oracle_truth_table(used)
        marked = [format(k, "04b") for k, sign in tables[label].items() if sign == -1]
        print(f"{label}: sign -1 on keys {marked};  +1 on the other {16 - len(marked)};  work qubits back to 0")

    heading(f"Step 3: Grover with ONE known pair ({SHOTS} seeded shots)")
    one = run_grover(pairs[:1], SEED)
    print(f"M = {one['M']} matching keys, {one['iterations']} iterations, {one['qubits']} qubits: counts {one['counts']}")
    print(f"P(a matching key) = {one['p_any_match']:.3f} (theory {one['theory']:.3f}); P(the secret key) = {one['p_secret']:.3f}")
    print("Half of the successes are the false positive: it fits pair 1 but is not the key.")

    heading(f"Step 4: Grover with TWO known pairs ({SHOTS} seeded shots)")
    two = run_grover(pairs, SEED)
    print(f"M = {two['M']}, {two['iterations']} iterations, {two['qubits']} qubits: top counts "
          f"{dict(list(two['counts'].items())[:3])}")
    print(f"P(the secret key) = {two['p_secret']:.3f} (theory {two['theory']:.3f})")

    heading("Step 5: oracle calls against classical brute force")
    rng = np.random.default_rng(SEED)
    classical = classical_trials(pairs, rng)
    quantum = (two["iterations"] + 1) / two["p_secret"]  # iterations + 1 classical check, repeated until right
    print(f"classical: try keys in random order until one fits both pairs: mean {classical:.2f} trials "
          f"(theory (16 + 1) / 2 = 8.5)")
    print(f"quantum:   {two['iterations']} oracle calls + 1 check per attempt, success {two['p_secret']:.3f}: "
          f"expected {quantum:.2f} calls")
    print(f"But each quantum oracle call runs the cipher {2 * len(pairs)} times (compute + uncompute, per pair):")
    print(f"{two['mcx_gates']} multi-controlled gates in the full circuit, for a 4-bit toy.")
    return {"pairs": pairs, "tables": tables, "one_pair": one, "two_pairs": two,
            "classical_mean": classical, "quantum_expected": quantum}


if __name__ == "__main__":
    main()
