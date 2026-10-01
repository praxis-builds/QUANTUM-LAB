"""Keys and certificates: PEM/DER, OpenSSH private keys, SSH public-key lines.

Only metadata is reported (type, size, curve, signature hash, subject, expiry, path). Key material
is never copied into a finding. Parsing uses the optional `cryptography` package; without it the
PEM headers still give the key type.
"""

from __future__ import annotations

import bisect
import re
import time
import warnings

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


INSTALL_HINT = "; install the [pqc] extra for size, subject and expiry"
SIGNATURE_NAME = {"RSA": "RSA-SIGNATURE", "EC": "ECDSA"}  # certificate findings name the signature scheme
WEAK_SIGNATURE_OIDS = {"1.2.840.113549.1.1.5": "SHA-1", "1.2.840.10045.4.1": "SHA-1", "1.2.840.10040.4.3": "SHA-1",
                       "1.2.840.113549.1.1.4": "MD5"}  # sha1WithRSA, ecdsa-with-SHA1, dsa-with-sha1, md5WithRSA
OPENSSH_TYPES = {b"ssh-rsa": "RSA", b"ssh-dss": "DSA", b"ssh-ed25519": "EdDSA", b"ssh-ed448": "EdDSA",
                 b"ecdsa-sha2-nistp256": "EC", b"ecdsa-sha2-nistp384": "EC", b"ecdsa-sha2-nistp521": "EC"}


def _hint() -> str:
    return "" if HAVE_CRYPTOGRAPHY else INSTALL_HINT


def _unknown(relative: str, line: int, rule: str, category: str, detail: str) -> list[Finding]:
    """A key or certificate whose algorithm could not be determined: reported, never guessed."""
    return [Finding.make(file=relative, line=line, category=category, algorithm="UNKNOWN", rule=rule, heuristic=True,
                         detail=detail + _hint())]


def _loaded_certificate(der_bytes: bytes):
    if not HAVE_CRYPTOGRAPHY:
        return None
    try:
        return x509.load_der_x509_certificate(der_bytes)
    except Exception:  # noqa: BLE001 - cryptography rejects some valid-enough DER; the OID reader may still cope
        return None


def _subject_and_expiry(cert) -> tuple[str, str]:
    if cert is None:
        return "(subject not parsed)", "unknown"
    try:
        subject = cert.subject.rfc4514_string()
    except Exception:  # noqa: BLE001
        subject = "(unreadable subject)"
    try:
        expiry = cert.not_valid_after_utc.date().isoformat()
    except Exception:  # noqa: BLE001
        expiry = "unknown"
    return subject, expiry


def _certificate(der_bytes: bytes | None, relative: str, line: int, rule: str) -> list[Finding]:
    """Certificate findings. Order: post-quantum OID; cryptography's full parse; the key OID (classical
    names, no size); otherwise UNKNOWN with the reason. The algorithm is never guessed."""
    if der_bytes is None:
        return _unknown(relative, line, rule, "certificate", "certificate could not be parsed: not valid base64")
    try:
        key_oid, signature_oid = der.certificate_oids(der_bytes)
    except der.DerError as error:
        key_oid = signature_oid = None
        reason = str(error)
    cert = _loaded_certificate(der_bytes)
    subject, expiry = _subject_and_expiry(cert)
    if key_oid in der.PQC_OIDS:
        family, parameter_set = der.PQC_OIDS[key_oid]
        return [Finding.make(file=relative, line=line, category="certificate", algorithm=family, rule=rule,
                             detail=f"certificate {subject}; key {parameter_set}; expires {expiry}{_hint()}")]
    if cert is not None:
        try:
            return _certificate_findings(cert, relative, line, rule)
        except Exception:  # noqa: BLE001 - e.g. UnsupportedAlgorithm for the key; fall back to the OID
            pass
    if key_oid is None:
        return _unknown(relative, line, rule, "certificate", f"certificate could not be parsed ({reason})")
    name = der.CLASSICAL_OIDS.get(key_oid)
    if name is None:
        return _unknown(relative, line, rule, "certificate",
                        f"certificate {subject}; key algorithm OID {key_oid} not recognised; expires {expiry}")
    findings = [Finding.make(file=relative, line=line, category="certificate", algorithm=SIGNATURE_NAME.get(name, name),
                             rule=rule, detail=f"certificate {subject}; key {name} (from its OID){_hint()}")]
    weak = WEAK_SIGNATURE_OIDS.get(signature_oid)
    if weak:
        findings.append(Finding.make(file=relative, line=line, category="certificate", algorithm=weak, rule=rule + "-hash",
                                     detail=f"certificate {subject} is signed with {weak}"))
    return findings


def _openssh_key_type(der_bytes: bytes | None) -> str | None:
    """The key type of an OpenSSH private key, read from its unencrypted public-key part."""
    magic = b"openssh-key-v1\x00"
    if not der_bytes or not der_bytes.startswith(magic):
        return None
    position = len(magic)
    try:
        for _ in range(3):  # ciphername, kdfname, kdfoptions
            position += 4 + int.from_bytes(der_bytes[position:position + 4], "big")
        position += 4 + 4  # number of keys, length of the first public key blob
        length = int.from_bytes(der_bytes[position:position + 4], "big")
        return OPENSSH_TYPES.get(der_bytes[position + 4:position + 4 + length])
    except (IndexError, ValueError):
        return None


def _key_from_oid(label: str, der_bytes: bytes | None) -> str | None:
    if der_bytes is None:
        return None
    try:
        oid = der.pkcs8_oid(der_bytes) if label == "PRIVATE KEY" else der.spki_oid(der_bytes)
    except der.DerError:
        return None
    return der.CLASSICAL_OIDS.get(oid)


def _key(label: str, block: bytes, der_bytes: bytes | None, relative: str, line: int, rule: str) -> list[Finding]:
    """Key findings. Order: post-quantum OID; cryptography; the PEM label or OID (no size); else UNKNOWN."""
    private = "PRIVATE" in label
    category = "private-key" if private else "public-key"
    kind = "private" if private else "public"
    if HAVE_CRYPTOGRAPHY and label != "ENCRYPTED PRIVATE KEY":
        pem = b"-----BEGIN " + label.encode() + b"-----\n" + block.strip() + b"\n-----END " + label.encode() + b"-----\n"
        try:
            if label == "OPENSSH PRIVATE KEY":
                key = serialization.load_ssh_private_key(pem, password=None)
            elif private:
                key = serialization.load_pem_private_key(pem, password=None)
            else:
                key = serialization.load_pem_public_key(pem)
            algorithm, size, detail = key_facts(key)
            if algorithm != "UNKNOWN":
                return [Finding.make(file=relative, line=line, category=category, algorithm=algorithm, rule=rule,
                                     key_size=size, detail=f"{kind} key: {detail}")]
        except Exception:  # noqa: BLE001 - encrypted, malformed or unsupported: use what the structure says
            pass
    name = HEADER_TYPES.get(label) or _key_from_oid(label, der_bytes)
    if label == "OPENSSH PRIVATE KEY":
        name = _openssh_key_type(der_bytes)
    encrypted = label == "ENCRYPTED PRIVATE KEY" or b"ENCRYPTED" in block or (
        label == "OPENSSH PRIVATE KEY" and der_bytes is not None and b"none" not in der_bytes[15:40])
    state = "encrypted " if encrypted else ""
    if name is None:
        why = "the key type is not visible without the password" if encrypted else "the key type could not be read"
        return _unknown(relative, line, rule, category, f"{state}{kind} key: {why}")
    return [Finding.make(file=relative, line=line, category=category, algorithm=name, rule=rule,
                         detail=f"{state}{kind} key: {name} (from its {'PEM label' if HEADER_TYPES.get(label) else 'encoding'}; size not parsed){_hint()}")]


def _pem_findings(label: str, block: bytes, relative: str, line: int) -> list[Finding]:
    rule = "pem-" + label.lower().replace(" ", "-")
    if label in ("CERTIFICATE REQUEST", "NEW CERTIFICATE REQUEST", "X509 CRL"):
        return []
    der_bytes = der.pem_body(block)
    if label in ("CERTIFICATE", "X509 CERTIFICATE", "TRUSTED CERTIFICATE"):
        return _certificate(der_bytes, relative, line, rule)
    if der_bytes is not None and label in ("PUBLIC KEY", "PRIVATE KEY"):
        pqc = _pqc_findings(label, der_bytes, relative, line, rule)
        if pqc is not None:
            return pqc
    if label in HEADER_TYPES or label.endswith("KEY"):
        return _key(label, block, der_bytes, relative, line, rule)
    if label == "DH PARAMETERS":
        return [Finding.make(file=relative, line=line, category="config", algorithm="DH", rule=rule,
                             detail="Diffie-Hellman parameters")]
    return []  # other PEM types (messages, PGP armour ...) carry no key-algorithm claim


def _pqc_findings(label: str | None, der_bytes: bytes, relative: str, line: int, rule: str) -> list[Finding] | None:
    """Findings for a post-quantum public or private key recognised by its algorithm OID, else None.
    Reads only the DER structure (no key material), so it works without `cryptography`."""
    private = label is not None and "PRIVATE" in label
    try:
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
    if algorithm == "UNKNOWN":
        raise ValueError("unsupported key type")
    subject, expiry = _subject_and_expiry(cert)
    findings = [Finding.make(file=relative, line=line, category="certificate", algorithm=SIGNATURE_NAME.get(algorithm, algorithm),
                             rule=rule, key_size=size, detail=f"certificate {subject}; key {detail}; expires {expiry}")]
    try:
        hash_algorithm = cert.signature_hash_algorithm
    except Exception:  # noqa: BLE001 - signature schemes without a separate hash
        hash_algorithm = None
    if hash_algorithm is not None and hash_algorithm.name in ("sha1", "md5"):
        findings.append(Finding.make(file=relative, line=line, category="certificate",
                                     algorithm="SHA-1" if hash_algorithm.name == "sha1" else "MD5", rule=rule + "-hash",
                                     detail=f"certificate {subject} is signed with {hash_algorithm.name.upper()}"))
    return findings


def detect(relative: str, data: bytes, is_text: bool, deadline: float | None = None) -> list[Finding]:
    """Findings for one file. Stops early (raising TimeoutError) once time.monotonic() passes deadline.

    Reading deprecated cryptography is this scanner's job, so the library's deprecation warnings are
    silenced here: they must not reach the user's console, and under warnings-as-errors they must not
    turn a parsed key into a label-only one (cryptography warns whenever a finite-field DH key is touched).
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return _detect(relative, data, is_text, deadline)


def _detect(relative: str, data: bytes, is_text: bool, deadline: float | None) -> list[Finding]:
    findings: list[Finding] = []
    if not is_text:  # DER: a certificate or a public key, recognised by structure; anything else is not reported
        try:
            der.certificate_oids(data)
            return _certificate(data, relative, 1, "der-certificate")
        except der.DerError:
            pass
        pqc = _pqc_findings(None, data, relative, 1, "der-public-key")
        if pqc is not None:
            return pqc
        if HAVE_CRYPTOGRAPHY:
            try:
                algorithm, size, detail = key_facts(serialization.load_der_public_key(data))
                return [Finding.make(file=relative, line=1, category="public-key", algorithm=algorithm,
                                     rule="der-public-key", key_size=size, detail=f"public key: {detail}")]
            except Exception:  # noqa: BLE001
                pass
        name = _key_from_oid("PUBLIC KEY", data)
        if name:
            return [Finding.make(file=relative, line=1, category="public-key", algorithm=name, rule="der-public-key",
                                 detail=f"public key: {name} (from its OID){_hint()}")]
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
