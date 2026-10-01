"""A clean file: only modern primitives (no quantum-vulnerable or weak findings expected)."""
import hashlib

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def digest(data):
    return hashlib.sha256(data).hexdigest()


def new_key():
    return AESGCM.generate_key(bit_length=256)


KEM_NAME = "ML-KEM-768"  # post-quantum key establishment (an OK finding)
