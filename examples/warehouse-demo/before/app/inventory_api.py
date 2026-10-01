"""Inventory API for the fictional Northwind Warehouse (demo code, never run)."""
import hashlib

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

TOKEN_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
STORAGE_KEY = AESGCM.generate_key(bit_length=128)


def sign_order_token(payload: bytes) -> bytes:
    return TOKEN_KEY.sign(payload, padding.PKCS1v15(), hashes.SHA256())


def etag(body: bytes) -> str:
    return hashlib.md5(body).hexdigest()


def barcode_checksum(sku: str) -> str:
    return hashlib.sha1(sku.encode()).hexdigest()[:8]


def encrypt_stock_snapshot(data: bytes, nonce: bytes) -> bytes:
    return AESGCM(STORAGE_KEY).encrypt(nonce, data, None)
