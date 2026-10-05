"""Where the ML-KEM-768 encapsulation key for the hybrid key share comes from.

In order: the `cryptography` package (45+), liboqs through lessons/_pqc (which never lets
liboqs-python auto-install), then `kyber-py` if it happens to be installed (it is not a dependency).
If none is available, the probe offers classical groups only and says that the PQ check was skipped.
The decapsulation key is discarded: the handshake is never completed.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

ENCAPSULATION_KEY_BYTES = 1184  # ML-KEM-768 (FIPS 203)
LESSONS = Path(__file__).resolve().parents[2] / "lessons"


@dataclass(frozen=True)
class EncapsulationKey:
    key: bytes
    source: str  # which implementation made it


def _from_cryptography() -> EncapsulationKey | None:
    try:
        import cryptography
        from cryptography.hazmat.primitives.asymmetric import mlkem
    except ImportError:
        return None
    try:
        key = mlkem.MLKEM768PrivateKey.generate().public_key().public_bytes_raw()
    except Exception:  # noqa: BLE001 - e.g. UnsupportedAlgorithm on a build without ML-KEM
        return None
    return EncapsulationKey(key, f"cryptography {cryptography.__version__}")


def _from_liboqs() -> EncapsulationKey | None:
    if not (LESSONS / "_pqc.py").is_file():
        return None
    if str(LESSONS) not in sys.path:
        sys.path.insert(0, str(LESSONS))
    try:
        import _pqc

        oqs = _pqc.load_oqs()
    except Exception:  # noqa: BLE001
        return None
    if oqs is None:
        return None
    try:
        with oqs.KeyEncapsulation("ML-KEM-768") as kem:
            key = bytes(kem.generate_keypair())
    except Exception:  # noqa: BLE001
        return None
    return EncapsulationKey(key, "liboqs (via lessons/_pqc)")


def _from_kyber_py() -> EncapsulationKey | None:
    try:
        from kyber_py.ml_kem import ML_KEM_768
    except ImportError:
        return None
    try:
        key, _ = ML_KEM_768.keygen()
    except Exception:  # noqa: BLE001
        return None
    return EncapsulationKey(bytes(key), "kyber-py")


PROVIDERS = (_from_cryptography, _from_liboqs, _from_kyber_py)


def encapsulation_key() -> EncapsulationKey | None:
    """A fresh ML-KEM-768 encapsulation key from the first working provider, or None."""
    for provider in PROVIDERS:
        result = provider()
        if result is not None and len(result.key) == ENCAPSULATION_KEY_BYTES:
            return result
    return None
