"""TLS (nginx, Apache, OpenSSL config) and SSH configuration directives."""

from __future__ import annotations

import re
import time

from .algorithms import SEVERITY, cipher_entries, classify, worst
from .model import Finding

TLS_PROTOCOLS = {"SSLV2": "SSLv2", "SSLV3": "SSLv3", "TLSV1": "TLS1.0", "TLSV1.0": "TLS1.0", "TLSV1.1": "TLS1.1",
                 "TLSV1.2": "TLS1.2", "TLSV1.3": "TLS1.3"}
GROUPS = {"X25519": "X25519", "X448": "X25519", "PRIME256V1": "ECDH", "SECP256R1": "ECDH", "P-256": "ECDH",
          "SECP384R1": "ECDH", "P-384": "ECDH", "SECP521R1": "ECDH", "P-521": "ECDH",
          "X25519MLKEM768": "HYBRID-PQ", "SECP256R1MLKEM768": "HYBRID-PQ", "SECP384R1MLKEM1024": "HYBRID-PQ",
          "MLKEM768": "ML-KEM", "MLKEM1024": "ML-KEM", "FFDHE2048": "DH", "FFDHE3072": "DH", "FFDHE4096": "DH"}
SSH_KEX = {"diffie-hellman-group1-sha1": ["DH", "SHA-1"], "diffie-hellman-group14-sha1": ["DH", "SHA-1"],
           "diffie-hellman-group14-sha256": ["DH"], "diffie-hellman-group16-sha512": ["DH"],
           "diffie-hellman-group18-sha512": ["DH"], "diffie-hellman-group-exchange-sha1": ["DH", "SHA-1"],
           "diffie-hellman-group-exchange-sha256": ["DH"], "ecdh-sha2-nistp256": ["ECDH"], "ecdh-sha2-nistp384": ["ECDH"],
           "ecdh-sha2-nistp521": ["ECDH"], "curve25519-sha256": ["X25519"], "curve25519-sha256@libssh.org": ["X25519"],
           "sntrup761x25519-sha512@openssh.com": ["HYBRID-PQ"], "sntrup761x25519-sha512": ["HYBRID-PQ"],
           "mlkem768x25519-sha256": ["HYBRID-PQ"]}
SSH_CIPHERS = {"3des-cbc": "3DES", "aes128-ctr": "AES-128", "aes128-cbc": "AES-128", "aes128-gcm@openssh.com": "AES-128",
               "aes192-ctr": "AES-192", "aes192-cbc": "AES-192", "aes256-ctr": "AES-256", "aes256-cbc": "AES-256",
               "aes256-gcm@openssh.com": "AES-256", "chacha20-poly1305@openssh.com": "CHACHA20", "arcfour": "RC4",
               "arcfour128": "RC4", "arcfour256": "RC4"}
SSH_MACS = {"hmac-md5": "HMAC-MD5", "hmac-md5-96": "HMAC-MD5", "hmac-md5-etm@openssh.com": "HMAC-MD5",
            "hmac-sha1": "HMAC-SHA1", "hmac-sha1-96": "HMAC-SHA1", "hmac-sha1-etm@openssh.com": "HMAC-SHA1",
            "hmac-sha2-256": "SHA-256", "hmac-sha2-512": "SHA-512", "hmac-sha2-256-etm@openssh.com": "SHA-256",
            "hmac-sha2-512-etm@openssh.com": "SHA-512"}
SSH_HOSTKEYS = {"ssh-rsa": "RSA-SIGNATURE", "rsa-sha2-256": "RSA-SIGNATURE", "rsa-sha2-512": "RSA-SIGNATURE",
                "ssh-dss": "DSA", "ecdsa-sha2-nistp256": "ECDSA", "ecdsa-sha2-nistp384": "ECDSA",
                "ecdsa-sha2-nistp521": "ECDSA", "ssh-ed25519": "EdDSA"}

# directive regexes: (rule id, pattern) -- value in group "v"
TLS_DIRECTIVES = [
    ("nginx-ssl-protocols", re.compile(r"^\s*ssl_protocols\s+(?P<v>[^;#]+);?", re.I)),
    ("nginx-ssl-ciphers", re.compile(r"^\s*ssl_ciphers\s+(?P<v>[^;#]+);?", re.I)),
    ("nginx-ssl-ecdh-curve", re.compile(r"^\s*ssl_ecdh_curve\s+(?P<v>[^;#]+);?", re.I)),
    ("apache-sslprotocol", re.compile(r"^\s*SSLProtocol\s+(?P<v>[^#]+)", re.I)),
    ("apache-sslciphersuite", re.compile(r"^\s*SSLCipherSuite\s+(?:(?:SSL|TLSv1\.3)\s+)?(?P<v>[^#]+)", re.I)),
    ("apache-sslopensslconfcmd-groups", re.compile(r"^\s*SSLOpenSSLConfCmd\s+(?:Groups|Curves)\s+(?P<v>[^#]+)", re.I)),
    ("openssl-cipherstring", re.compile(r"^\s*CipherString\s*=\s*(?P<v>[^#]+)", re.I)),
    ("openssl-ciphersuites", re.compile(r"^\s*Ciphersuites\s*=\s*(?P<v>[^#]+)", re.I)),
    ("openssl-minprotocol", re.compile(r"^\s*MinProtocol\s*=\s*(?P<v>[^#\s]+)", re.I)),
    ("openssl-groups", re.compile(r"^\s*(?:Groups|Curves)\s*=\s*(?P<v>[^#]+)", re.I)),
    ("openssl-default-bits", re.compile(r"^\s*default_bits\s*=\s*(?P<v>\d+)", re.I)),
    ("openssl-default-md", re.compile(r"^\s*default_md\s*=\s*(?P<v>[\w-]+)", re.I)),
]
# Literal prefilter: a file without any of these words cannot match a TLS directive (plain substring search).
TLS_KEYWORDS = ("ssl_protocols", "ssl_ciphers", "ssl_ecdh_curve", "sslprotocol", "sslciphersuite", "sslopensslconfcmd",
                "cipherstring", "ciphersuites", "minprotocol", "groups", "curves", "default_bits", "default_md")
SSH_DIRECTIVES = re.compile(r"^\s*(?P<k>KexAlgorithms|Ciphers|MACs|HostKeyAlgorithms|PubkeyAcceptedAlgorithms|PubkeyAcceptedKeyTypes)\s+(?P<v>\S+)", re.I)
DIGESTS = {"md5": "MD5", "sha1": "SHA-1", "sha224": "SHA-224", "sha256": "SHA-256", "sha384": "SHA-384", "sha512": "SHA-512"}


def _list(value: str) -> list[str]:
    return [t for t in re.split(r"[\s,:]+", value.strip().strip("\"'")) if t]


def _suite_findings(relative: str, line: int, rule: str, raw: str) -> list[Finding]:
    findings = []
    for entry in cipher_entries(raw):
        algorithms = entry.algorithms
        risks = {alg: classify(alg)[0] for alg in algorithms}
        worst_alg = max(algorithms, key=lambda alg: SEVERITY[risks[alg]])
        detail = (f"cipher selector {entry.token} selects {' + '.join(algorithms)} (contents depend on the OpenSSL build)"
                  if entry.heuristic else f"cipher suite {entry.token} = {' + '.join(algorithms)}")
        finding = Finding.make(file=relative, line=line, category="tls-config", algorithm=worst_alg, rule=rule,
                               heuristic=entry.heuristic, detail=detail, evidence=raw)
        finding.risk = worst(risks.values())
        findings.append(finding)
    return findings


def detect_tls(relative: str, text: str, deadline: float | None = None) -> list[Finding]:
    findings: list[Finding] = []
    lowered = text.lower()
    if not any(keyword in lowered for keyword in TLS_KEYWORDS):
        return findings
    for number, line in enumerate(text.splitlines(), start=1):
        if deadline is not None and time.monotonic() > deadline:
            raise TimeoutError
        if line.lstrip().startswith(("#", ";")):
            continue
        for rule, pattern in TLS_DIRECTIVES:
            match = pattern.match(line)
            if not match:
                continue
            value = match.group("v").strip()
            if rule.endswith(("protocols", "sslprotocol", "minprotocol")):
                tokens = [t for t in _list(value) if not t.startswith("-")]
                for token in tokens:
                    name = TLS_PROTOCOLS.get(token.lstrip("+").upper())
                    if name and name not in ("TLS1.2", "TLS1.3"):
                        findings.append(Finding.make(file=relative, line=number, category="tls-config", algorithm=name,
                                                     rule=rule, detail=f"protocol {token.lstrip('+')} enabled", evidence=line))
                if rule == "apache-sslprotocol" and any(t.lower() in ("all", "+all") for t in tokens):
                    excluded = {t.lstrip("-").upper() for t in _list(value) if t.startswith("-")}
                    for old in ("TLSV1", "TLSV1.1"):
                        if old not in excluded:
                            findings.append(Finding.make(file=relative, line=number, category="tls-config",
                                                         algorithm=TLS_PROTOCOLS[old], rule=rule, heuristic=True,
                                                         detail=f"'all' may include {TLS_PROTOCOLS[old].replace('TLS', 'TLS ')} depending on the OpenSSL build",
                                                         evidence=line))
            elif "ciphers" in rule or "ciphersuite" in rule or "cipherstring" in rule:
                findings += _suite_findings(relative, number, rule, value)
            elif "groups" in rule or "curve" in rule:
                for token in _list(value):
                    algorithm = GROUPS.get(token.upper())
                    if algorithm:
                        findings.append(Finding.make(file=relative, line=number, category="tls-config", algorithm=algorithm,
                                                     rule=rule, detail=f"key-exchange group {token}", evidence=line))
            elif rule == "openssl-default-bits":
                bits = int(value)
                findings.append(Finding.make(file=relative, line=number, category="tls-config", algorithm="RSA", rule=rule,
                                             key_size=bits, detail=f"new keys default to RSA {bits}-bit", evidence=line))
            elif rule == "openssl-default-md":
                algorithm = DIGESTS.get(value.lower())
                if algorithm:
                    findings.append(Finding.make(file=relative, line=number, category="tls-config", algorithm=algorithm,
                                                 rule=rule, detail=f"default digest {value}", evidence=line))
    return findings


def detect_ssh(relative: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    tables = {"kexalgorithms": SSH_KEX, "ciphers": SSH_CIPHERS, "macs": SSH_MACS, "hostkeyalgorithms": SSH_HOSTKEYS,
              "pubkeyacceptedalgorithms": SSH_HOSTKEYS, "pubkeyacceptedkeytypes": SSH_HOSTKEYS}
    for number, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("#"):
            continue
        match = SSH_DIRECTIVES.match(line)
        if not match:
            continue
        key = match.group("k").lower()
        table = tables[key]
        for token in match.group("v").lstrip("+-^").split(","):
            mapped = table.get(token.strip())
            if mapped is None:
                continue
            for algorithm in mapped if isinstance(mapped, list) else [mapped]:
                findings.append(Finding.make(file=relative, line=number, category="ssh-config", algorithm=algorithm,
                                             rule=f"ssh-{key}", detail=f"{match.group('k')} {token.strip()}", evidence=line))
    return findings
