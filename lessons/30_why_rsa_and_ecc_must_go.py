"""Lesson 30: why RSA and elliptic-curve crypto must be replaced (ties lessons 16 and 25 together)."""

from __future__ import annotations

import math

import numpy as np

from _common import SEED, heading
from _shor import factor_with_shor, sample_runs

# Lesson 16's toy key: N = 21, e = 5, message "HIDE" with A = 0 ... T = 19.
N, E = 21, 5
CIPHER = [7, 8, 12, 16]
ALPHABET = "ABCDEFGHIJKLMNOPQRST"

# Mosca's inequality x + y > z (Mosca, IEEE Security & Privacy 16(5), 2018). Example systems; every
# number here is an ASSUMPTION for illustration, not a forecast.
SYSTEMS = {
    "web session keys": {"x": 0.1, "y": 3},
    "customer records": {"x": 10, "y": 5},
    "health / legal archives": {"x": 30, "y": 7},
    "firmware signing root key": {"x": 15, "y": 8},
}
Z_SCENARIOS = (10, 15, 20)  # years until a cryptographically relevant quantum computer: unknown, so several


def ecc_logical_qubits(n_bits: int) -> int:
    """Upper bound 9n + 2 ceil(log2 n) + 10 logical qubits for an n-bit prime-field curve
    (Roetteler, Naehrig, Svore, Lauter, ASIACRYPT 2017)."""
    return 9 * n_bits + 2 * math.ceil(math.log2(n_bits)) + 10


def main() -> dict:
    heading("Step 1: Lesson 16 again: Shor turns a public key into a private key")
    runs_for = {a: sample_runs(a, N, 64, SEED + 300 + a) for a in range(2, N) if math.gcd(a, N) == 1}
    attempt = factor_with_shor(N, np.random.default_rng(SEED + 30), runs_for)
    p, q = attempt["factors"]
    d = pow(E, -1, (p - 1) * (q - 1))
    plain = "".join(ALPHABET[pow(c, d, N)] for c in CIPHER)
    print(f"public key (N, e) = ({N}, {E}) -> factors {p} x {q} -> d = {d} -> ciphertext {CIPHER} decrypts to {plain!r}")
    print("Nothing about this depends on N being small except the size of the quantum computer.")

    heading("Step 2: what breaking real keys needs (published estimates, not simulations)")
    curves = {f"P-{n}": ecc_logical_qubits(n) for n in (256, 384, 521)}
    print("RSA-2048: under a million noisy physical qubits for under a week (Gidney 2025, Lesson 16),")
    print("  assuming 0.1% gate errors; most of those qubits are error-correction overhead (Lesson 25).")
    for curve, qubits in curves.items():
        print(f"ECC {curve}: at most {qubits} LOGICAL qubits (9n + 2 ceil(log2 n) + 10, Roetteler et al. 2017)")
    print("A few thousand logical qubits for P-256: elliptic curves are no safe harbour from Shor.")

    heading("Step 3: harvest now, decrypt later (Mosca: at risk if x + y > z)")
    verdicts = {}
    for name, system in SYSTEMS.items():
        verdicts[name] = {z: system["x"] + system["y"] > z for z in Z_SCENARIOS}
        row = "  ".join(f"z={z}: {'AT RISK' if risk else 'ok'}" for z, risk in verdicts[name].items())
        print(f"{name:<26} x = {system['x']:>4} years secret, y = {system['y']} years to migrate -> {row}")
    print("x = how long the data must stay secret, y = how long migrating takes, z = years until a")
    print("cryptographically relevant quantum computer. All example numbers are assumptions; z is unknown.")
    print("Recorded ciphertext can be decrypted later, so long-lived data is at risk TODAY.")

    heading("Step 4: the replacements NIST standardised (FIPS 203, 204, 205; 13 August 2024)")
    replacements = {
        "RSA / ECDH / DH key exchange": "ML-KEM (FIPS 203), module lattices",
        "RSA / ECDSA / EdDSA signatures": "ML-DSA (FIPS 204), module lattices",
        "conservative signatures (roots, firmware)": "SLH-DSA (FIPS 205), hash-based, larger and slower",
        "AES-128 (Grover only weakens)": "AES-256 where margin matters (Lesson 20)",
    }
    for old, new in replacements.items():
        print(f"{old:<44} -> {new}")
    print("NIST IR 8547 (initial public draft, Nov 2024) proposes deprecating 112-bit RSA/ECC after 2030")
    print("and disallowing quantum-vulnerable public-key algorithms after 2035 (draft; see the lesson page).")
    return {"plain": plain, "factors": (p, q), "d": d, "curves": curves, "verdicts": verdicts, "replacements": replacements}


if __name__ == "__main__":
    main()
