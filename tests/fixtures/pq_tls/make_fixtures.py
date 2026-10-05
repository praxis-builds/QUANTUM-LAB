"""Writes the byte fixtures for tests/test_pq_tls.py. Deterministic: run it again and nothing changes.

    .venv/bin/python tests/fixtures/pq_tls/make_fixtures.py

The ServerHello side is built here by hand from RFC 8446 section 4.1.3, independently of
tools/pq_tls/hello.py, so the parser is checked against bytes it did not produce. Key material is
filler (counter bytes), never a real key.
"""

from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HRR_RANDOM = hashlib.sha256(b"HelloRetryRequest").digest()


def filler(label: str, size: int) -> bytes:
    out = b""
    counter = 0
    while len(out) < size:
        out += hashlib.sha256(f"{label}:{counter}".encode()).digest()
        counter += 1
    return out[:size]


def record(content_type: int, fragment: bytes) -> bytes:
    return struct.pack("!BBBH", content_type, 3, 3, len(fragment)) + fragment


def server_hello(*, random: bytes, group: int, share: bytes | None, version: int | None = 0x0304,
                 cipher: int = 0x1301, legacy_version: int = 0x0303) -> bytes:
    extensions = b""
    if version is not None:
        extensions += struct.pack("!HHH", 43, 2, version)
    if share is None:
        extensions += struct.pack("!HHH", 51, 2, group)
    else:
        body = struct.pack("!HH", group, len(share)) + share
        extensions += struct.pack("!HH", 51, len(body)) + body
    body = struct.pack("!H", legacy_version) + random + bytes([32]) + filler("session", 32) + struct.pack("!HB", cipher, 0)
    body += struct.pack("!H", len(extensions)) + extensions
    return record(22, b"\x02" + len(body).to_bytes(3, "big") + body)


def fixtures() -> dict[str, bytes]:
    random = filler("server-random", 32)
    hybrid_share = filler("mlkem-ciphertext", 1088) + filler("server-x25519", 32)
    tls12_body = struct.pack("!H", 0x0303) + random + bytes([0]) + struct.pack("!HB", 0xC02F, 0)  # no extensions
    out = {
        "server_hello_hybrid": server_hello(random=random, group=0x11EC, share=hybrid_share),
        "server_hello_x25519": server_hello(random=random, group=0x001D, share=filler("server-x25519", 32)),
        "hello_retry_secp256r1": server_hello(random=HRR_RANDOM, group=0x0017, share=None),
        "alert_protocol_version": record(21, bytes([2, 70])),
        "server_hello_tls12": record(22, b"\x02" + len(tls12_body).to_bytes(3, "big") + tls12_body),
    }
    # The client side comes from the tool, with fixed inputs, so any change to the wire format shows up.
    sys.path.insert(0, str(HERE.parents[2] / "tools"))
    from pq_tls.hello import build_client_hello

    shares = [(0x11EC, filler("mlkem-encapsulation-key", 1184) + filler("client-x25519-a", 32)),
              (0x001D, filler("client-x25519-b", 32))]
    out["client_hello_hybrid"] = build_client_hello("example.com", shares, [0x11EC, 0x001D, 0x0017],
                                                    random=filler("client-random", 32), session_id=filler("client-session", 32))
    return out


if __name__ == "__main__":
    for name, data in fixtures().items():
        (HERE / f"{name}.hex").write_text(data.hex() + "\n")
        print(f"{name}.hex: {len(data)} bytes")
