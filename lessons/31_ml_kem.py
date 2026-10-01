"""Lesson 31: ML-KEM hands-on (keygen, encapsulate, decapsulate) against RSA-2048 and X25519.

Needs the optional extra: pip install -e '.[pqc]' plus the liboqs C library (docs/DECISIONS.md D1).
Without them the script prints why and exits cleanly.
"""

from __future__ import annotations

import os

from _common import heading
from _pqc import load_oqs, median_time, missing_reason

PARAMETER_SETS = ("ML-KEM-512", "ML-KEM-768", "ML-KEM-1024")
REPEATS = 200


def ml_kem(oqs) -> dict:
    rows = {}
    for name in PARAMETER_SETS:
        with oqs.KeyEncapsulation(name) as alice:
            public = alice.generate_keypair()
            with oqs.KeyEncapsulation(name) as bob:
                ciphertext, bob_secret = bob.encap_secret(public)
                alice_secret = alice.decap_secret(ciphertext)
                tampered = bytearray(ciphertext)
                tampered[0] ^= 1
                tampered_secret = alice.decap_secret(bytes(tampered))
                details = alice.details
                rows[name] = {
                    "public_key": len(public), "secret_key": details["length_secret_key"], "ciphertext": len(ciphertext),
                    "shared_secret": len(bob_secret), "agree": alice_secret == bob_secret,
                    "tampered_differs": tampered_secret != bob_secret, "claimed_nist_level": details["claimed_nist_level"],
                    "keygen_s": median_time(lambda: oqs.KeyEncapsulation(name).generate_keypair(), REPEATS),
                    "encaps_s": median_time(lambda: bob.encap_secret(public), REPEATS),
                    "decaps_s": median_time(lambda: alice.decap_secret(ciphertext), REPEATS),
                }
    return rows


def classical() -> dict:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa, x25519

    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rsa_public = rsa_key.public_key()
    oaep = padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
    secret = os.urandom(32)
    rsa_ciphertext = rsa_public.encrypt(secret, oaep)
    spki = serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    rsa_row = {
        "public_key": len(rsa_public.public_bytes(*spki)), "public_key_raw": 256,
        "secret_key": len(rsa_key.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8,
                                                 serialization.NoEncryption())),
        "ciphertext": len(rsa_ciphertext), "agree": rsa_key.decrypt(rsa_ciphertext, oaep) == secret,
        "keygen_s": median_time(lambda: rsa.generate_private_key(public_exponent=65537, key_size=2048), 9),
        "encaps_s": median_time(lambda: rsa_public.encrypt(secret, oaep), REPEATS),
        "decaps_s": median_time(lambda: rsa_key.decrypt(rsa_ciphertext, oaep), REPEATS),
    }
    alice, bob = x25519.X25519PrivateKey.generate(), x25519.X25519PrivateKey.generate()
    raw = serialization.Encoding.Raw, serialization.PublicFormat.Raw
    x_row = {
        "public_key": len(alice.public_key().public_bytes(*raw)), "secret_key": 32, "ciphertext": len(bob.public_key().public_bytes(*raw)),
        "agree": alice.exchange(bob.public_key()) == bob.exchange(alice.public_key()),
        "keygen_s": median_time(x25519.X25519PrivateKey.generate, REPEATS),
        "encaps_s": median_time(lambda: bob.exchange(alice.public_key()), REPEATS),
        "decaps_s": median_time(lambda: alice.exchange(bob.public_key()), REPEATS),
    }
    return {"RSA-2048 (OAEP)": rsa_row, "X25519": x_row}


def main() -> dict:
    reason = missing_reason()
    if reason:
        print(f"Skipping lesson 31: {reason}")
        return {"skipped": reason}
    oqs = load_oqs()

    heading("Step 1: ML-KEM round trip (keygen -> encapsulate -> decapsulate), liboqs " + oqs.oqs_version())
    kem = ml_kem(oqs)
    for name, row in kem.items():
        print(f"{name}: shared secrets agree: {row['agree']};  a flipped ciphertext bit gives a different secret: "
              f"{row['tampered_differs']}  (NIST level {row['claimed_nist_level']})")
    print("ML-KEM never reports 'tampered'. It returns an unrelated secret (implicit rejection), and the")
    print("mismatch shows up later, when the derived keys fail to decrypt.")

    heading("Step 2: sizes in bytes (what goes over the wire matters)")
    others = classical()
    print(f"{'scheme':<16}{'public key':>12}{'secret key':>12}{'ciphertext*':>13}{'shared':>8}")
    for name, row in {**kem, **others}.items():
        shared = row.get("shared_secret", 32)
        print(f"{name:<16}{row['public_key']:>12}{row['secret_key']:>12}{row['ciphertext']:>13}{shared:>8}")
    print("* for X25519 the 'ciphertext' is the other side's public key; RSA's public key is SPKI DER")
    print("  (256 bytes of modulus inside). Secret keys: ML-KEM's decapsulation key as liboqs stores it; RSA as PKCS#8 DER.")

    heading(f"Step 3: speed (median of {REPEATS} runs on this machine; indicative only)")
    print(f"{'scheme':<16}{'keygen':>12}{'encaps/encrypt':>16}{'decaps/decrypt':>16}")
    for name, row in {**kem, **others}.items():
        print(f"{name:<16}{row['keygen_s'] * 1e6:>10.1f}us{row['encaps_s'] * 1e6:>14.1f}us{row['decaps_s'] * 1e6:>14.1f}us")
    print("ML-KEM is fast, often faster than RSA. Its cost is size: about 1 KB each way at ML-KEM-768,")
    print("against 32 bytes for X25519.")
    return {"kem": kem, "classical": others}


if __name__ == "__main__":
    main()
