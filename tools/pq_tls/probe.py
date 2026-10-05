"""Talk to one host: the key-exchange probe (our own ClientHello) and a normal TLS connection
(Python's ssl module) for the negotiated version and the certificate.

Traffic: one ClientHello and the server's first flight, then the connection is closed; plus one
ordinary TLS handshake, which is exactly what a browser opening the site does. Every socket has a
timeout (10 s by default). Nothing is sent after the handshake.
"""

from __future__ import annotations

import os
import socket
import ssl
from dataclasses import asdict, dataclass, field

from . import __version__, mlkem, x25519
from .hello import (GROUP_NAMES, PQ_HYBRID_GROUPS, SECP256R1, X25519, X25519MLKEM768, ProtocolError, ResponseParser,
                    build_client_hello)

HYBRID_NAMES = {GROUP_NAMES[group] for group in PQ_HYBRID_GROUPS}

TIMEOUT = 10.0


@dataclass
class KeyExchangeProbe:
    outcome: str  # server_hello | hello_retry_request | alert | timeout | error
    offered_groups: list[str]
    pq_offered: bool
    selected_group: str | None = None
    server_share_bytes: int | None = None
    tls_version: str | None = None
    alert: str | None = None
    error: str | None = None
    notes: list[str] = field(default_factory=list)


def _group_list(encapsulation_key: bytes | None) -> tuple[list[int], list[tuple[int, bytes]]]:
    shares = [(X25519, x25519.new_public_key())]
    groups = [X25519, SECP256R1]
    if encapsulation_key is not None:
        # RFC 10024: X25519MLKEM768 share = ML-KEM-768 encapsulation key || X25519 share (its own key)
        shares.insert(0, (X25519MLKEM768, encapsulation_key + x25519.new_public_key()))
        groups.insert(0, X25519MLKEM768)
    return groups, shares


def probe_key_exchange(host: str, port: int = 443, *, timeout: float = TIMEOUT,
                       encapsulation_key: bytes | None) -> KeyExchangeProbe:
    """Send one ClientHello and report what the server chose. Never completes the handshake."""
    groups, shares = _group_list(encapsulation_key)
    result = KeyExchangeProbe(outcome="error", offered_groups=[GROUP_NAMES[g] for g in groups],
                              pq_offered=encapsulation_key is not None)
    hello = build_client_hello(host, shares, groups, random=os.urandom(32), session_id=os.urandom(32))
    parser = ResponseParser()
    try:
        with socket.create_connection((host, port), timeout=timeout) as connection:
            connection.settimeout(timeout)
            connection.sendall(hello)
            reply = None
            while reply is None:
                chunk = connection.recv(16384)
                if not chunk:
                    result.error = "the server closed the connection without answering"
                    return result
                reply = parser.feed(chunk)
    except socket.timeout:
        result.outcome, result.error = "timeout", f"no answer within {timeout:g} s"
        return result
    except ProtocolError as error:
        result.error = str(error)
        return result
    except OSError as error:
        result.error = f"{error.__class__.__name__}: {error.strerror or error}"
        return result
    result.outcome, result.tls_version, result.alert = reply.kind, reply.version, reply.alert
    result.selected_group, result.server_share_bytes, result.notes = reply.group_name, reply.share_length, reply.notes
    return result


@dataclass
class ConnectionInfo:
    ok: bool
    tls_version: str | None = None
    cipher: str | None = None
    certificate_key: str | None = None  # e.g. "ECDSA P-256", "RSA 2048"
    certificate_signature: str | None = None  # the issuer's signature algorithm on this certificate
    certificate_verified: bool | None = None
    certificate_subject: str | None = None
    certificate_expires: str | None = None
    error: str | None = None


def describe_certificate(der: bytes) -> dict:
    """Key algorithm and size, the issuer's signature algorithm, subject and expiry of a DER certificate.
    Uses `cryptography` when installed, else the pq_inventory DER reader (names only, no size)."""
    from pq_inventory import der as der_reader

    info = {"certificate_key": None, "certificate_signature": None, "certificate_subject": None, "certificate_expires": None}
    try:
        key_oid, signature_oid = der_reader.certificate_oids(der)
    except der_reader.DerError:
        key_oid = signature_oid = None
    if signature_oid:
        info["certificate_signature"] = der_reader.SIGNATURE_OIDS.get(signature_oid, (None, signature_oid))[1]
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives.asymmetric import dsa, ec, ed448, ed25519, rsa
    except ImportError:
        if key_oid in der_reader.PQC_OIDS:
            info["certificate_key"] = der_reader.PQC_OIDS[key_oid][1]
        elif key_oid:
            info["certificate_key"] = der_reader.CLASSICAL_OIDS.get(key_oid, f"OID {key_oid}") + " (size not read: install cryptography)"
        return info
    try:
        certificate = x509.load_der_x509_certificate(der)
        info["certificate_subject"] = certificate.subject.rfc4514_string()
        info["certificate_expires"] = certificate.not_valid_after_utc.date().isoformat()
        key = certificate.public_key()
    except Exception:  # noqa: BLE001 - e.g. a post-quantum key cryptography cannot load
        if key_oid in der_reader.PQC_OIDS:
            info["certificate_key"] = der_reader.PQC_OIDS[key_oid][1]
        return info
    if isinstance(key, rsa.RSAPublicKey):
        info["certificate_key"] = f"RSA {key.key_size}"
    elif isinstance(key, ec.EllipticCurvePublicKey):
        names = {"secp256r1": "P-256", "secp384r1": "P-384", "secp521r1": "P-521"}
        info["certificate_key"] = f"ECDSA {names.get(key.curve.name, key.curve.name)}"
    elif isinstance(key, ed25519.Ed25519PublicKey):
        info["certificate_key"] = "Ed25519"
    elif isinstance(key, ed448.Ed448PublicKey):
        info["certificate_key"] = "Ed448"
    elif isinstance(key, dsa.DSAPublicKey):
        info["certificate_key"] = f"DSA {key.key_size}"
    elif key_oid in der_reader.PQC_OIDS:
        info["certificate_key"] = der_reader.PQC_OIDS[key_oid][1]
    else:
        info["certificate_key"] = type(key).__name__
    return info


def inspect_connection(host: str, port: int = 443, *, timeout: float = TIMEOUT,
                       context: ssl.SSLContext | None = None) -> ConnectionInfo:
    """An ordinary verified TLS handshake (what a browser does). If verification fails, the error is
    reported and the certificate is read once more without verification, so its algorithm is still known."""
    server_name = host  # for an IP address Python checks the certificate's IP entries and sends no SNI

    def handshake(ctx: ssl.SSLContext) -> ConnectionInfo:
        with socket.create_connection((host, port), timeout=timeout) as raw:
            raw.settimeout(timeout)
            with ctx.wrap_socket(raw, server_hostname=server_name) as tls:
                info = ConnectionInfo(ok=True, tls_version=tls.version(), cipher=(tls.cipher() or (None,))[0])
                der = tls.getpeercert(binary_form=True)
        if der:
            for key, value in describe_certificate(der).items():
                setattr(info, key, value)
        return info

    verified = context or ssl.create_default_context()
    try:
        info = handshake(verified)
        info.certificate_verified = True
        return info
    except ssl.SSLCertVerificationError as error:
        reason = f"certificate not trusted: {error.verify_message or error}"
    except (ssl.SSLError, OSError, ValueError) as error:
        return ConnectionInfo(ok=False, error=f"{error.__class__.__name__}: {getattr(error, 'strerror', None) or error}")
    unverified = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    unverified.check_hostname = False
    unverified.verify_mode = ssl.CERT_NONE
    try:
        info = handshake(unverified)
    except (ssl.SSLError, OSError, ValueError) as error:
        return ConnectionInfo(ok=False, certificate_verified=False, error=f"{reason}; then {error.__class__.__name__}")
    info.certificate_verified = False
    info.error = reason
    return info


CERTIFICATE_NOTE = ("Quantum-vulnerable (Shor's algorithm breaks RSA and elliptic-curve signatures). This is true of "
                    "essentially every web certificate today: post-quantum certificates are not yet issued by public CAs "
                    "or accepted by browsers, so there is nothing to switch to yet.")


def verdict(probe: KeyExchangeProbe, connection: ConnectionInfo) -> dict:
    """The per-host summary: key exchange, certificate, TLS version, one-line recommendation."""
    if probe.outcome in ("server_hello", "hello_retry_request") and probe.selected_group:
        if probe.selected_group in HYBRID_NAMES:
            key_exchange = "PQ-HYBRID"
        elif probe.pq_offered:
            key_exchange = "CLASSICAL"
        else:
            key_exchange = "UNKNOWN"
    else:
        key_exchange = "UNKNOWN"
    if not probe.pq_offered:
        key_exchange_detail = (f"PQ check skipped: no ML-KEM implementation is available here, so only classical groups were "
                               f"offered (the server chose {probe.selected_group or 'nothing'}). Install the [pqc] extra.")
    elif key_exchange == "PQ-HYBRID":
        key_exchange_detail = f"The server chose {probe.selected_group} (ML-KEM-768 + X25519, RFC 10024)."
    elif key_exchange == "CLASSICAL":
        retry = " in a HelloRetryRequest" if probe.outcome == "hello_retry_request" else ""
        key_exchange_detail = (f"Offered X25519MLKEM768 first; the server chose {probe.selected_group}{retry}. Traffic recorded "
                               "today could be decrypted by a future quantum computer.")
    elif probe.outcome == "alert":
        key_exchange_detail = f"The server refused the TLS 1.3 ClientHello ({probe.alert})."
    else:
        key_exchange_detail = f"Probe failed: {probe.error}."
    tls_version = connection.tls_version or probe.tls_version
    if connection.certificate_key:
        certificate = f"{connection.certificate_key}: {CERTIFICATE_NOTE}"
    else:
        certificate = "Not read" + (f" ({connection.error})" if connection.error else "") + f". {CERTIFICATE_NOTE}"
    if key_exchange == "PQ-HYBRID":
        recommendation = "Key exchange is already post-quantum hybrid; keep it, and plan certificate migration once PQ certificates exist."
    elif tls_version and tls_version not in ("TLSv1.3", "TLS 1.3"):
        recommendation = f"Enable TLS 1.3 first ({tls_version} negotiated); hybrid post-quantum key exchange needs it."
    elif key_exchange == "CLASSICAL":
        recommendation = "Enable the hybrid group X25519MLKEM768 (RFC 10024) on the TLS endpoint or CDN to stop harvest-now-decrypt-later."
    elif not probe.pq_offered:
        recommendation = "Re-run with an ML-KEM implementation installed (pip install -e '.[pqc]') to check post-quantum key exchange."
    else:
        recommendation = "Could not determine the key exchange; check that the host serves TLS on this port and re-run."
    return {"key_exchange": key_exchange, "key_exchange_detail": key_exchange_detail, "certificate": certificate,
            "tls_version": tls_version, "recommendation": recommendation}


def check_host(host: str, port: int = 443, *, timeout: float = TIMEOUT, encapsulation_key: bytes | None) -> dict:
    probe = probe_key_exchange(host, port, timeout=timeout, encapsulation_key=encapsulation_key)
    connection = inspect_connection(host, port, timeout=timeout)
    return {"host": host, "port": port, "verdict": verdict(probe, connection),
            "key_exchange_probe": asdict(probe), "connection": asdict(connection)}


def run(hosts: list[str], port: int = 443, *, timeout: float = TIMEOUT, checked_at: str) -> dict:
    """Check every host; one ML-KEM key per run (it is only ever sent, never used)."""
    key = mlkem.encapsulation_key()
    return {
        "tool": "pq_tls", "version": __version__, "checked_at": checked_at,
        "ml_kem": key.source if key else None,
        "pq_check": "performed" if key else "skipped: no ML-KEM implementation (cryptography, liboqs or kyber-py) is available",
        "hosts": [check_host(host, port, timeout=timeout, encapsulation_key=key.key if key else None) for host in hosts],
    }
