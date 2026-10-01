"""Minimal, bounded DER reading: the algorithm OIDs of public keys, PKCS#8 private keys and certificates.

Used before (and without) the optional `cryptography` package, so post-quantum keys and certificates
are recognised even when `cryptography` cannot load them (SLH-DSA in cryptography 50) or is absent.
Only tags, lengths and OIDs are read; key material is never decoded or kept.
"""

from __future__ import annotations

import base64
import binascii

# NIST Computer Security Objects Register: sigAlgs = 2.16.840.1.101.3.4.3, kems = 2.16.840.1.101.3.4.4.
_SIG, _KEM = "2.16.840.1.101.3.4.3.", "2.16.840.1.101.3.4.4."
PQC_OIDS: dict[str, tuple[str, str]] = {
    _KEM + "1": ("ML-KEM", "ML-KEM-512"), _KEM + "2": ("ML-KEM", "ML-KEM-768"), _KEM + "3": ("ML-KEM", "ML-KEM-1024"),
    _SIG + "17": ("ML-DSA", "ML-DSA-44"), _SIG + "18": ("ML-DSA", "ML-DSA-65"), _SIG + "19": ("ML-DSA", "ML-DSA-87"),
}
# id-slh-dsa-* = sigAlgs 20..31, in this order (FIPS 205 parameter sets).
_SLH = ["SHA2-128s", "SHA2-128f", "SHA2-192s", "SHA2-192f", "SHA2-256s", "SHA2-256f",
        "SHAKE-128s", "SHAKE-128f", "SHAKE-192s", "SHAKE-192f", "SHAKE-256s", "SHAKE-256f"]
PQC_OIDS.update({_SIG + str(20 + i): ("SLH-DSA", f"SLH-DSA-{name}") for i, name in enumerate(_SLH)})
# Classical public-key algorithm OIDs (for naming keys cryptography cannot load).
CLASSICAL_OIDS: dict[str, str] = {
    "1.2.840.113549.1.1.1": "RSA", "1.2.840.113549.1.1.10": "RSA", "1.2.840.10045.2.1": "EC", "1.2.840.10040.4.1": "DSA",
    "1.3.101.110": "X25519", "1.3.101.111": "X25519", "1.3.101.112": "EdDSA", "1.3.101.113": "EdDSA",
    "1.2.840.113549.1.3.1": "DH", "1.2.840.10046.2.1": "DH",
}
MAX_DER = 1 << 20


class DerError(ValueError):
    pass


def _tlv(data: bytes, position: int, end: int) -> tuple[int, int, int]:
    """(tag, value start, value end) of the element at position, checked against end."""
    if position + 2 > end:
        raise DerError("truncated")
    tag, first = data[position], data[position + 1]
    position += 2
    if first < 0x80:
        length = first
    else:
        count = first & 0x7F
        if count == 0 or count > 4 or position + count > end:
            raise DerError("bad length")
        length = int.from_bytes(data[position:position + count], "big")
        position += count
    if position + length > end:
        raise DerError("length past end")
    return tag, position, position + length


def _children(data: bytes, start: int, end: int, limit: int = 16) -> list[tuple[int, int, int, int]]:
    """(tag, element start, value start, value end) for up to `limit` elements in start..end."""
    items, position = [], start
    while position < end and len(items) < limit:
        tag, value_start, value_end = _tlv(data, position, end)
        items.append((tag, position, value_start, value_end))
        position = value_end
    return items


def oid_string(raw: bytes) -> str:
    if not raw or len(raw) > 64:
        raise DerError("bad OID")
    first = raw[0]
    parts = [min(first // 40, 2), first - 40 * min(first // 40, 2)]
    value = 0
    for byte in raw[1:]:
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            parts.append(value)
            value = 0
    return ".".join(map(str, parts))


def _algorithm_oid(data: bytes, start: int, end: int) -> str:
    """OID of an AlgorithmIdentifier SEQUENCE { OID, parameters OPTIONAL } spanning start..end."""
    tag, value_start, value_end = _tlv(data, start, end)
    if tag != 0x30:
        raise DerError("AlgorithmIdentifier is not a SEQUENCE")
    oid_tag, oid_start, oid_end = _tlv(data, value_start, value_end)
    if oid_tag != 0x06:
        raise DerError("no OID")
    return oid_string(data[oid_start:oid_end])


def _outer(data: bytes) -> tuple[int, int]:
    if len(data) > MAX_DER:
        raise DerError("too large")
    tag, start, end = _tlv(data, 0, len(data))
    if tag != 0x30:
        raise DerError("not a SEQUENCE")
    return start, end


def spki_oid(data: bytes) -> str:
    """SubjectPublicKeyInfo ::= SEQUENCE { algorithm AlgorithmIdentifier, subjectPublicKey BIT STRING }."""
    start, end = _outer(data)
    children = _children(data, start, end, 2)
    if len(children) != 2 or children[1][0] != 0x03:
        raise DerError("not a SubjectPublicKeyInfo")
    return _algorithm_oid(data, children[0][1], children[0][3])


def pkcs8_oid(data: bytes) -> str:
    """PrivateKeyInfo ::= SEQUENCE { version INTEGER, privateKeyAlgorithm AlgorithmIdentifier, privateKey OCTET STRING, ... }."""
    start, end = _outer(data)
    children = _children(data, start, end, 3)
    if len(children) < 3 or children[0][0] != 0x02 or children[2][0] != 0x04:
        raise DerError("not a PKCS#8 PrivateKeyInfo")
    return _algorithm_oid(data, children[1][1], children[1][3])


def certificate_oids(data: bytes) -> tuple[str, str]:
    """(subject public-key algorithm OID, signature algorithm OID) of an X.509 certificate."""
    start, end = _outer(data)
    children = _children(data, start, end, 3)
    if len(children) != 3 or children[0][0] != 0x30 or children[1][0] != 0x30:
        raise DerError("not a Certificate")
    _, _, tbs_start, tbs_end = children[0]
    fields = _children(data, tbs_start, tbs_end, 10)
    if fields and fields[0][0] == 0xA0:  # explicit [0] version
        fields = fields[1:]
    # serialNumber, signature, issuer, validity, subject, subjectPublicKeyInfo
    if len(fields) < 6 or fields[5][0] != 0x30:
        raise DerError("TBSCertificate too short")
    spki = data[fields[5][1]:fields[5][3]]
    return spki_oid(spki), _algorithm_oid(data, children[1][1], children[1][3])


def pem_body(block: bytes) -> bytes | None:
    """Base64 body of a PEM block (None for encrypted legacy PEM with headers, or bad base64)."""
    if b":" in block:  # RFC 1421 headers (Proc-Type, DEK-Info): a legacy encrypted key
        return None
    try:
        return base64.b64decode(b"".join(block.split()), validate=True)
    except (binascii.Error, ValueError):
        return None


# ------------------------------------------------------------------ encoding (test fixtures only)

def _length(n: int) -> bytes:
    return bytes([n]) if n < 0x80 else bytes([0x80 | ((n.bit_length() + 7) // 8)]) + n.to_bytes((n.bit_length() + 7) // 8, "big")


def encode(tag: int, value: bytes) -> bytes:
    return bytes([tag]) + _length(len(value)) + value


def encode_oid(dotted: str) -> bytes:
    numbers = [int(x) for x in dotted.split(".")]
    body = bytes([40 * numbers[0] + numbers[1]])
    for number in numbers[2:]:
        chunk = [number & 0x7F]
        number >>= 7
        while number:
            chunk.append(0x80 | (number & 0x7F))
            number >>= 7
        body += bytes(reversed(chunk))
    return encode(0x06, body)


def spki_der(oid: str, public_key: bytes) -> bytes:
    return encode(0x30, encode(0x30, encode_oid(oid)) + encode(0x03, b"\x00" + public_key))


def to_pem(label: str, der: bytes) -> bytes:
    text = base64.b64encode(der).decode()
    lines = "\n".join(text[i:i + 64] for i in range(0, len(text), 64))
    return f"-----BEGIN {label}-----\n{lines}\n-----END {label}-----\n".encode()


def spki_pem(oid: str, public_key: bytes) -> bytes:
    return to_pem("PUBLIC KEY", spki_der(oid, public_key))
