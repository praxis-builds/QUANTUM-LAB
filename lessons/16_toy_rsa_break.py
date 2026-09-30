"""Lesson 16: finale. Break a toy RSA key with Shor's algorithm (lesson 15's pipeline)."""

from __future__ import annotations

import math

import numpy as np

from _common import SEED, heading
from _shor import factor_with_shor, factors_from_order, period_from_measurement, sample_runs, trial_division

P, Q = 3, 7
E = 5
MESSAGE = "HIDE"
ALPHABET = "ABCDEFGHIJKLMNOPQRST"  # A = 0 ... T = 19: every symbol is a number below N = 21
ATTACK_SHOTS = 64  # quantum runs sampled per a (the attack uses only a few of them)
QUANTUM_A = 2  # a unit mod 21 with r = 6: forces the quantum path (no lucky gcd)


def make_key(p: int, q: int, e: int) -> dict:
    """Textbook RSA: N = pq, phi = (p-1)(q-1), e coprime to phi, d = e^-1 mod phi."""
    n, phi = p * q, (p - 1) * (q - 1)
    if math.gcd(e, phi) != 1:
        raise ValueError("e must share no factor with phi.")
    return {"N": n, "e": e, "d": pow(e, -1, phi), "phi": phi}


def encrypt(numbers: list[int], e: int, n: int) -> list[int]:
    return [pow(m, e, n) for m in numbers]


def decrypt(numbers: list[int], d: int, n: int) -> list[int]:
    return [pow(c, d, n) for c in numbers]


def encode(text: str) -> list[int]:
    return [ALPHABET.index(ch) for ch in text]


def decode(numbers: list[int]) -> str:
    return "".join(ALPHABET[x] for x in numbers)


def fixed_points(e: int, n: int) -> list[int]:
    return [m for m in range(n) if pow(m, e, n) == m]


def main() -> dict:
    heading("Step 1: the defender makes a toy RSA key")
    key = make_key(P, Q, E)
    print(f"p = {P}, q = {Q} (secret);  N = {key['N']}, phi = {key['phi']}")
    print(f"public key (N, e) = ({key['N']}, {key['e']});  private d = e^-1 mod phi = {key['d']}  (5 x 5 = 25 = 2 x 12 + 1)")
    valid_e = [e for e in range(2, key["phi"]) if math.gcd(e, key["phi"]) == 1]
    print(f"valid e below phi: {valid_e}, with d = {[pow(e, -1, key['phi']) for e in valid_e]} (each its own inverse at this size)")
    identity_e = [e for e in valid_e if len(fixed_points(e, key["N"])) == key["N"]]
    print(f"e = {identity_e} would encrypt NOTHING: m^e = m for every m (they are 1 mod lcm(p-1, q-1) = 6)")

    heading("Step 2: encrypt a message, one symbol at a time")
    plain = encode(MESSAGE)
    cipher = encrypt(plain, key["e"], key["N"])
    print(f"message {MESSAGE!r} -> numbers {plain} -> ciphertext {cipher}")
    fixed = fixed_points(key["e"], key["N"])
    print(f"{len(fixed)} of {key['N']} values encrypt to themselves: {fixed}  (H = 7 and I = 8 among them)")
    round_trip = all(decrypt(encrypt([m], key["e"], key["N"]), key["d"], key["N"]) == [m] for m in range(key["N"]))
    print(f"decrypt(encrypt(m)) = m for all m < {key['N']}: {round_trip}")

    heading("Step 3: the attacker sees only (N, e) and the ciphertext; runs Shor to factor N")
    n = key["N"]
    t = 2 * n.bit_length()
    runs_for = {a: sample_runs(a, n, ATTACK_SHOTS, SEED + 100 + a) for a in range(2, n) if math.gcd(a, n) == 1}
    print(f"Quantum period finding with a = {QUANTUM_A} (lesson 15's circuit, {t} counting qubits), one run at a time:")
    quantum_path = []
    for m in runs_for[QUANTUM_A]:
        candidate = period_from_measurement(m, t, n)
        passes = pow(QUANTUM_A, candidate, n) == 1
        factors, reason = factors_from_order(QUANTUM_A, n, candidate) if passes else (None, "fails a^c = 1")
        quantum_path.append({"m": m, "candidate": candidate, "factors": factors})
        print(f"  run {len(quantum_path)}: m = {m:>4} -> candidate r = {candidate}: "
              f"{f'factors {factors[0]} x {factors[1]}' if factors else reason}")
        if factors:
            break
    p, q = quantum_path[-1]["factors"]
    phi = (p - 1) * (q - 1)
    d = pow(key["e"], -1, phi)
    recovered = decode(decrypt(cipher, d, n))
    print(f"phi = ({p}-1)({q}-1) = {phi};  d = {key['e']}^-1 mod {phi} = {d};  decrypted: {recovered!r}")
    attempt = factor_with_shor(n, np.random.default_rng(SEED + 16), runs_for)
    print(f"(The full algorithm with a random a, same seed family: a = {attempt['a']} after {attempt['picks']} pick(s) and "
          f"{attempt['quantum_runs']} quantum run(s) -> {attempt['factors'][0]} x {attempt['factors'][1]}"
          f"{'; a lucky gcd did the work' if math.gcd(attempt['a'], n) > 1 else ''}.)")

    heading("Step 4: the classical baseline")
    small, large, tried = trial_division(n)
    print(f"trial division: {n} = {small} x {large} after {tried} division(s). Instant, no quantum computer.")
    print("The point is scaling: for a 2048-bit N, trial division and every known classical method are")
    print("hopeless, while Shor's cost grows only polynomially in the number of bits. See the lesson page")
    print("for published resource estimates and why RSA is being replaced.")
    return {"key": key, "plain": plain, "cipher": cipher, "fixed_points": fixed, "identity_e": identity_e,
            "round_trip": round_trip, "quantum_path": quantum_path, "attack": attempt, "recovered_d": d, "recovered": recovered,
            "trial_division": (small, large, tried)}


if __name__ == "__main__":
    main()
