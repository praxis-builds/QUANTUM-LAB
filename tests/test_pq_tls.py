"""pq_tls: wire format, parsing, verdicts and CLI limits. No network: every connection goes to a
server in this process on 127.0.0.1, and a guard fails the test if anything else is dialled."""

from __future__ import annotations

import contextlib
import datetime
import hashlib
import io
import json
import socket
import ssl
import struct
import sys
import threading
import time
from pathlib import Path

import pytest

from pq_tls import cli, hello, mlkem, probe, x25519

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "pq_tls"
sys.path.insert(0, str(FIXTURES))
import make_fixtures  # noqa: E402


def fixture(name: str) -> bytes:
    return bytes.fromhex((FIXTURES / f"{name}.hex").read_text().strip())


@pytest.fixture(autouse=True)
def loopback_only(monkeypatch):
    real = socket.create_connection

    def guarded(address, *args, **kwargs):
        if address[0] not in ("127.0.0.1", "localhost", "::1"):
            raise AssertionError(f"test tried to reach {address[0]}")
        return real(address, *args, **kwargs)

    monkeypatch.setattr(socket, "create_connection", guarded)


# ------------------------------------------------------------------ primitives and fixtures

def test_x25519_matches_rfc_7748_and_cryptography():
    # RFC 7748 section 6.1, Alice's key pair
    private = bytes.fromhex("77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a")
    assert x25519.public_key(private).hex() == "8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a"
    cx = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.x25519")
    from cryptography.hazmat.primitives import serialization

    for seed in range(8):
        scalar = hashlib.sha256(bytes([seed])).digest()
        expected = cx.X25519PrivateKey.from_private_bytes(scalar).public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        assert x25519.public_key(scalar) == expected


def test_hello_retry_random_is_the_rfc_8446_constant():
    assert hello.HELLO_RETRY_RANDOM == hashlib.sha256(b"HelloRetryRequest").digest()


def test_byte_fixtures_are_what_the_generator_writes():
    for name, data in make_fixtures.fixtures().items():
        assert fixture(name) == data, f"{name}.hex is stale: run tests/fixtures/pq_tls/make_fixtures.py"


def _client_hello_fields(record: bytes) -> dict:
    """An independent decoder (not hello.py) for the parts of the ClientHello that matter."""
    content_type, major, minor, length = struct.unpack("!BBBH", record[:5])
    assert (content_type, major, minor, length) == (22, 3, 1, len(record) - 5)
    body = record[5:]
    assert body[0] == 1 and int.from_bytes(body[1:4], "big") == len(body) - 4
    position = 4 + 2 + 32
    session_length = body[position]
    position += 1 + session_length
    suites_length = struct.unpack("!H", body[position:position + 2])[0]
    suites = [struct.unpack("!H", body[position + 2 + i:position + 4 + i])[0] for i in range(0, suites_length, 2)]
    position += 2 + suites_length
    position += 1 + body[position]  # compression methods
    extensions_end = position + 2 + struct.unpack("!H", body[position:position + 2])[0]
    position += 2
    extensions = {}
    while position < extensions_end:
        kind, size = struct.unpack("!HH", body[position:position + 4])
        extensions[kind] = body[position + 4:position + 4 + size]
        position += 4 + size
    assert position == len(body) == extensions_end
    groups_data = extensions[10][2:]
    shares, data = [], extensions[51][2:]
    while data:
        group, size = struct.unpack("!HH", data[:4])
        shares.append((group, data[4:4 + size]))
        data = data[4 + size:]
    return {"suites": suites, "groups": [struct.unpack("!H", groups_data[i:i + 2])[0] for i in range(0, len(groups_data), 2)],
            "shares": shares, "versions": extensions[43], "sni": extensions.get(0), "session_length": session_length}


def test_client_hello_offers_the_hybrid_share_in_rfc_10024_layout():
    fields = _client_hello_fields(fixture("client_hello_hybrid"))
    assert fields["suites"] == [0x1301, 0x1302, 0x1303] and fields["session_length"] == 32
    assert fields["groups"] == [0x11EC, 0x001D, 0x0017]
    assert fields["versions"] == b"\x02\x03\x04"  # TLS 1.3 only
    assert fields["sni"].endswith(b"example.com")
    (hybrid_group, hybrid), (classical_group, classical) = fields["shares"]
    assert (hybrid_group, len(hybrid)) == (0x11EC, 1216) and (classical_group, len(classical)) == (0x001D, 32)
    # ML-KEM-768 encapsulation key first, then the X25519 share (RFC 10024)
    assert hybrid[:1184] == make_fixtures.filler("mlkem-encapsulation-key", 1184)
    assert hybrid[1184:] == make_fixtures.filler("client-x25519-a", 32)


def test_client_hello_without_ml_kem_offers_classical_groups_only():
    groups, shares = probe._group_list(None)
    record = hello.build_client_hello("example.com", shares, groups, random=bytes(32), session_id=bytes(32))
    fields = _client_hello_fields(record)
    assert fields["groups"] == [0x001D, 0x0017] and [g for g, _ in fields["shares"]] == [0x001D]


def test_client_hello_sends_no_sni_for_an_ip_address():
    groups, shares = probe._group_list(None)
    assert _client_hello_fields(hello.build_client_hello("192.0.2.1", shares, groups, random=bytes(32), session_id=bytes(32)))["sni"] is None


@pytest.mark.parametrize("name,kind,group,version,share", [
    ("server_hello_hybrid", "server_hello", "X25519MLKEM768", "TLS 1.3", 1120),
    ("server_hello_x25519", "server_hello", "x25519", "TLS 1.3", 32),
    ("hello_retry_secp256r1", "hello_retry_request", "secp256r1", "TLS 1.3", None),
    ("server_hello_tls12", "server_hello", None, "TLS 1.2", None),
])
def test_server_replies_parse(name, kind, group, version, share):
    reply = hello.ResponseParser().feed(fixture(name))
    assert (reply.kind, reply.group_name, reply.version, reply.share_length) == (kind, group, version, share)


def test_alert_and_byte_by_byte_feeding():
    assert hello.ResponseParser().feed(fixture("alert_protocol_version")).alert == "protocol_version"
    parser, data = hello.ResponseParser(), fixture("server_hello_hybrid")
    results = [parser.feed(data[i:i + 1]) for i in range(len(data))]
    assert results[:-1] == [None] * (len(data) - 1) and results[-1].group_name == "X25519MLKEM768"


@pytest.mark.parametrize("garbage", [b"HTTP/1.1 400 Bad Request\r\n\r\n", b"\x16\x03\x03\x00\x05\x0b\x00\x00\x01\x00",
                                     b"SSH-2.0-OpenSSH_9.6\r\n"])
def test_non_tls_replies_are_protocol_errors(garbage):
    with pytest.raises(hello.ProtocolError):
        hello.ResponseParser().feed(garbage)


# ------------------------------------------------------------------ a fake server in a thread

class FakeServer:
    """Accepts connections on 127.0.0.1, reads the ClientHello record, then plays `behaviour`."""

    def __init__(self, behaviour):
        self.behaviour, self.received = behaviour, []
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen()
        self.port = self.listener.getsockname()[1]
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        self.listener.settimeout(0.2)
        while not self.stop.is_set():
            try:
                connection, _ = self.listener.accept()
            except OSError:
                continue
            with connection:
                connection.settimeout(5)
                data = b""
                try:
                    while len(data) < 5 or len(data) < 5 + struct.unpack("!H", data[3:5])[0]:
                        chunk = connection.recv(65536)
                        if not chunk:
                            break
                        data += chunk
                    self.received.append(data)
                    self.behaviour(connection)
                except OSError:
                    pass

    def close(self):
        self.stop.set()
        self.thread.join(timeout=5)
        self.listener.close()


@contextlib.contextmanager
def fake_server(behaviour):
    server = FakeServer(behaviour)
    try:
        yield server
    finally:
        server.close()


def send(data: bytes, chunk: int | None = None):
    def behaviour(connection):
        if chunk is None:
            connection.sendall(data)
        else:
            for i in range(0, len(data), chunk):
                connection.sendall(data[i:i + chunk])
                time.sleep(0.001)
        time.sleep(0.1)
    return behaviour


KEY = b"\x07" * 1184  # filler encapsulation key: the fake server never uses it


@pytest.mark.parametrize("name,outcome,group,verdict", [
    ("server_hello_hybrid", "server_hello", "X25519MLKEM768", "PQ-HYBRID"),
    ("server_hello_x25519", "server_hello", "x25519", "CLASSICAL"),
    ("hello_retry_secp256r1", "hello_retry_request", "secp256r1", "CLASSICAL"),
    ("alert_protocol_version", "alert", None, "UNKNOWN"),
])
def test_probe_against_crafted_replies(name, outcome, group, verdict):
    with fake_server(send(fixture(name), chunk=50)) as server:
        result = probe.probe_key_exchange("127.0.0.1", server.port, timeout=3, encapsulation_key=KEY)
    assert (result.outcome, result.selected_group) == (outcome, group)
    assert probe.verdict(result, probe.ConnectionInfo(ok=False))["key_exchange"] == verdict
    sent = _client_hello_fields(server.received[0])
    assert sent["groups"][0] == 0x11EC and sent["shares"][0][1][:1184] == KEY


def test_probe_reports_garbage_timeout_and_silent_close():
    with fake_server(send(b"HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n")) as server:
        garbage = probe.probe_key_exchange("127.0.0.1", server.port, timeout=3, encapsulation_key=KEY)
    assert garbage.outcome == "error" and "not TLS" in garbage.error
    with fake_server(lambda connection: time.sleep(1.5)) as server:
        start = time.monotonic()
        slow = probe.probe_key_exchange("127.0.0.1", server.port, timeout=0.5, encapsulation_key=KEY)
        assert time.monotonic() - start < 1.4
    assert slow.outcome == "timeout"
    with fake_server(lambda connection: None) as server:
        closed = probe.probe_key_exchange("127.0.0.1", server.port, timeout=3, encapsulation_key=KEY)
    assert closed.outcome == "error" and "closed" in closed.error
    for result in (garbage, slow, closed):
        assert probe.verdict(result, probe.ConnectionInfo(ok=False))["key_exchange"] == "UNKNOWN"


def test_nothing_listening_is_an_error_not_a_crash():
    with socket.socket() as placeholder:
        placeholder.bind(("127.0.0.1", 0))
        port = placeholder.getsockname()[1]
    result = probe.probe_key_exchange("127.0.0.1", port, timeout=2, encapsulation_key=None)
    assert result.outcome == "error" and "Connection" in result.error


def test_without_ml_kem_the_pq_check_is_skipped_and_says_so(monkeypatch):
    monkeypatch.setattr(mlkem, "PROVIDERS", ())
    with fake_server(send(fixture("server_hello_x25519"))) as server:
        results = probe.run(["127.0.0.1"], server.port, timeout=2, checked_at="2026-10-05T00:00:00+00:00")
    assert results["ml_kem"] is None and results["pq_check"].startswith("skipped")
    entry = results["hosts"][0]
    assert entry["verdict"]["key_exchange"] == "UNKNOWN" and "PQ check skipped" in entry["verdict"]["key_exchange_detail"]
    assert 0x11EC not in _client_hello_fields(server.received[0])["groups"]


def test_ml_kem_provider_gives_a_768_encapsulation_key():
    key = mlkem.encapsulation_key()
    if key is None:
        pytest.skip("no ML-KEM implementation installed")
    assert len(key.key) == 1184 and key.source


# ------------------------------------------------------------------ a real TLS 1.3 server on loopback

@pytest.fixture()
def local_tls_server(tmp_path):
    pytest.importorskip("cryptography")
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.timezone.utc)
    certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
                   .serial_number(1).not_valid_before(now - datetime.timedelta(days=1)).not_valid_after(now + datetime.timedelta(days=2))
                   .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False).sign(key, hashes.SHA256()))
    cert_file, key_file = tmp_path / "cert.pem", tmp_path / "key.pem"
    cert_file.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_file.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                           serialization.NoEncryption()))  # generated at test time, in tmp_path (D9)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.load_cert_chain(cert_file, key_file)

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    stop = threading.Event()

    def serve():
        listener.settimeout(0.2)
        while not stop.is_set():
            try:
                connection, _ = listener.accept()
            except OSError:
                continue
            try:
                with context.wrap_socket(connection, server_side=True) as tls:
                    tls.settimeout(2)
                    tls.recv(1)
            except (ssl.SSLError, OSError):
                pass

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    yield listener.getsockname()[1], cert_file
    stop.set()
    thread.join(timeout=5)
    listener.close()


def test_real_tls13_server_on_loopback(local_tls_server):
    port, cert_file = local_tls_server
    key = mlkem.encapsulation_key()
    result = probe.probe_key_exchange("localhost", port, timeout=5, encapsulation_key=key.key if key else None)
    # Python's OpenSSL (3.0 here) does not know X25519MLKEM768, ignores that share and picks x25519.
    assert result.outcome == "server_hello" and result.tls_version == "TLS 1.3"
    assert result.selected_group in ("x25519", "X25519MLKEM768")
    untrusted = probe.inspect_connection("localhost", port, timeout=5)
    assert untrusted.ok and untrusted.certificate_verified is False and "not trusted" in untrusted.error
    assert untrusted.certificate_key == "ECDSA P-256" and untrusted.tls_version == "TLSv1.3"
    trusting = ssl.create_default_context(cafile=str(cert_file))
    trusted = probe.inspect_connection("localhost", port, timeout=5, context=trusting)
    assert trusted.certificate_verified is True and trusted.certificate_signature == "ecdsa-with-SHA256"
    summary = probe.verdict(result, trusted)
    assert summary["tls_version"] == "TLSv1.3" and "Quantum-vulnerable" in summary["certificate"]


# ------------------------------------------------------------------ CLI limits and output

@pytest.mark.parametrize("bad", ["10.0.0.0/24", "*.example.com", "1.2.3.4-9", "https://example.com/", "example.com:443",
                                 "a..b", "-bad.example", "a,b", "999.1.1.1"])
def test_cli_refuses_anything_but_single_hosts(bad):
    with pytest.raises(SystemExit) as error, contextlib.redirect_stderr(io.StringIO()):
        cli.main(["check", bad])
    assert error.value.code == 2


def test_cli_refuses_more_than_20_hosts():
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        assert cli.main(["check", *[f"host{i}.example" for i in range(21)]]) == 2
    assert "at most 20" in err.getvalue()


def test_cli_accepts_names_and_addresses():
    for good in ("example.com", "EXAMPLE.com.", "localhost", "192.0.2.1", "2001:db8::1", "[2001:db8::1]"):
        cli.validate_host(good)


def test_cli_writes_json_and_a_table(tmp_path):
    with fake_server(send(fixture("server_hello_hybrid"))) as server:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["check", "127.0.0.1", "127.0.0.1", "--port", str(server.port), "--json", str(tmp_path / "r.json")],
                            timeout=2, now="2026-10-05T00:00:00+00:00")
    assert code == 0
    results = json.loads((tmp_path / "r.json").read_text())
    assert len(results["hosts"]) == 1  # duplicates are checked once
    assert results["checked_at"] == "2026-10-05T00:00:00+00:00" and results["tool"] == "pq_tls"
    if results["ml_kem"]:
        assert results["hosts"][0]["verdict"]["key_exchange"] == "PQ-HYBRID"
    assert "key exchange :" in out.getvalue()
