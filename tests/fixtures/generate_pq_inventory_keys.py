"""Regenerate the key/certificate fixtures (TEST MATERIAL ONLY, never used anywhere else).

No unencrypted private key is written here: the committed corpus holds public keys, certificates
and one password-encrypted private key. Tests that need plain private keys generate them at run
time in a temporary directory (see tests/test_pq_inventory.py).
Run: .venv/bin/python tests/fixtures/generate_pq_inventory_keys.py
"""

from __future__ import annotations

import datetime
import subprocess
import tempfile
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
from cryptography.x509.oid import NameOID

HERE = Path(__file__).resolve().parent / "pq_inventory"


def certificate(key, name: str, hash_algorithm, days: int = 365):
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name),
                         x509.NameAttribute(NameOID.ORGANIZATION_NAME, "pq_inventory TEST ONLY")])
    start = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    return (x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(start)
            .not_valid_after(start + datetime.timedelta(days=days)).sign(key, hash_algorithm))


def main() -> None:
    keys = HERE / "keys"
    ssh = HERE / "ssh"
    keys.mkdir(exist_ok=True)
    ssh.mkdir(exist_ok=True)
    pem, spki = serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    # cryptography refuses to create SHA-1 signatures, so the legacy certificate comes from the openssl CLI;
    # its private key only ever exists in a temporary directory.
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", f"{tmp}/k.pem",
                        "-out", str(keys / "legacy_sha1_cert.pem"), "-sha1", "-days", "365",
                        "-subj", "/CN=legacy.test.invalid/O=pq_inventory TEST ONLY"], check=True, capture_output=True)
    ec_key = ec.generate_private_key(ec.SECP256R1())
    (keys / "ec_p256_public.pem").write_bytes(ec_key.public_key().public_bytes(pem, spki))
    modern = certificate(ec_key, "api.test.invalid", hashes.SHA256())
    (keys / "ecdsa_cert.der").write_bytes(modern.public_bytes(serialization.Encoding.DER))
    encrypted = rsa.generate_private_key(public_exponent=65537, key_size=3072).private_bytes(
        pem, serialization.PrivateFormat.PKCS8, serialization.BestAvailableEncryption(b"test-only-password"))
    (keys / "encrypted_private_key.pem").write_bytes(encrypted)
    ssh_rsa = rsa.generate_private_key(public_exponent=65537, key_size=3072).public_key().public_bytes(
        serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH)
    ssh_ed = ed25519.Ed25519PrivateKey.generate().public_key().public_bytes(
        serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH)
    (ssh / "authorized_keys").write_text(f"{ssh_rsa.decode()} deploy@test\n{ssh_ed.decode()} admin@test\n")


if __name__ == "__main__":
    main()
