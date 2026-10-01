"""Keys and certificates: PEM/DER, OpenSSH private keys, SSH public-key lines.

Only metadata is reported (type, size, curve, signature hash, subject, expiry, path). Key material
is never copied into a finding. Parsing uses the optional `cryptography` package; without it the
PEM headers still give the key type.
"""

from __future__ import annotations

import bisect
import re
import time

from . import der
from .model import Finding

PEM_BEGIN = re.compile(rb"-----BEGIN ([A-Z0-9 ]{1,64})-----")
PEM_END = re.compile(rb"-----END ([A-Z0-9 ]{1,64})-----")
MAX_PEM_BLOCK = 1024 * 1024  # bytes between BEGIN and END; larger "blocks" are not PEM
SSH_PUBLIC = re.compile(rb"(?:^|\s)(ssh-rsa|ssh-dss|ssh-ed25519|ssh-ed448|ecdsa-sha2-nistp(?:256|384|521)|sk-ssh-ed25519@openssh\.com|sk-ecdsa-sha2-nistp256@openssh\.com)\s+(AAAA[0-9A-Za-z+/=]+)")
SSH_TYPES = {b"ssh-rsa": "RSA-SIGNATURE", b"ssh-dss": "DSA", b"ssh-ed25519": "EdDSA", b"ssh-ed448": "EdDSA",
             b"sk-ssh-ed25519@openssh.com": "EdDSA", b"sk-ecdsa-sha2-nistp256@openssh.com": "ECDSA"}
HEADER_TYPES = {"RSA PRIVATE KEY": "RSA", "RSA PUBLIC KEY": "RSA", "EC PRIVATE KEY": "EC", "DSA PRIVATE KEY": "DSA",
                "OPENSSH PRIVATE KEY": None, "PRIVATE KEY": None, "PUBLIC KEY": None, "ENCRYPTED PRIVATE KEY": None,
                "CERTIFICATE": None, "CERTIFICATE REQUEST": None, "X509 CRL": None}

try:  # optional dependency ([pqc] extra)
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import dsa, ec, ed448, ed25519, rsa, x448, x25519
    HAVE_CRYPTOGRAPHY = True
except ImportError:  # pragma: no cover - exercised only without the extra
    HAVE_CRYPTOGRAPHY = False
# Imported separately, so that one module disappearing from a future cryptography release cannot
# switch off all key parsing (finite-field DH is already deprecated there; ML-KEM/ML-DSA are recent).
try:
    from cryptography.hazmat.primitives.asymmetric import dh
except ImportError:  # pragma: no cover
    dh = None
try:
    from cryptography.hazmat.primitives.asymmetric import mldsa, mlkem
except ImportError:  # pragma: no cover - cryptography < 45
    mldsa = mlkem = None


def pem_blocks(data: bytes):
    """Yield (label, body, offset) for each PEM block: a BEGIN marker paired with the next END marker of
    the same label, with no other BEGIN marker in between (a PEM body never contains one).

    The markers are found with bounded regexes (labels of at most 64 characters, no nested
    quantifiers); pairing uses a binary search and a forward `find` that stops at the next BEGIN, so
    the regions scanned do not overlap and the work is O(n log n). The old single regex
    `BEGIN (X)(.*?)END \\1` rescanned to the end of the file for every unterminated BEGIN (quadratic).
    """
    ends: dict[bytes, list[int]] = {}
    for match in PEM_END.finditer(data):
        ends.setdefault(match.group(1), []).append(match.start())
    if not ends:
        return
    cursor = 0
    for match in PEM_BEGIN.finditer(data):
        start = match.start()
        if start < cursor:
            continue  # inside the previous block
        candidates = ends.get(match.group(1))
        if not candidates:
            continue
        after = match.end()
        index = bisect.bisect_left(candidates, after)
        if index == len(candidates):
            continue
        end_start = candidates[index]
        if end_start - after > MAX_PEM_BLOCK or data.find(b"-----BEGIN ", after, end_start) >= 0:
            continue
        yield match.group(1).decode(), data[after:end_start], start
        cursor = end_start


def _line_of(data: bytes, offset: int) -> int:
    return data.count(b"\n", 0, offset) + 1


def key_facts(key) -> tuple[str, int | None, str]:
    """(algorithm, key size, detail) for a cryptography public or private key object."""
    if isinstance(key, (rsa.RSAPublicKey, rsa.RSAPrivateKey)):
        return "RSA", key.key_size, f"RSA {key.key_size}-bit"
    if isinstance(key, (ec.EllipticCurvePublicKey, ec.EllipticCurvePrivateKey)):
        return "EC", key.curve.key_size, f"EC curve {key.curve.name}"
    if isinstance(key, (dsa.DSAPublicKey, dsa.DSAPrivateKey)):
        return "DSA", key.key_size, f"DSA {key.key_size}-bit"
    if isinstance(key, (ed25519.Ed25519PublicKey, ed25519.Ed25519PrivateKey)):
        return "EdDSA", 256, "Ed25519"
    if isinstance(key, (ed448.Ed448PublicKey, ed448.Ed448PrivateKey)):
        return "EdDSA", 456, "Ed448"
    if isinstance(key, (x25519.X25519PublicKey, x25519.X25519PrivateKey)):
        return "X25519", 256, "X25519"
    if isinstance(key, (x448.X448PublicKey, x448.X448PrivateKey)):
        return "X25519", 448, "X448"
    for module, family, sets in ((mldsa, "ML-DSA", (44, 65, 87)), (mlkem, "ML-KEM", (512, 768, 1024))):
        for number in sets if module is not None else ():
            classes = tuple(getattr(module, f"{family.replace('-', '')}{number}{kind}Key", None) for kind in ("Public", "Private"))
            if any(cls is not None and isinstance(key, cls) for cls in classes):
                return family, None, f"{family}-{number}"
    if dh is not None and isinstance(key, (dh.DHPublicKey, dh.DHPrivateKey)):  # last: touching dh warns (deprecated)
        return "DH", key.key_size, f"DH {key.key_size}-bit"
    return "UNKNOWN", None, type(key).__name__


def _certificate_subject(der_bytes: bytes) -> tuple[str, str]:
    """(subject, expiry) via cryptography when it can load the certificate (even if not its key)."""
    if not HAVE_CRYPTOGRAPHY:
        return "(subject not parsed: install the [pqc] extra)", "unknown"
    try:
        cert = x509.load_der_x509_certificate(der_bytes)
        return cert.subject.rfc4514_string(), cert.not_valid_after_utc.date().isoformat()
    except Exception:  # noqa: BLE001
        return "(unreadable subject)", "unknown"


def _pqc_findings(label: str | None, der_bytes: bytes, relative: str, line: int, rule: str) -> list[Finding] | None:
    """Findings for a post-quantum key or certificate recognised by its algorithm OID, else None.

    Reads only the DER structure (no key material), so it works without `cryptography` and for
    algorithms `cryptography` cannot load yet (SLH-DSA)."""
    try:
        if label in (None, "CERTIFICATE"):
            try:
                key_oid, _ = der.certificate_oids(der_bytes)
                if key_oid not in der.PQC_OIDS:
                    return None
                family, parameter_set = der.PQC_OIDS[key_oid]
                subject, expiry = _certificate_subject(der_bytes)
                return [Finding.make(file=relative, line=line, category="certificate", algorithm=family, rule=rule,
                                     detail=f"certificate {subject}; key {parameter_set}; expires {expiry}")]
            except der.DerError:
                if label == "CERTIFICATE":
                    return None
        private = label is not None and "PRIVATE" in label
        oid = der.pkcs8_oid(der_bytes) if private else der.spki_oid(der_bytes)
    except der.DerError:
        return None
    if oid not in der.PQC_OIDS:
        return None
    family, parameter_set = der.PQC_OIDS[oid]
    return [Finding.make(file=relative, line=line, category="private-key" if private else "public-key", algorithm=family,
                         rule=rule, detail=f"{'private' if private else 'public'} key: {parameter_set}")]


def _certificate_findings(cert, relative: str, line: int, rule: str) -> list[Finding]:
    algorithm, size, detail = key_facts(cert.public_key())
    try:
        subject = cert.subject.rfc4514_string()
    except Exception:  # noqa: BLE001 - malformed subjects still get reported by key
        subject = "(unreadable subject)"
    expiry = cert.not_valid_after_utc.date().isoformat()
    signature_algorithm = {"RSA": "RSA-SIGNATURE", "EC": "ECDSA"}.get(algorithm, algorithm)
    findings = [Finding.make(file=relative, line=line, category="certificate", algorithm=signature_algorithm, rule=rule,
                             key_size=size, detail=f"certificate {subject}; key {detail}; expires {expiry}")]
    hash_algorithm = cert.signature_hash_algorithm
    if hash_algorithm is not None and hash_algorithm.name in ("sha1", "md5"):
        findings.append(Finding.make(file=relative, line=line, category="certificate",
                                     algorithm="SHA-1" if hash_algorithm.name == "sha1" else "MD5", rule=rule + "-hash",
                                     detail=f"certificate {subject} is signed with {hash_algorithm.name.upper()}"))
    return findings


def _pem_findings(label: str, block: bytes, relative: str, line: int) -> list[Finding]:
    rule = "pem-" + label.lower().replace(" ", "-")
    pem = b"-----BEGIN " + label.encode() + b"-----\n" + block.strip() + b"\n-----END " + label.encode() + b"-----\n"
    private = "PRIVATE" in label
    category = "private-key" if private else "public-key"
    if label in ("CERTIFICATE REQUEST", "X509 CRL"):
        return []
    body = der.pem_body(block)
    if body is not None and label in ("CERTIFICATE", "PUBLIC KEY", "PRIVATE KEY"):
        pqc = _pqc_findings(label, body, relative, line, rule)
        if pqc is not None:
            return pqc
    if HAVE_CRYPTOGRAPHY:
        try:
            if label == "CERTIFICATE":
                return _certificate_findings(x509.load_pem_x509_certificate(pem), relative, line, rule)
            if label == "OPENSSH PRIVATE KEY":
                key = serialization.load_ssh_private_key(pem, password=None)
            elif private:
                key = serialization.load_pem_private_key(pem, password=None)
            else:
                key = serialization.load_pem_public_key(pem)
            algorithm, size, detail = key_facts(key)
            return [Finding.make(file=relative, line=line, category=category, algorithm=algorithm, rule=rule,
                                 key_size=size, detail=f"{'private' if private else 'public'} key: {detail}")]
        except (TypeError, ValueError) as error:  # encrypted key, or not parseable
            reason = "encrypted" if "password" in str(error).lower() or "encrypted" in str(error).lower() or label == "ENCRYPTED PRIVATE KEY" else "unparsed"
            algorithm = HEADER_TYPES.get(label) or "RSA"
            return [Finding.make(file=relative, line=line, category=category, algorithm=algorithm, rule=rule,
                                 heuristic=True, detail=f"{label.lower()} ({reason}): key type assumed from the header, review manually")]
        except Exception:  # noqa: BLE001 - never let one malformed block stop the scan
            pass
    algorithm = HEADER_TYPES.get(label)
    if label == "CERTIFICATE":
        return [Finding.make(file=relative, line=line, category="certificate", algorithm="RSA", rule=rule, heuristic=True,
                             detail="certificate not parsed (install the [pqc] extra for details); RSA assumed")]
    return [Finding.make(file=relative, line=line, category=category, algorithm=algorithm or "RSA", rule=rule,
                         heuristic=algorithm is None, detail=f"{label.lower()} (header only)")]


def detect(relative: str, data: bytes, is_text: bool, deadline: float | None = None) -> list[Finding]:
    """Findings for one file. Stops early (raising TimeoutError) once time.monotonic() passes deadline."""
    findings: list[Finding] = []
    if not is_text:
        pqc = _pqc_findings(None, data, relative, 1, "der-certificate")
        if pqc is not None:
            if pqc[0].category == "public-key":
                pqc[0].rule = "der-public-key"
            return pqc
        if HAVE_CRYPTOGRAPHY:
            try:
                return _certificate_findings(x509.load_der_x509_certificate(data), relative, 1, "der-certificate")
            except Exception:  # noqa: BLE001
                try:
                    algorithm, size, detail = key_facts(serialization.load_der_public_key(data))
                    return [Finding.make(file=relative, line=1, category="public-key", algorithm=algorithm,
                                         rule="der-public-key", key_size=size, detail=f"public key: {detail}")]
                except Exception:  # noqa: BLE001
                    return []
        return []
    for label, body, offset in pem_blocks(data):
        if deadline is not None and time.monotonic() > deadline:
            raise TimeoutError
        findings += _pem_findings(label, body, relative, _line_of(data, offset))
    for match in SSH_PUBLIC.finditer(data):
        if deadline is not None and time.monotonic() > deadline:
            raise TimeoutError
        kind = match.group(1)
        line = _line_of(data, match.start(1))
        size, detail = None, kind.decode()
        if kind.startswith(b"ecdsa"):
            algorithm, size = "ECDSA", int(kind[-3:])
        else:
            algorithm = SSH_TYPES[kind]
        if HAVE_CRYPTOGRAPHY and kind in (b"ssh-rsa", b"ssh-dss"):
            try:
                key = serialization.load_ssh_public_key(kind + b" " + match.group(2))
                size = key.key_size
                detail = f"{kind.decode()} {size}-bit"
            except Exception:  # noqa: BLE001
                pass
        findings.append(Finding.make(file=relative, line=line, category="ssh-key", algorithm=algorithm,
                                     rule="ssh-public-key", key_size=size, detail=f"SSH public key: {detail}"))
    return findings
