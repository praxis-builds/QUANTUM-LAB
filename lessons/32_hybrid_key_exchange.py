"""Lesson 32: hybrid key exchange, X25519 + ML-KEM-768 combined through HKDF.

EDUCATIONAL, NOT PRODUCTION: no authentication, no TLS key schedule, no protection against
misuse. It shows the idea browsers deploy (Chrome: X25519MLKEM768), nothing more.
"""

from __future__ import annotations

import hashlib
import os

from _common import heading
from _pqc import load_oqs, missing_reason

KEM = "ML-KEM-768"
CONTEXT = b"praxis-quantum-lab lesson 32 hybrid demo (educational, not production)"


def combine(ml_kem_secret: bytes, x25519_secret: bytes, transcript: bytes) -> bytes:
    """HKDF-SHA256 over both secrets, bound to everything that was sent (the transcript)."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF

    info = CONTEXT + b"|" + hashlib.sha256(transcript).digest()
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=info).derive(ml_kem_secret + x25519_secret)


def handshake(oqs) -> dict:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import x25519

    raw = serialization.Encoding.Raw, serialization.PublicFormat.Raw
    # Client: one X25519 key share and one ML-KEM public key, sent together.
    client_x = x25519.X25519PrivateKey.generate()
    client_kem = oqs.KeyEncapsulation(KEM)
    client_kem_public = client_kem.generate_keypair()
    client_hello = client_x.public_key().public_bytes(*raw) + client_kem_public
    # Server: its own X25519 share, and an ML-KEM encapsulation to the client's key.
    server_x = x25519.X25519PrivateKey.generate()
    with oqs.KeyEncapsulation(KEM) as server_kem:
        ciphertext, server_kem_secret = server_kem.encap_secret(client_kem_public)
    server_x_secret = server_x.exchange(client_x.public_key())
    server_hello = server_x.public_key().public_bytes(*raw) + ciphertext
    transcript = client_hello + server_hello
    server_key = combine(server_kem_secret, server_x_secret, transcript)
    # Client: the same two secrets from its side.
    client_x_secret = client_x.exchange(server_x.public_key())
    client_kem_secret = client_kem.decap_secret(ciphertext)
    client_key = combine(client_kem_secret, client_x_secret, transcript)
    client_kem.free()
    return {"client_hello": len(client_hello), "server_hello": len(server_hello), "transcript": transcript,
            "client_key": client_key, "server_key": server_key,
            "x25519_secret": server_x_secret, "ml_kem_secret": server_kem_secret}


def main() -> dict:
    reason = missing_reason()
    if reason:
        print(f"Skipping lesson 32: {reason}")
        return {"skipped": reason}
    oqs = load_oqs()

    heading("Step 1: one handshake, two key exchanges, one key")
    run = handshake(oqs)
    print(f"client -> server: X25519 share (32 B) + ML-KEM-768 public key (1184 B) = {run['client_hello']} bytes")
    print(f"server -> client: X25519 share (32 B) + ML-KEM-768 ciphertext (1088 B) = {run['server_hello']} bytes")
    print(f"both derive the same 32-byte key: {run['client_key'] == run['server_key']}   ({run['client_key'].hex()[:24]}...)")

    heading("Step 2: an attacker who breaks only ONE of the two")
    t = run["transcript"]
    guesses = {
        "knows X25519 secret (e.g. via Shor), guesses ML-KEM": combine(os.urandom(32), run["x25519_secret"], t),
        "knows ML-KEM secret (hypothetical lattice break), guesses X25519": combine(run["ml_kem_secret"], os.urandom(32), t),
        "knows both": combine(run["ml_kem_secret"], run["x25519_secret"], t),
    }
    attacker = {}
    for label, key in guesses.items():
        attacker[label] = key == run["server_key"]
        print(f"{label:<66}: gets the session key? {attacker[label]}")
    print("HKDF mixes both secrets: the key stays secret as long as EITHER exchange holds.")
    print("X25519 covers a surprise break of the young ML-KEM; ML-KEM covers the future quantum attack on X25519.")
    print("EDUCATIONAL ONLY: no authentication (anyone can sit in the middle), no TLS key schedule.")
    return {"client_hello": run["client_hello"], "server_hello": run["server_hello"],
            "keys_match": run["client_key"] == run["server_key"], "attacker": attacker}


if __name__ == "__main__":
    main()
