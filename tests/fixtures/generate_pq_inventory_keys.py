"""Regenerate the key/certificate fixtures (TEST MATERIAL ONLY, never used anywhere else).

No private key is written here, not even an encrypted one: the committed corpus holds public keys
and certificates only. Tests that need private keys (plain or encrypted) generate them at run time
in a temporary directory (see tests/test_pq_inventory.py and tests/test_pq_inventory_hardening.py).
Post-quantum fixtures (keys/pqc/, public material only) need cryptography >= 45 for ML-KEM/ML-DSA
and liboqs for SLH-DSA; regenerate only them with --pqc-only.
Run: .venv/bin/python tests/fixtures/generate_pq_inventory_keys.py [--pqc-only]
"""

from __future__ import annotations

import datetime
import subprocess
import sys
import tempfile
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
from cryptography.x509.oid import NameOID

HERE = Path(__file__).resolve().parent / "pq_inventory"
ROOT = Path(__file__).resolve().parents[2]
SLH_DSA_SHA2_128S = "2.16.840.1.101.3.4.3.20"  # id-slh-dsa-sha2-128s (NIST CSOR)


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
    ssh_rsa = rsa.generate_private_key(public_exponent=65537, key_size=3072).public_key().public_bytes(
        serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH)
    ssh_ed = ed25519.Ed25519PrivateKey.generate().public_key().public_bytes(
        serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH)
    (ssh / "authorized_keys").write_text(f"{ssh_rsa.decode()} deploy@test\n{ssh_ed.decode()} admin@test\n")


def _name(common_name: str) -> bytes:
    from pq_inventory.der import encode, encode_oid

    def rdn(oid: str, value: str) -> bytes:
        return encode(0x31, encode(0x30, encode_oid(oid) + encode(0x0C, value.encode())))

    return encode(0x30, rdn("2.5.4.3", common_name) + rdn("2.5.4.10", "pq_inventory TEST ONLY"))


def pqc_fixtures() -> None:
    """ML-KEM-768 and ML-DSA-65 public keys and an ML-DSA-65 certificate (cryptography), an SLH-DSA-SHA2-128s
    public key and a self-signed SLH-DSA certificate (liboqs; DER assembled here because cryptography 50
    cannot build SLH-DSA certificates). The private keys only ever exist in memory."""
    from cryptography.hazmat.primitives.asymmetric import mldsa, mlkem

    sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "lessons")]
    import _pqc
    from pq_inventory.der import encode, encode_oid, spki_der, to_pem

    out = HERE / "keys" / "pqc"
    out.mkdir(parents=True, exist_ok=True)
    pem, spki = serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    (out / "mlkem768_public.pem").write_bytes(mlkem.MLKEM768PrivateKey.generate().public_key().public_bytes(pem, spki))
    dsa_key = mldsa.MLDSA65PrivateKey.generate()
    (out / "mldsa65_public.pem").write_bytes(dsa_key.public_key().public_bytes(pem, spki))
    (out / "mldsa65_cert.pem").write_bytes(certificate(dsa_key, "mldsa.test.invalid", None).public_bytes(pem))
    oqs = _pqc.load_oqs()
    if oqs is None:
        raise SystemExit(_pqc.missing_reason())
    with oqs.Signature("SLH_DSA_PURE_SHA2_128S") as signer:
        public = signer.generate_keypair()
        (out / "slh_dsa_sha2_128s_public.pem").write_bytes(to_pem("PUBLIC KEY", spki_der(SLH_DSA_SHA2_128S, public)))
        algorithm = encode(0x30, encode_oid(SLH_DSA_SHA2_128S))
        validity = encode(0x30, encode(0x17, b"260101000000Z") + encode(0x17, b"270101000000Z"))
        name = _name("slh.test.invalid")
        tbs = encode(0x30, encode(0xA0, encode(0x02, b"\x02")) + encode(0x02, b"\x01") + algorithm + name + validity + name
                     + spki_der(SLH_DSA_SHA2_128S, public))
        signature = signer.sign(tbs)
    (out / "slh_dsa_sha2_128s_cert.der").write_bytes(encode(0x30, tbs + algorithm + encode(0x03, b"\x00" + signature)))


if __name__ == "__main__":
    if "--pqc-only" not in sys.argv:
        main()
    pqc_fixtures()
