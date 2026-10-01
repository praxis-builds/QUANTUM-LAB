"""Generate the demo's public keys and certificates (TEST ONLY; no private key is kept).

Run from the repository root: python examples/warehouse-demo/generate_demo_keys.py
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

HERE = Path(__file__).resolve().parent


def cert(key, common_name: str, start: datetime.datetime, days: int) -> bytes:
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name),
                      x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Northwind Warehouse DEMO - TEST ONLY")])
    built = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
             .serial_number(x509.random_serial_number()).not_valid_before(start)
             .not_valid_after(start + datetime.timedelta(days=days)).sign(key, hashes.SHA256()))
    return built.public_bytes(serialization.Encoding.PEM)


def openssh_public(key) -> str:
    return key.public_key().public_bytes(serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH).decode()


def main() -> None:
    start = datetime.datetime(2026, 1, 15, tzinfo=datetime.timezone.utc)
    before, after = HERE / "before", HERE / "after"
    for folder in (before / "certs", before / "ssh", after / "certs", after / "ssh"):
        folder.mkdir(parents=True, exist_ok=True)
    (before / "certs" / "warehouse-api.pem").write_bytes(
        cert(rsa.generate_private_key(public_exponent=65537, key_size=2048), "inventory.northwind.test", start, 825))
    with tempfile.TemporaryDirectory() as tmp:  # SHA-1 needs the openssl CLI; the key stays in tmp
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", f"{tmp}/k.pem",
                        "-out", str(before / "certs" / "legacy-edi.pem"), "-sha1", "-days", "3650",
                        "-subj", "/CN=edi.northwind.test/O=Northwind Warehouse DEMO - TEST ONLY"], check=True, capture_output=True)
    deploy_rsa = openssh_public(rsa.generate_private_key(public_exponent=65537, key_size=2048))
    (before / "ssh" / "deploy_key.pub").write_text(f"{deploy_rsa} deploy@northwind.test\n")
    (before / "ssh" / "authorized_keys").write_text(f"{deploy_rsa} deploy@northwind.test\n")
    # After the first wave: the API certificate moves to ECDSA P-256 (still quantum-vulnerable: public PKI
    # cannot issue ML-DSA certificates yet), the SHA-1 EDI certificate is retired, SSH moves to Ed25519.
    (after / "certs" / "warehouse-api.pem").write_bytes(cert(ec.generate_private_key(ec.SECP256R1()), "inventory.northwind.test", start, 398))
    deploy_ed = openssh_public(ed25519.Ed25519PrivateKey.generate())
    (after / "ssh" / "deploy_key.pub").write_text(f"{deploy_ed} deploy@northwind.test\n")
    (after / "ssh" / "authorized_keys").write_text(f"{deploy_ed} deploy@northwind.test\n")


if __name__ == "__main__":
    main()
