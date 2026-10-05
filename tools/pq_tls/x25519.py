"""X25519 (RFC 7748, section 5) in pure Python, so the classical key share needs no dependency.

Only public keys are computed and used here; the handshake is never completed, so the private
scalar is thrown away. Not constant-time: fine for a probe, not for real key agreement.
"""

from __future__ import annotations

import os

P = 2**255 - 19
A24 = 121665


def _clamp(scalar: bytes) -> int:
    if len(scalar) != 32:
        raise ValueError("an X25519 scalar is 32 bytes")
    value = bytearray(scalar)
    value[0] &= 248
    value[31] &= 127
    value[31] |= 64
    return int.from_bytes(value, "little")


def _decode_u(u: bytes) -> int:
    if len(u) != 32:
        raise ValueError("an X25519 u-coordinate is 32 bytes")
    value = bytearray(u)
    value[31] &= 127
    return int.from_bytes(value, "little") % P


def x25519(scalar: bytes, u: bytes) -> bytes:
    """The Montgomery ladder of RFC 7748 section 5."""
    k, x1 = _clamp(scalar), _decode_u(u)
    x2, z2, x3, z3, swap = 1, 0, x1, 1, 0
    for t in reversed(range(255)):
        bit = (k >> t) & 1
        swap ^= bit
        if swap:
            x2, x3, z2, z3 = x3, x2, z3, z2
        swap = bit
        a, b = (x2 + z2) % P, (x2 - z2) % P
        aa, bb = a * a % P, b * b % P
        e = (aa - bb) % P
        c, d = (x3 + z3) % P, (x3 - z3) % P
        da, cb = d * a % P, c * b % P
        x3 = (da + cb) ** 2 % P
        z3 = x1 * (da - cb) ** 2 % P
        x2 = aa * bb % P
        z2 = e * (aa + A24 * e) % P
    if swap:
        x2, z2 = x3, z3
    return (x2 * pow(z2, P - 2, P) % P).to_bytes(32, "little")


BASE_POINT = (9).to_bytes(32, "little")


def public_key(scalar: bytes) -> bytes:
    return x25519(scalar, BASE_POINT)


def new_public_key() -> bytes:
    """A fresh X25519 public key; its private scalar is discarded."""
    return public_key(os.urandom(32))
