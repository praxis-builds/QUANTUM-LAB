"""Lesson 33: ML-DSA signatures (FIPS 204): sign, verify, sizes against ECDSA, tampering fails."""

from __future__ import annotations

from _common import heading
from _pqc import load_oqs, median_time, missing_reason

ML_DSA = ("ML-DSA-44", "ML-DSA-65", "ML-DSA-87")
SLH_DSA = ("SLH_DSA_PURE_SHA2_128S", "SLH_DSA_PURE_SHA2_128F")
MESSAGE = b"Pay 100 EUR to account 12345"
TAMPERED = b"Pay 900 EUR to account 12345"
REPEATS = 100


def pq_signature(oqs, name: str, repeats: int) -> dict:
    with oqs.Signature(name) as signer:
        public = signer.generate_keypair()
        signature = signer.sign(MESSAGE)
        with oqs.Signature(name) as verifier:
            flipped = bytearray(signature)
            flipped[10] ^= 1
            other = oqs.Signature(name)
            other_public = other.generate_keypair()
            other.free()
            row = {
                "public_key": len(public), "secret_key": signer.details["length_secret_key"], "signature": len(signature),
                "valid": verifier.verify(MESSAGE, signature, public),
                "tampered_message": verifier.verify(TAMPERED, signature, public),
                "tampered_signature": verifier.verify(MESSAGE, bytes(flipped), public),
                "wrong_key": verifier.verify(MESSAGE, signature, other_public),
                "level": signer.details["claimed_nist_level"],
                "sign_s": median_time(lambda: signer.sign(MESSAGE), repeats),
                "verify_s": median_time(lambda: verifier.verify(MESSAGE, signature, public), repeats),
            }
    return row


def classical() -> dict:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec, ed25519

    def checks(verify) -> dict:
        def ok(*args) -> bool:
            try:
                verify(*args)
                return True
            except InvalidSignature:
                return False
        return ok

    rows = {}
    key = ec.generate_private_key(ec.SECP256R1())
    signature = key.sign(MESSAGE, ec.ECDSA(hashes.SHA256()))
    ok = checks(lambda m, s: key.public_key().verify(s, m, ec.ECDSA(hashes.SHA256())))
    point = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    rows["ECDSA P-256"] = {"public_key": len(point), "secret_key": 32, "signature": len(signature),
                           "valid": ok(MESSAGE, signature), "tampered_message": ok(TAMPERED, signature),
                           "sign_s": median_time(lambda: key.sign(MESSAGE, ec.ECDSA(hashes.SHA256())), REPEATS),
                           "verify_s": median_time(lambda: ok(MESSAGE, signature), REPEATS)}
    ed = ed25519.Ed25519PrivateKey.generate()
    ed_signature = ed.sign(MESSAGE)
    ok = checks(lambda m, s: ed.public_key().verify(s, m))
    rows["Ed25519"] = {"public_key": 32, "secret_key": 32, "signature": len(ed_signature),
                       "valid": ok(MESSAGE, ed_signature), "tampered_message": ok(TAMPERED, ed_signature),
                       "sign_s": median_time(lambda: ed.sign(MESSAGE), REPEATS),
                       "verify_s": median_time(lambda: ok(MESSAGE, ed_signature), REPEATS)}
    return rows


def main() -> dict:
    reason = missing_reason()
    if reason:
        print(f"Skipping lesson 33: {reason}")
        return {"skipped": reason}
    oqs = load_oqs()

    heading("Step 1: sign, verify, and try to cheat (ML-DSA, FIPS 204)")
    pq = {name: pq_signature(oqs, name, REPEATS) for name in ML_DSA}
    for name, row in pq.items():
        print(f"{name}: valid {row['valid']};  altered message {row['tampered_message']};  "
              f"flipped signature bit {row['tampered_signature']};  someone else's public key {row['wrong_key']}")
    print(f"(signed: {MESSAGE!r}; altered: {TAMPERED!r})")

    heading("Step 2: sizes in bytes, and the hash-based alternative SLH-DSA (FIPS 205)")
    slh = {name: pq_signature(oqs, name, 3) for name in SLH_DSA}
    others = classical()
    print(f"{'scheme':<24}{'public key':>11}{'signature':>11}{'level':>7}")
    for name, row in {**others, **pq, **slh}.items():
        print(f"{name:<24}{row['public_key']:>11}{row['signature']:>11}{row.get('level', '-'):>7}")
    print("ECDSA public key: uncompressed point; ECDSA signature: DER, so 70-72 bytes depending on the values.")

    heading(f"Step 3: speed (median, this machine; indicative only)")
    for name, row in {**others, **pq, **slh}.items():
        print(f"{name:<24} sign {row['sign_s'] * 1e6:>10.1f} us   verify {row['verify_s'] * 1e6:>9.1f} us")
    print("ML-DSA signs and verifies fast; its cost is size (ML-DSA-65: about 3.3 KB per signature).")
    print("SLH-DSA rests only on hash functions (very conservative) but is slower and bigger.")
    return {"pq": pq, "slh": slh, "classical": others}


if __name__ == "__main__":
    main()
