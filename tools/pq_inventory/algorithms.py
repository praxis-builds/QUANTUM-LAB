"""Algorithm knowledge: risk classes, reasons, and recommended replacements.

Risk classes (most to least severe, see SEVERITY):
- CLASSICALLY-BROKEN: weak today, without any quantum computer (MD5, SHA-1, DES, 3DES, RC4,
  RSA below 2048 bits, TLS 1.0/1.1).
- QUANTUM-BROKEN: secure today, broken by Shor's algorithm on a large quantum computer
  (RSA, DSA, DH, ECDH, ECDSA, EdDSA, X25519 ...).
- QUANTUM-WEAKENED: Grover roughly halves the security (AES-128 and other 128-bit keys).
- OK: no known quantum break (AES-256, SHA-256 and up, ML-KEM, ML-DSA, SLH-DSA, ChaCha20).
"""

from __future__ import annotations

import re

CLASSICALLY_BROKEN = "CLASSICALLY-BROKEN"
QUANTUM_BROKEN = "QUANTUM-BROKEN"
QUANTUM_WEAKENED = "QUANTUM-WEAKENED"
OK = "OK"
SEVERITY = {CLASSICALLY_BROKEN: 3, QUANTUM_BROKEN: 2, QUANTUM_WEAKENED: 1, OK: 0}
RISK_ORDER = [CLASSICALLY_BROKEN, QUANTUM_BROKEN, QUANTUM_WEAKENED, OK]

KEM_REPLACEMENT = "ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition"
SIG_REPLACEMENT = "ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots"
HASH_REPLACEMENT = "SHA-256 or SHA-384 (FIPS 180-4) or SHA3-256 (FIPS 202)"
CIPHER_REPLACEMENT = "AES-256-GCM (FIPS 197, SP 800-38D)"

# name -> (risk, why, replacement)
ALGORITHMS: dict[str, tuple[str, str, str]] = {
    "RSA": (QUANTUM_BROKEN, "factoring falls to Shor's algorithm", f"{KEM_REPLACEMENT} for key exchange; {SIG_REPLACEMENT} for signatures"),
    "RSA-SIGNATURE": (QUANTUM_BROKEN, "RSA signatures fall to Shor's algorithm", SIG_REPLACEMENT),
    "RSA-KEX": (QUANTUM_BROKEN, "RSA key transport falls to Shor's algorithm (and has no forward secrecy)", KEM_REPLACEMENT),
    "DSA": (QUANTUM_BROKEN, "discrete logarithms fall to Shor's algorithm", SIG_REPLACEMENT),
    "DH": (QUANTUM_BROKEN, "finite-field Diffie-Hellman falls to Shor's algorithm", KEM_REPLACEMENT),
    "ECDH": (QUANTUM_BROKEN, "elliptic-curve Diffie-Hellman falls to Shor's algorithm", KEM_REPLACEMENT),
    "ECDSA": (QUANTUM_BROKEN, "elliptic-curve signatures fall to Shor's algorithm", SIG_REPLACEMENT),
    "EC": (QUANTUM_BROKEN, "elliptic-curve cryptography falls to Shor's algorithm", f"{KEM_REPLACEMENT} / {SIG_REPLACEMENT}"),
    "EdDSA": (QUANTUM_BROKEN, "Ed25519/Ed448 signatures fall to Shor's algorithm", SIG_REPLACEMENT),
    "X25519": (QUANTUM_BROKEN, "X25519/X448 key agreement falls to Shor's algorithm", KEM_REPLACEMENT),
    "AES-128": (QUANTUM_WEAKENED, "Grover's algorithm roughly halves a 128-bit key's strength", CIPHER_REPLACEMENT),
    "AES-192": (OK, "192-bit key: still about 96 bits against Grover", "AES-256-GCM for margin"),
    "AES-256": (OK, "256-bit key: no known quantum break", "none needed"),
    "AES": (QUANTUM_WEAKENED, "AES with an unknown key size; assume 128 bits until checked", "use 256-bit keys (AES-256-GCM)"),
    "CHACHA20": (OK, "256-bit key: no known quantum break", "none needed"),
    "CAMELLIA-128": (QUANTUM_WEAKENED, "128-bit key: Grover roughly halves its strength", CIPHER_REPLACEMENT),
    "CAMELLIA-256": (OK, "256-bit key", "none needed"),
    "MD5": (CLASSICALLY_BROKEN, "practical collisions since 2004", HASH_REPLACEMENT),
    "SHA-1": (CLASSICALLY_BROKEN, "practical collisions since 2017 (SHAttered); deprecated by NIST", HASH_REPLACEMENT),
    "HMAC-SHA1": (CLASSICALLY_BROKEN, "SHA-1 based; HMAC-SHA1 itself is not known to be broken but SHA-1 is deprecated", "HMAC-SHA-256"),
    "HMAC-MD5": (CLASSICALLY_BROKEN, "MD5 based; deprecated", "HMAC-SHA-256"),
    "SHA-224": (OK, "112-bit collision resistance; acceptable but SHA-256+ preferred", "SHA-256 or SHA-384"),
    "SHA-256": (OK, "no known practical attack; Grover-type attacks leave ample margin", "none needed"),
    "SHA-384": (OK, "no known practical attack", "none needed"),
    "SHA-512": (OK, "no known practical attack", "none needed"),
    "SHA-3": (OK, "no known practical attack", "none needed"),
    "DES": (CLASSICALLY_BROKEN, "56-bit key: brute-forced since 1998", CIPHER_REPLACEMENT),
    "3DES": (CLASSICALLY_BROKEN, "64-bit blocks (Sweet32) and disallowed by NIST after 2023", CIPHER_REPLACEMENT),
    "RC4": (CLASSICALLY_BROKEN, "biased keystream; prohibited in TLS (RFC 7465)", CIPHER_REPLACEMENT),
    "RC2": (CLASSICALLY_BROKEN, "obsolete 64-bit block cipher", CIPHER_REPLACEMENT),
    "TLS1.0": (CLASSICALLY_BROKEN, "deprecated by RFC 8996 (2021)", "TLS 1.3 (TLS 1.2 minimum)"),
    "TLS1.1": (CLASSICALLY_BROKEN, "deprecated by RFC 8996 (2021)", "TLS 1.3 (TLS 1.2 minimum)"),
    "SSLv3": (CLASSICALLY_BROKEN, "broken (POODLE); prohibited by RFC 7568", "TLS 1.3"),
    "SSLv2": (CLASSICALLY_BROKEN, "broken; prohibited by RFC 6176", "TLS 1.3"),
    "TLS1.2": (OK, "acceptable protocol version; the cipher suites decide the risk", "TLS 1.3 where possible"),
    "TLS1.3": (OK, "current protocol version", "none needed"),
    "ML-KEM": (OK, "NIST post-quantum KEM (FIPS 203)", "none needed"),
    "ML-DSA": (OK, "NIST post-quantum signature (FIPS 204)", "none needed"),
    "SLH-DSA": (OK, "NIST post-quantum hash-based signature (FIPS 205)", "none needed"),
    "HYBRID-PQ": (OK, "hybrid post-quantum key exchange (classical + post-quantum)", "none needed"),
}


def classify(algorithm: str, key_size: int | None = None) -> tuple[str, str, str]:
    """(risk, why, replacement) for an algorithm name, adjusting RSA/DSA/DH for short keys."""
    risk, why, replacement = ALGORITHMS.get(algorithm, (QUANTUM_WEAKENED, "unrecognised algorithm: review manually", "review"))
    if algorithm in ("RSA", "RSA-SIGNATURE", "RSA-KEX", "DSA", "DH") and key_size is not None and key_size < 2048:
        return CLASSICALLY_BROKEN, f"{key_size}-bit keys are below NIST's 2048-bit minimum (and Shor breaks every size)", replacement
    return risk, why, replacement


def worst(risks) -> str:
    risks = list(risks)
    return max(risks, key=SEVERITY.__getitem__) if risks else OK


# ----------------------------------------------------------- cipher suite parsing

# OpenSSL / IANA cipher-suite name fragments -> algorithms. Order matters only within each group.
_KX = [("ECDHE", "ECDH"), ("ECDH", "ECDH"), ("DHE", "DH"), ("EDH", "DH"), ("ADH", "DH"), ("DH", "DH")]
_AUTH = [("ECDSA", "ECDSA"), ("RSA", "RSA-SIGNATURE"), ("DSS", "DSA")]
_ENC = [("AES256", "AES-256"), ("AES_256", "AES-256"), ("AES128", "AES-128"), ("AES_128", "AES-128"),
        ("CHACHA20", "CHACHA20"), ("DES-CBC3", "3DES"), ("3DES", "3DES"), ("DES_CBC", "DES"), ("DES-CBC", "DES"),
        ("RC4", "RC4"), ("CAMELLIA256", "CAMELLIA-256"), ("CAMELLIA_256", "CAMELLIA-256"),
        ("CAMELLIA128", "CAMELLIA-128"), ("CAMELLIA_128", "CAMELLIA-128")]
_TLS13 = {"TLS_AES_128_GCM_SHA256": ["AES-128", "SHA-256"], "TLS_AES_256_GCM_SHA384": ["AES-256", "SHA-384"],
          "TLS_CHACHA20_POLY1305_SHA256": ["CHACHA20", "SHA-256"], "TLS_AES_128_CCM_SHA256": ["AES-128", "SHA-256"],
          "TLS_AES_128_CCM_8_SHA256": ["AES-128", "SHA-256"]}
CIPHER_KEYWORDS = {"HIGH", "MEDIUM", "LOW", "DEFAULT", "ALL", "COMPLEMENTOFDEFAULT", "COMPLEMENTOFALL", "SECURE", "PFS"}


def suite_algorithms(suite: str) -> list[str]:
    """Algorithms inside one cipher-suite name such as ECDHE-RSA-AES128-GCM-SHA256 or AES256-SHA."""
    name = suite.strip().upper()
    if name in _TLS13:
        return list(_TLS13[name])
    parts = re.split(r"[-_]", name)
    found: list[str] = []
    kx = next((alg for token, alg in _KX if token in parts), None)
    auth = next((alg for token, alg in _AUTH if token in parts), None)
    if kx:
        found.append(kx)
    if auth:
        found.append(auth)
    if not kx:
        # No (EC)DHE prefix: RSA key transport (e.g. AES256-SHA, RSA-AES128-SHA)
        found.append("RSA-KEX")
        if not auth:
            found.append("RSA-SIGNATURE")
    enc = next((alg for token, alg in _ENC if token in name), None)
    if enc is None and "AES" in parts:
        enc = "AES-128"  # OpenSSL's 'AES-SHA'-style names without a size mean 128-bit
    if enc:
        found.append(enc)
    if name.endswith(("-MD5", "_MD5")):
        found.append("HMAC-MD5")
    elif name.endswith(("-SHA", "_SHA")):
        found.append("HMAC-SHA1")
    elif "SHA384" in name:
        found.append("SHA-384")
    elif "SHA256" in name:
        found.append("SHA-256")
    return found


def parse_cipher_string(value: str) -> list[str]:
    """Cipher-suite names named positively in an OpenSSL/Apache/nginx cipher string or a list.
    Exclusions (!RC4, -DES) and keyword classes (HIGH, DEFAULT ...) are not suites and are skipped."""
    tokens = [t.strip().strip("'\";") for t in re.split(r"[:,\s]+", value) if t.strip()]
    suites = []
    for token in tokens:
        token = token.split("@", 1)[0]  # DEFAULT@SECLEVEL=2 -> DEFAULT (a security-level directive, not a suite)
        if not token or token[0] in "!-+" or "=" in token or token.upper() in CIPHER_KEYWORDS:
            continue
        if token.upper() in ("ECDHE", "EECDH", "EDH", "DHE", "RSA", "ECDSA", "AESGCM", "AES", "SHA", "SHA1", "SHA256", "SHA384", "CHACHA20", "KRSA", "ARSA", "AES256", "AES128"):
            # bare family keywords: selector classes, not suite names
            continue
        suites.append(token)
    return suites
