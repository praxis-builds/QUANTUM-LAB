"""Inventory API for the fictional Northwind Warehouse (demo code, never run). Migrated: wave 1."""
import hashlib

import oqs
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

TOKEN_SIGNER = oqs.Signature("ML-DSA-65")  # post-quantum signatures for order tokens (FIPS 204)
TOKEN_PUBLIC = TOKEN_SIGNER.generate_keypair()
STORAGE_KEY = AESGCM.generate_key(bit_length=256)


def sign_order_token(payload: bytes) -> bytes:
    return TOKEN_SIGNER.sign(payload)


def etag(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def barcode_checksum(sku: str) -> str:
    return hashlib.sha256(sku.encode()).hexdigest()[:8]


def encrypt_stock_snapshot(data: bytes, nonce: bytes) -> bytes:
    return AESGCM(STORAGE_KEY).encrypt(nonce, data, None)
