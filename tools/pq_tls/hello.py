"""A TLS 1.3 ClientHello that offers hybrid post-quantum key exchange, and a parser for the reply.

Wire formats: TLS 1.3 is RFC 8446 (record layer 5.1, ClientHello 4.1.2, ServerHello and
HelloRetryRequest 4.1.3, key_share 4.2.8, supported_versions 4.2.1). The hybrid group
X25519MLKEM768 (0x11EC) is RFC 10024 (August 2026, formerly draft-ietf-tls-ecdhe-mlkem): the
client share is the ML-KEM-768 encapsulation key (1184 bytes) followed by the X25519 share
(32 bytes), 1216 bytes in all; the server share is the ML-KEM ciphertext (1088 bytes) followed
by its X25519 share, 1120 bytes.

Only the first flight is built and read. Nothing here completes a handshake, derives a key or
decrypts anything.
"""

from __future__ import annotations

import hashlib
import ipaddress
import struct
from dataclasses import dataclass, field

X25519MLKEM768, X25519, SECP256R1 = 0x11EC, 0x001D, 0x0017
GROUP_NAMES = {
    0x11EC: "X25519MLKEM768", 0x11EB: "SecP256r1MLKEM768", 0x11ED: "SecP384r1MLKEM1024",
    0x001D: "x25519", 0x001E: "x448", 0x0017: "secp256r1", 0x0018: "secp384r1", 0x0019: "secp521r1",
    0x0100: "ffdhe2048", 0x0101: "ffdhe3072", 0x0102: "ffdhe4096", 0x0103: "ffdhe6144", 0x0104: "ffdhe8192",
}
PQ_HYBRID_GROUPS = {0x11EC, 0x11EB, 0x11ED}  # RFC 10024
HYBRID_CLIENT_SHARE_BYTES = 1184 + 32
HYBRID_SERVER_SHARE_BYTES = 1088 + 32

# RFC 8446 4.1.3: a HelloRetryRequest is a ServerHello whose random is SHA-256("HelloRetryRequest").
HELLO_RETRY_RANDOM = bytes.fromhex("CF21AD74E59A6111BE1D8C021E65B891C2A211167ABB8C5E079E09E2C8A8339C")
assert HELLO_RETRY_RANDOM == hashlib.sha256(b"HelloRetryRequest").digest()

CIPHER_SUITES = (0x1301, 0x1302, 0x1303)  # TLS_AES_128_GCM_SHA256, TLS_AES_256_GCM_SHA384, TLS_CHACHA20_POLY1305_SHA256
SIGNATURE_SCHEMES = (0x0403, 0x0804, 0x0401, 0x0503, 0x0805, 0x0501, 0x0806, 0x0601, 0x0807)
TLS13 = 0x0304
VERSION_NAMES = {0x0304: "TLS 1.3", 0x0303: "TLS 1.2", 0x0302: "TLS 1.1", 0x0301: "TLS 1.0"}
ALERT_NAMES = {0: "close_notify", 10: "unexpected_message", 20: "bad_record_mac", 40: "handshake_failure",
               42: "bad_certificate", 47: "illegal_parameter", 50: "decode_error", 51: "decrypt_error",
               70: "protocol_version", 71: "insufficient_security", 80: "internal_error",
               86: "inappropriate_fallback", 109: "missing_extension", 110: "unsupported_extension",
               112: "unrecognized_name", 120: "no_application_protocol"}
MAX_RESPONSE_BYTES = 64 * 1024  # more than any first flight needs; stop reading after this


class ProtocolError(ValueError):
    """The server's bytes are not a TLS record we understand."""


def _u8(data: bytes) -> bytes:
    return struct.pack("!B", len(data)) + data


def _u16(data: bytes) -> bytes:
    return struct.pack("!H", len(data)) + data


def _extension(kind: int, body: bytes) -> bytes:
    return struct.pack("!H", kind) + _u16(body)


def is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def build_client_hello(host: str, key_shares: list[tuple[int, bytes]], groups: list[int], *,
                       random: bytes, session_id: bytes) -> bytes:
    """One TLS record holding a ClientHello. key_shares and groups are in preference order;
    every share's group must also be in groups. random and session_id are 32 bytes each."""
    if len(random) != 32 or len(session_id) != 32:
        raise ValueError("random and session_id are 32 bytes")
    if not {group for group, _ in key_shares} <= set(groups):
        raise ValueError("every key share must be for an offered group")
    extensions = b""
    if host and not is_ip_literal(host):  # RFC 6066: SNI carries DNS names only
        name = host.rstrip(".").encode("ascii")
        extensions += _extension(0, _u16(b"\x00" + _u16(name)))
    extensions += _extension(10, _u16(b"".join(struct.pack("!H", g) for g in groups)))
    extensions += _extension(13, _u16(b"".join(struct.pack("!H", s) for s in SIGNATURE_SCHEMES)))
    extensions += _extension(43, _u8(struct.pack("!H", TLS13)))  # only TLS 1.3: key_share is a TLS 1.3 extension
    extensions += _extension(45, _u8(b"\x01"))  # psk_dhe_ke; no PSK is offered
    extensions += _extension(51, _u16(b"".join(struct.pack("!H", g) + _u16(k) for g, k in key_shares)))
    body = (struct.pack("!H", 0x0303) + random + _u8(session_id)
            + _u16(b"".join(struct.pack("!H", c) for c in CIPHER_SUITES)) + _u8(b"\x00") + _u16(extensions))
    handshake = b"\x01" + len(body).to_bytes(3, "big") + body
    if len(handshake) > 16384:
        raise ValueError("ClientHello does not fit one record")
    return b"\x16\x03\x01" + struct.pack("!H", len(handshake)) + handshake


@dataclass
class ServerReply:
    kind: str  # server_hello | hello_retry_request | alert
    version: str | None = None  # from supported_versions, else the legacy version
    selected_group: int | None = None
    share_length: int | None = None  # bytes of the server's key share (None in a HelloRetryRequest)
    cipher_suite: int | None = None
    alert: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def group_name(self) -> str | None:
        if self.selected_group is None:
            return None
        return GROUP_NAMES.get(self.selected_group, f"unknown group 0x{self.selected_group:04X}")


class _Reader:
    def __init__(self, data: bytes, what: str):
        self.data, self.position, self.what = data, 0, what

    def take(self, count: int) -> bytes:
        if self.position + count > len(self.data):
            raise ProtocolError(f"truncated {self.what}")
        chunk = self.data[self.position:self.position + count]
        self.position += count
        return chunk

    def u8(self) -> int:
        return self.take(1)[0]

    def u16(self) -> int:
        return struct.unpack("!H", self.take(2))[0]

    def vector(self, length_bytes: int) -> bytes:
        length = self.u8() if length_bytes == 1 else self.u16()
        return self.take(length)

    def done(self) -> bool:
        return self.position == len(self.data)


def parse_server_hello(body: bytes) -> ServerReply:
    """A ServerHello or HelloRetryRequest handshake body (without the 4-byte handshake header)."""
    reader = _Reader(body, "ServerHello")
    legacy_version = reader.u16()
    random = reader.take(32)
    reader.vector(1)  # legacy_session_id_echo
    cipher_suite = reader.u16()
    reader.u8()  # legacy_compression_method
    reply = ServerReply(kind="hello_retry_request" if random == HELLO_RETRY_RANDOM else "server_hello",
                        cipher_suite=cipher_suite, version=VERSION_NAMES.get(legacy_version, f"0x{legacy_version:04X}"))
    if reader.done():
        reply.notes.append("no extensions: a pre-TLS 1.3 server")
        return reply
    extensions = _Reader(reader.vector(2), "ServerHello extensions")
    seen = set()
    while not extensions.done():
        kind = extensions.u16()
        data = extensions.vector(2)
        if kind in seen:
            raise ProtocolError(f"duplicate extension {kind}")
        seen.add(kind)
        if kind == 43:
            if len(data) != 2:
                raise ProtocolError("bad supported_versions")
            selected = struct.unpack("!H", data)[0]
            reply.version = VERSION_NAMES.get(selected, f"0x{selected:04X}")
        elif kind == 51:
            share = _Reader(data, "key_share")
            reply.selected_group = share.u16()
            if reply.kind == "server_hello":
                reply.share_length = len(share.vector(2))
            if not share.done():
                raise ProtocolError("trailing bytes in key_share")
    if reply.kind == "server_hello" and reply.selected_group == X25519MLKEM768 and reply.share_length != HYBRID_SERVER_SHARE_BYTES:
        reply.notes.append(f"hybrid server share is {reply.share_length} bytes, expected {HYBRID_SERVER_SHARE_BYTES}")
    return reply


class ResponseParser:
    """Feed bytes as they arrive; `result` is set once a ServerHello, HelloRetryRequest or alert
    has been read. Raises ProtocolError for anything that is not TLS."""

    def __init__(self):
        self.buffer = b""
        self.handshake = b""
        self.result: ServerReply | None = None
        self.received = 0

    def feed(self, data: bytes) -> ServerReply | None:
        self.received += len(data)
        if self.received > MAX_RESPONSE_BYTES:
            raise ProtocolError("server sent too much before a ServerHello")
        self.buffer += data
        while self.result is None and len(self.buffer) >= 5:
            content_type, major, _minor, length = struct.unpack("!BBBH", self.buffer[:5])
            if content_type not in (20, 21, 22) or major != 3 or length > 16384 + 256:
                raise ProtocolError("not a TLS record (the reply is not TLS, or the port speaks another protocol)")
            if len(self.buffer) < 5 + length:
                break
            fragment, self.buffer = self.buffer[5:5 + length], self.buffer[5 + length:]
            if content_type == 21:
                if len(fragment) != 2:
                    raise ProtocolError("bad alert")
                description = fragment[1]
                self.result = ServerReply(kind="alert", alert=ALERT_NAMES.get(description, f"alert {description}"))
            elif content_type == 22:
                self.handshake += fragment
                if len(self.handshake) >= 4:
                    message_type = self.handshake[0]
                    size = int.from_bytes(self.handshake[1:4], "big")
                    if message_type != 2:
                        raise ProtocolError(f"expected a ServerHello, got handshake message {message_type}")
                    if len(self.handshake) >= 4 + size:
                        self.result = parse_server_hello(self.handshake[4:4 + size])
            # content type 20 (change_cipher_spec) before the ServerHello is ignored
        return self.result
