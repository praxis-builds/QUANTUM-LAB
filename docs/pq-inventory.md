# pq_inventory: cryptography inventory for post-quantum migration

A read-only command-line scanner that answers the first question of any post-quantum migration: **where is our cryptography, and which of it breaks?** It finds algorithms in source code, keys, certificates and configuration. It classifies each finding by quantum risk and recommends the NIST replacement. It produces reports a manager can read, a machine-readable CBOM, and a prioritised roadmap.

## Usage

    pip install -e '.[pqc]'      # 'cryptography' for key/certificate parsing (liboqs is not needed for scanning)
    python -m pq_inventory scan <path> --out <dir> [--systems systems.json] [--rules extra.json] \
        [--formats json,html,md,cbom] [--fail-on quantum-broken] [--max-file-size BYTES] [--max-files N]
    python -m pq_inventory diff <before/scan.json> <after/scan.json> --out <dir> [--fail-on quantum-broken]

Outputs in `--out`: `scan.json` (everything, including the roadmap), `report.html` (self-contained, no external assets, readable by a non-specialist), `report.md`, and `cbom.cdx.json` (CycloneDX 1.6 cryptography bill of materials). `diff` writes `diff.json` and `diff.md` (fixed / new / unchanged, matched by a fingerprint that ignores line numbers).

Exit codes: `0` done; `1` a `--fail-on` threshold was reached (any finding at that level **or more severe**); `2` usage or input error; `3` nothing was scanned (no readable file under the path, e.g. an empty directory, only binaries, or a symlinked root, which is not followed). An empty scan is never a pass, whatever `--fail-on` says. `4` internal error (a bug, never confused with `1`). Malformed inputs (a `scan.json` from elsewhere, a systems config with text where a number belongs) are input errors (`2`), not crashes. A sample CI workflow is in [`docs/ci/pq-inventory.yml`](ci/pq-inventory.yml).

## Risk classes and replacements

| Class | Meaning | Examples | Recommended replacement |
|---|---|---|---|
| CLASSICALLY-BROKEN | weak today, no quantum computer needed | MD5, SHA-1, DES, 3DES, RC4, RSA < 2048 bit, TLS 1.0/1.1 | SHA-256/384, AES-256-GCM, TLS 1.3 |
| QUANTUM-BROKEN | broken by Shor's algorithm | RSA, DSA, DH, ECDH, ECDSA, EdDSA, X25519 | ML-KEM-768 (FIPS 203), hybrid X25519MLKEM768 in transition; ML-DSA-65 (FIPS 204), SLH-DSA (FIPS 205) |
| QUANTUM-WEAKENED | Grover roughly halves the key strength | AES-128 (and AES of unknown size) | AES-256 |
| OK | no known quantum break | AES-256, SHA-256+, ChaCha20, ML-KEM, ML-DSA, SLH-DSA, hybrid PQ groups | none |

Severity order (for `--fail-on`): CLASSICALLY-BROKEN > QUANTUM-BROKEN > QUANTUM-WEAKENED > OK.

## What it detects

- **Source code** (Python, JavaScript/TypeScript, Java/Kotlin, Go, C/C++, C#): library calls for RSA, DSA, DH, EC, Ed25519, X25519, key sizes where they appear in the call, MD5/SHA-1/SHA-2, DES/3DES/RC4, AES with an explicit key length, and post-quantum algorithm names. Whole-line comments are skipped. 62 rules in [`tools/pq_inventory/rules/default_rules.json`](../tools/pq_inventory/rules/default_rules.json).
- **Keys and certificates**: PEM and DER, parsed with `cryptography` (type, size, curve, signature hash, subject, expiry), OpenSSH private keys, SSH public-key lines (`authorized_keys`, `*.pub`, `known_hosts`). When a key or certificate cannot be parsed, its algorithm is taken from the PEM label or the DER algorithm OID (no size); if neither says, it is reported as **UNKNOWN** (heuristic) with the reason, for example an encrypted PKCS#8 key or an unrecognised OID. The algorithm is never guessed. **Post-quantum keys and certificates** (ML-KEM-512/768/1024, ML-DSA-44/65/87, all twelve SLH-DSA parameter sets) are recognised by their NIST algorithm OIDs with a small built-in DER reader, so they are classified OK even without `cryptography`, or when `cryptography` cannot load them (SLH-DSA in version 50). **Only metadata is reported**: no key material and no source text. A finding's `evidence` field is always `[redacted]`: file, line, rule and algorithm locate it (DECISIONS D18).
- **SSH configuration** (files with "ssh" in the name): `KexAlgorithms`, `Ciphers`, `MACs`, `HostKeyAlgorithms`.
- **TLS configuration** (any text file except source code and Markdown/HTML docs, where such lines are assignments or examples): nginx (`ssl_protocols`, `ssl_ciphers`, `ssl_ecdh_curve`), Apache (`SSLProtocol`, `SSLCipherSuite`, `SSLOpenSSLConfCmd Groups`), OpenSSL (`CipherString`, `Ciphersuites`, `MinProtocol`, `Groups`, `default_bits`, `default_md`). Cipher strings are parsed with tables: explicit suites (OpenSSL `ECDHE-RSA-AES128-GCM-SHA256` or IANA `TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256`) are split exactly into key exchange, authentication, cipher and MAC, including NULL encryption, anonymous (aNULL/ADH/AECDH), PSK, SRP and export suites. Selectors such as `EECDH+AESGCM` or `eNULL` are reported as **heuristic** with the algorithms their parts name (what they expand to depends on the OpenSSL build). Exclusions, reorderings, `@` directives and class keywords (`HIGH`, `DEFAULT`) are skipped. A finding's algorithm is the suite's most severe component.
- **Heuristic rules** (flagged `heuristic` in every report): SAP profile parameters (`ssl/ciphersuites`, `login/password_hash_algorithm`, `ssf/ssfapi_hash_alg`), EDI/AS2 partner settings (encryption and signing algorithms), and generic `key_size = 1024`-style settings. These are pattern matches without parsing the product's semantics: confirm them by hand.

### Adding rules
Pass `--rules my_rules.json` (repeatable). The format is `{"rules": [{"id", "files", "pattern", "algorithm" | "algorithm_map" + "map_group", "key_size_group"?, "flags"?, "category"?, "heuristic"?}]}`. `files` takes suffixes (`.py`), exact names (`DEFAULT.PFL`) or `*`. YAML rule files are accepted only if PyYAML happens to be installed (it is not a dependency of this project).

## Migration roadmap (Mosca)
`--systems systems.json` groups findings into systems and ranks them with Mosca's inequality **x + y > z** (M. Mosca, *IEEE Security & Privacy* 16(5), 2018):

    {"assumptions": {"z_years": 9},
     "systems": [{"name": "Customer archive", "paths": ["archive/*"], "data_lifetime_years": 25, "migration_years": 5}]}

Priority tiers: 1 = already weak today; 2 = quantum-broken and at risk (x + y > z); 3 = quantum-broken with slack (with a "start migrating by" year); 4 = Grover-weakened only. **Defaults are labelled assumptions in every report.** By default z = years until 2035, the year NIST IR 8547 (initial public draft, November 2024) proposes for disallowing quantum-vulnerable public-key algorithms: a regulatory planning horizon, *not* a forecast of when a quantum computer will exist. x defaults to 10 years and y to 5.

## Safety
Read-only. No network code (enforced by a test). Nothing is written outside `--out`, and an `--out` inside the scanned tree is excluded from the scan. Symbolic links are never followed (no loops, no escaping the root). Anything that is not a regular file (FIFOs, sockets, devices) is skipped before it is opened and listed under skipped files; files are opened non-blocking and read only up to the size limit, even if their reported size is wrong. Files above 2 MB, binary files (except DER certificates) and more than 50,000 files are skipped, each with the reason recorded. Every detector is linear or line-bounded (PEM blocks are found by pairing BEGIN/END markers, not by one backtracking regex), and each file has a 10-second time budget as a backstop: a file that exceeds it is reported as skipped, never as a partial clean result. Private keys are reported by type, size and path only.

## How good is it? (honest numbers)
- **Planted corpus** (`tests/fixtures/pq_inventory`, 21 files, 60 planted findings plus decoys): precision **1.00**, recall **1.00**. **This is optimistic by construction:** I wrote the corpus and the rules together, so it checks the rules do what they were written for. It is not an independent accuracy estimate. The expected list (`tests/fixtures/pq_inventory_expected.json`) was written by hand from the fixtures, not from scanner output.
- **This repository's own code** (`lessons/`, not written for the scanner): 23 findings, all genuine uses on manual review (precision 23/23). Recall is not measurable without a full manual audit. Known misses there: textbook RSA implemented with plain integers (lesson 16) is invisible to API rules, and operations on an existing key object (`rsa_public.encrypt(...)`) are not reported separately from the key generation.
- **Known weaknesses:** regex rules see one line at a time (multi-line calls can be missed); AES key sizes are often decided at run time and are then reported as "AES" (assumed 128-bit); configuration semantics (SAP, AS2) are heuristic; cipher-class keywords such as `HIGH` or `DEFAULT` are skipped because their contents depend on the OpenSSL version; the CBOM follows the CycloneDX 1.6 cryptography fields as documented but was not validated against the official JSON schema (no validator dependency).
