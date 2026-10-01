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
from dataclasses import dataclass

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
    "NULL-CIPHER": (CLASSICALLY_BROKEN, "no encryption at all: the traffic is plaintext", CIPHER_REPLACEMENT),
    "ANON-KEX": (CLASSICALLY_BROKEN, "anonymous key exchange: the server is not authenticated, so a man-in-the-middle is trivial",
                 "authenticated (EC)DHE, then hybrid ML-KEM, with certificates"),
    "EXPORT": (CLASSICALLY_BROKEN, "export-grade (40/56-bit or 512-bit) cryptography, broken today (FREAK, Logjam)", "TLS 1.3 suites"),
    "PSK": (OK, "pre-shared symmetric key: no public-key step for Shor's algorithm; its strength is the key's length",
            "256-bit PSKs; (EC)DHE-PSK or ML-KEM for forward secrecy"),
    "SRP": (QUANTUM_BROKEN, "SRP is built on discrete logarithms, which Shor's algorithm breaks", KEM_REPLACEMENT),
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
#
# Two kinds of positive token appear in OpenSSL/nginx/Apache cipher strings:
# - explicit suite names (OpenSSL "ECDHE-RSA-AES128-GCM-SHA256" or IANA "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256"),
#   decomposed exactly with the tables below;
# - selectors ("EECDH+AESGCM", "aRSA", "eNULL"), which add every suite matching all their parts. Their
#   contents depend on the OpenSSL build and on later exclusions, so they are reported as heuristic,
#   with the algorithms their parts name.
# Exclusions (!X, -X), reordering (+X), directives (@SECLEVEL=2) and class keywords (HIGH, DEFAULT ...)
# add nothing and are skipped.

_TLS13 = {"TLS_AES_128_GCM_SHA256": ["AES-128", "SHA-256"], "TLS_AES_256_GCM_SHA384": ["AES-256", "SHA-384"],
          "TLS_CHACHA20_POLY1305_SHA256": ["CHACHA20", "SHA-256"], "TLS_AES_128_CCM_SHA256": ["AES-128", "SHA-256"],
          "TLS_AES_128_CCM_8_SHA256": ["AES-128", "SHA-256"]}
CIPHER_KEYWORDS = {"HIGH", "MEDIUM", "LOW", "DEFAULT", "ALL", "COMPLEMENTOFDEFAULT", "COMPLEMENTOFALL", "SECURE", "PFS",
                   "FIPS", "SUITEB128", "SUITEB128ONLY", "SUITEB192", "SSLV2", "SSLV3", "TLSV1", "TLSV1.0", "TLSV1.1",
                   "TLSV1.2", "TLSV1.3"}
# Key-exchange tokens in suite names (OpenSSL and IANA spellings).
_SUITE_KX = {"ECDHE": ["ECDH"], "EECDH": ["ECDH"], "ECDH": ["ECDH"], "DHE": ["DH"], "EDH": ["DH"], "DH": ["DH"],
             "ADH": ["DH", "ANON-KEX"], "AECDH": ["ECDH", "ANON-KEX"], "PSK": ["PSK"], "SRP": ["SRP"]}
_SUITE_AUTH = {"RSA": "RSA-SIGNATURE", "ECDSA": "ECDSA", "DSS": "DSA", "ANON": "ANON-KEX"}
# Bulk ciphers, most specific first (matched as substrings of the part after the key exchange).
_SUITE_ENC = [("CHACHA20", "CHACHA20"), ("AES256", "AES-256"), ("AES_256", "AES-256"), ("AES-256", "AES-256"),
              ("AES128", "AES-128"), ("AES_128", "AES-128"), ("AES-128", "AES-128"),
              ("CAMELLIA256", "CAMELLIA-256"), ("CAMELLIA_256", "CAMELLIA-256"), ("CAMELLIA128", "CAMELLIA-128"),
              ("CAMELLIA_128", "CAMELLIA-128"), ("3DES", "3DES"), ("DES-CBC3", "3DES"), ("DES_CBC3", "3DES"),
              ("DES-CBC", "DES"), ("DES_CBC", "DES"), ("DES40", "DES"), ("RC4", "RC4"), ("RC2", "RC2")]
_SUITE_MAC = {"SHA": "HMAC-SHA1", "MD5": "HMAC-MD5", "SHA256": "SHA-256", "SHA384": "SHA-384"}
_ENC_FIRST = ("AES", "DES", "3DES", "RC4", "RC2", "CAMELLIA", "NULL", "IDEA", "SEED")  # OpenSSL RSA-kx names start here
# Selector keywords (OpenSSL ciphers(1)); "RSA" alone is an alias for kRSA (RSA key exchange).
SELECTORS = {"KEECDH": ["ECDH"], "KECDHE": ["ECDH"], "ECDHE": ["ECDH"], "EECDH": ["ECDH"], "KECDH": ["ECDH"], "ECDH": ["ECDH"],
             "KEDH": ["DH"], "KDHE": ["DH"], "EDH": ["DH"], "DHE": ["DH"], "KDH": ["DH"], "DH": ["DH"],
             "KRSA": ["RSA-KEX"], "RSA": ["RSA-KEX"], "ARSA": ["RSA-SIGNATURE"], "AECDSA": ["ECDSA"], "ECDSA": ["ECDSA"],
             "ADSS": ["DSA"], "DSS": ["DSA"], "ANULL": ["ANON-KEX"], "ADH": ["DH", "ANON-KEX"], "AECDH": ["ECDH", "ANON-KEX"],
             "ENULL": ["NULL-CIPHER"], "NULL": ["NULL-CIPHER"], "EXPORT": ["EXPORT"], "EXP": ["EXPORT"],
             "AESGCM": ["AES"], "AESCCM": ["AES"], "AES": ["AES"], "AES128": ["AES-128"], "AES256": ["AES-256"],
             "AES128GCM": ["AES-128"], "AES256GCM": ["AES-256"], "CHACHA20": ["CHACHA20"], "CAMELLIA128": ["CAMELLIA-128"],
             "CAMELLIA256": ["CAMELLIA-256"], "3DES": ["3DES"], "DES": ["DES"], "RC4": ["RC4"], "MD5": ["HMAC-MD5"],
             "SHA1": ["HMAC-SHA1"], "SHA": ["HMAC-SHA1"], "SHA256": ["SHA-256"], "SHA384": ["SHA-384"],
             "PSK": ["PSK"], "KPSK": ["PSK"], "SRP": ["SRP"], "KSRP": ["SRP"]}


@dataclass
class CipherEntry:
    token: str
    algorithms: list[str]
    heuristic: bool  # True for selectors: what they expand to depends on the OpenSSL build


def _bulk_and_mac(rest: str, separator: str) -> list[str]:
    found = []
    first = rest.split(separator, 1)[0]
    if first == "NULL":
        found.append("NULL-CIPHER")
    else:
        enc = next((name for token, name in _SUITE_ENC if token in rest), None)
        if enc is None and first == "AES":
            enc = "AES-128"  # OpenSSL's size-less AES names (e.g. SRP-AES-128 spells it out; AES-SHA does not)
        if enc:
            found.append(enc)
    mac = _SUITE_MAC.get(rest.rsplit(separator, 1)[-1])
    if mac:
        found.append(mac)
    return found


def suite_algorithms(suite: str) -> list[str]:
    """Algorithms inside one explicit suite name; [] if the name is not recognised."""
    name = suite.strip().upper()
    if name in _TLS13:
        return list(_TLS13[name])
    if name.startswith(("TLS_", "SSL_")) and "_WITH_" in name:
        kx_part, rest = name[4:].split("_WITH_", 1)
        tokens, separator = kx_part.split("_"), "_"
    else:
        tokens, separator, rest = name.split("-"), "-", None
    found: list[str] = []
    if tokens and tokens[0] in ("EXP", "EXP1024", "EXPORT"):
        found.append("EXPORT")
        tokens = tokens[1:]
    if tokens and tokens[-1] in ("EXPORT", "EXPORT1024") and rest is not None:
        found.insert(0, "EXPORT")
        tokens = tokens[:-1]
    kx: list[str] = []
    auth: list[str] = []
    index = 0
    if len(tokens) > 1 and tokens[0] == "RSA" and tokens[1] == "PSK":
        kx, index = ["RSA-KEX", "PSK"], 2
    else:
        while index < len(tokens) and tokens[index] in _SUITE_KX and len(kx) < 2:
            kx += [a for a in _SUITE_KX[tokens[index]] if a not in kx]
            index += 1
        if index < len(tokens) and tokens[index] in _SUITE_AUTH:
            auth.append(_SUITE_AUTH[tokens[index]])
            index += 1
    if rest is None:
        rest = "-".join(tokens[index:])
    elif index < len(tokens):
        return []  # unexpected tokens before _WITH_
    if not rest:
        return []
    if not kx:
        if auth == ["RSA-SIGNATURE"] or (not auth and rest.split(separator, 1)[0].startswith(_ENC_FIRST)):
            kx, auth = ["RSA-KEX"], ["RSA-SIGNATURE"]  # RSA key transport: AES256-SHA, TLS_RSA_WITH_...
        else:
            return []
    auth = [a for a in auth if a not in kx]
    bulk = _bulk_and_mac(rest, separator)
    if not bulk:
        return []
    return found + kx + auth + bulk


def cipher_entries(value: str) -> list[CipherEntry]:
    """Positive entries of an OpenSSL/Apache/nginx cipher string or a comma-separated suite list."""
    entries = []
    for raw in re.split(r"[:,\s]+", value):
        token = raw.strip().strip("'\";").split("@", 1)[0]
        if not token or token[0] in "!-+" or "=" in token or token.upper() in CIPHER_KEYWORDS:
            continue
        if "+" in token or token.upper() in SELECTORS:
            algorithms: list[str] = []
            for part in token.split("+"):
                algorithms += [a for a in SELECTORS.get(part.upper(), []) if a not in algorithms]
            if algorithms:
                entries.append(CipherEntry(token, algorithms, True))
            continue
        algorithms = suite_algorithms(token)
        if algorithms:
            entries.append(CipherEntry(token, algorithms, False))
    return entries


def parse_cipher_string(value: str) -> list[str]:
    """The positive suites and selectors of a cipher string (see cipher_entries)."""
    return [entry.token for entry in cipher_entries(value)]
