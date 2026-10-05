# pq_tls: is this website quantum-safe?

A small command-line check: does a web server already use **hybrid post-quantum key exchange**
(ML-KEM + X25519), and what protects its certificate?

    python -m pq_tls check google.com github.com [--port 443] [--json out.json]

For each host it prints four things:

| Field | What it means |
|---|---|
| Key exchange | **PQ-HYBRID** if the server picked X25519MLKEM768; **CLASSICAL** if it picked x25519 or secp256r1 although X25519MLKEM768 was offered first; **UNKNOWN** if the probe failed or no ML-KEM implementation was available to offer (then it says "PQ check skipped"). |
| TLS version | From a normal TLS handshake with Python's `ssl` module. |
| Certificate | Key algorithm and size (e.g. ECDSA P-256, RSA 2048), stated as quantum-vulnerable. That is true of essentially every web certificate today: public CAs do not issue post-quantum certificates and browsers do not accept them yet, so this line is a fact to track, not a fault of the site. |
| Recommendation | One line: keep hybrid, enable X25519MLKEM768, or enable TLS 1.3 first. |

Why the key exchange matters most: traffic recorded today can be decrypted later by whoever breaks
its key exchange ("harvest now, decrypt later"). A certificate only has to resist forgery while it
is in use, so it can migrate later.

## How it works

1. **Key-exchange probe.** The tool builds a TLS 1.3 ClientHello in pure Python
   (`tools/pq_tls/hello.py`). It offers the groups X25519MLKEM768 (0x11EC), x25519 and secp256r1,
   with key shares for X25519MLKEM768 and x25519. Following RFC 10024 (August 2026, formerly
   draft-ietf-tls-ecdhe-mlkem), the hybrid share is the ML-KEM-768 encapsulation key (1184 bytes)
   followed by an X25519 public key (32 bytes). It reads the ServerHello, or a HelloRetryRequest,
   and reports the group the server chose. The handshake is **not** completed: the connection is
   closed after the server's first answer.
2. **Normal connection.** A verified TLS handshake through Python's `ssl` module gives the
   negotiated TLS version and the certificate. If verification fails, the error is reported and
   the certificate is read once more without verification, so its algorithm is still known.

The ML-KEM encapsulation key comes from `cryptography` (the `[pqc]` extra), else liboqs through
`lessons/_pqc`, else `kyber-py` if it happens to be installed. If none is available, only classical
groups are offered and the output says plainly that the PQ check was skipped. X25519 is computed in
pure Python (RFC 7748), so the classical check needs no dependency. No key is ever used: the probe
only sends public keys and throws the private halves away.

**Evidence the wire format is right:** on 2026-10-05 three real servers chose X25519MLKEM768 and
answered with a 1120-byte server share, the size RFC 10024 specifies
(`examples/pq-tls/sample-results.json`). A server would reject a malformed hybrid share.

## Safety and limits

- **The same traffic a browser makes.** One ClientHello per host (then the connection is closed)
  and one ordinary TLS handshake. Nothing is sent after the handshake.
- 10-second timeouts on every connection. At most 20 hosts per run.
- Hosts come only from the command line, one DNS name or one IP address each. Ranges
  (`10.0.0.0/24`), wildcards, URLs, `host:port` and address look-alikes are refused, so the tool
  cannot be turned into a scanner. Only check sites you are allowed to test.
- It reports what one server answered from one place at one time. CDNs and load balancers can
  answer differently by region or over time.
- Only TLS 1.3 is offered in the probe (hybrid key exchange needs TLS 1.3). A TLS 1.2-only server
  refuses it; the normal connection then shows the version, and the recommendation is to enable TLS 1.3.
- The probe offers only X25519MLKEM768, x25519 and secp256r1. A server that supports only another
  hybrid group (SecP256r1MLKEM768, SecP384r1MLKEM1024) would answer with a HelloRetryRequest for
  secp256r1 and be reported as CLASSICAL.

## Tests (no network)

`tests/test_pq_tls.py`: X25519 against RFC 7748 and `cryptography`; the ClientHello against a byte
fixture and an independent decoder (hybrid share layout, TLS 1.3 only, no SNI for IP addresses);
ServerHello, HelloRetryRequest, alert and TLS 1.2 replies from byte fixtures built separately from
RFC 8446 (`tests/fixtures/pq_tls/make_fixtures.py`); a fake server in a thread answering PQ,
classical, HRR, alert, garbage, a timeout and a silent close; a real TLS 1.3 server from Python's
`ssl` module on loopback; and the CLI's host limits. A guard fails any test that dials anything
other than loopback.
