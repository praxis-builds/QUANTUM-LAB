"""Planted legacy crypto for pq_inventory tests (never executed)."""
import hashlib

from Crypto.Cipher import DES3
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# TODO: drop md5 everywhere (a comment, not a use: must NOT be reported)
rsa_value = 3  # a variable name, not RSA


def make_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def checksum(data):
    return hashlib.md5(data).hexdigest()


def modern_checksum(data):
    return hashlib.sha256(data).hexdigest()


def legacy_encrypt(key, data):
    return DES3.new(key, DES3.MODE_CBC).encrypt(data)


def session_key():
    return AESGCM.generate_key(bit_length=128)
