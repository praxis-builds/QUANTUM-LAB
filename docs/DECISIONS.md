# Decisions log (final build: program step 8 and showcase features)

Each entry: the decision, the alternatives, and why. Logged as the work happened (2026-09-30).

## D1. Post-quantum library: liboqs-python on a locally built liboqs
- **Decision:** use liboqs-python 0.16.0.1 (the Open Quantum Safe wrapper of the liboqs C library) on liboqs 0.16.0, built as a shared library into `~/_oqs` with `-DOQS_USE_OPENSSL=OFF -DOQS_BUILD_ONLY_LIB=ON`.
- **Alternatives:** the pure-Python kyber-py / dilithium-py (the brief's fallback); liboqs-python's own auto-installer; system OpenSSL 3.5+ (which has ML-KEM natively).
- **Why:** liboqs-python is the preferred option and it works here. Its auto-installer (triggered by `import oqs` when no library is found) failed in this WSL image because the OpenSSL development headers (`libssl-dev`) are missing and installing them needs sudo. liboqs can use its own SHA-3/AES code instead of OpenSSL, so building with `OQS_USE_OPENSSL=OFF` succeeded without root. `~/_oqs` is where liboqs-python looks by default, so no environment variable is needed. The fallback libraries were not needed.
- **Consequence:** `import oqs` would try to clone and build liboqs from GitHub on a machine without it. `lessons/_pqc.py` therefore checks for the shared library *before* importing oqs, so lessons and tests skip cleanly instead.

## D2. Optional extra, core install unchanged
- **Decision:** a `[pqc]` extra in `pyproject.toml` (`liboqs-python==0.16.0.1`, `cryptography==50.0.2`) and `requirements-pqc.lock` for its resolved versions (plus `cffi`, `pycparser`). `requirements.lock` and the core dependencies are untouched.
- **Alternatives:** add both to the core dependencies; unpinned ranges.
- **Why:** the brief requires an optional extra; pins match the repo's existing practice of exact versions.

## D3. Scanner packaging: `tools/pq_inventory` as an installed package
- **Decision:** `tools/` is added to the setuptools package roots and to pytest's `pythonpath`; a `pq-inventory` console script is registered. `python -m pq_inventory` works anywhere in the venv.
- **Alternatives:** a separate repository or `pyproject.toml`; running with `PYTHONPATH=tools`.
- **Why:** the brief asks for `python -m pq_inventory scan ...` under `tools/`. One install keeps the lab and the product together while the scanner keeps its own module boundary (it imports nothing from the lab).

## D4. Rule files are JSON; YAML only if PyYAML is already present
- **Decision:** default and user rules are JSON. A `.yaml` rule file is accepted only when PyYAML is importable; otherwise exit code 2 with a message.
- **Alternatives:** add PyYAML as a dependency.
- **Why:** the only new dependencies allowed are those of Part B. JSON needs nothing and is equally extensible.

## D5. What goes in rules and what goes in code
- **Decision:** source-code API patterns are data (62 regex rules). PEM/DER/SSH key parsing, SSH and TLS directive parsing, and cipher-string decomposition are code.
- **Why:** regexes suit "this call appears on this line"; structured formats need real parsing (certificates, cipher suites split into key exchange, authentication, cipher and MAC) that a regex cannot express robustly.

## D6. Four risk classes, one severity order, `--fail-on` means "this level or worse"
- **Decision:** CLASSICALLY-BROKEN (3) > QUANTUM-BROKEN (2) > QUANTUM-WEAKENED (1) > OK (0). `--fail-on quantum-broken` also fails on classically broken findings. Exit codes: 0 done, 1 threshold reached, 2 usage/input error.
- **Why:** something weak today is more urgent than something weak after a CRQC exists. A CI gate on "quantum-broken" that passed MD5 would be misleading.

## D7. Debatable classifications
- RSA/DSA/DH below 2048 bits → CLASSICALLY-BROKEN (below NIST's minimum), not just QUANTUM-BROKEN.
- Any SHA-1 use, including HMAC-SHA1, → CLASSICALLY-BROKEN. HMAC-SHA1 itself is not known to be broken; the finding's text says so. It is flagged because SHA-1 is deprecated and its presence usually marks old configuration.
- AES whose key size cannot be seen → reported as "AES", QUANTUM-WEAKENED (assume 128-bit until checked).
- A TLS cipher suite is one finding whose algorithm is its most severe component (e.g. `AES256-SHA` → HMAC-SHA1). The full decomposition is in the finding's detail.
- Hybrid PQ groups (X25519MLKEM768, sntrup761x25519) → OK.

## D8. Comments are skipped in source files
- **Decision:** whole-line comments (`#`, `//`, `/*`, `*`, `--`) are not matched in source files.
- **Why:** a comment such as "TODO drop md5" is not a use. The corpus includes such decoys. **Cost:** commented-out code is missed (arguably correct).

## D9. No private keys committed, even test ones
- **Decision:** the committed fixtures contain public keys, certificates and one password-encrypted private key. Tests that need plain private keys generate them at run time in a temporary directory. The fixture generator is `tests/fixtures/generate_pq_inventory_keys.py`.
- **Why:** committed private keys can trip secret scanners on push and model bad hygiene. **Note:** `cryptography` 50 refuses to *create* SHA-1-signed certificates, so the SHA-1 test certificate is made with the `openssl` CLI and its key only ever exists in a temporary directory.

## D10. Fingerprints for `diff`
- **Decision:** a finding's fingerprint hashes file, rule, algorithm, key size, detail, the redacted line text and an occurrence counter, but **not** the line number.
- **Why:** inserting a line above a finding must not turn it into "fixed + new". **Cost:** editing the matched line itself counts as fixed + new.

## D11. CBOM: CycloneDX 1.6-shaped, not schema-validated
- **Decision:** `cbom.cdx.json` uses CycloneDX 1.6 `cryptographic-asset` components with `cryptoProperties` (`assetType` algorithm / certificate / protocol / related-crypto-material, `algorithmProperties.primitive`, `parameterSetIdentifier`, `nistQuantumSecurityLevel`) and `evidence.occurrences` with file and line.
- **Why not validated:** no JSON-schema validator is available without a new dependency. Field names follow my reading of the 1.6 specification. **Unverified:** that every field passes the official schema.

## D12. Default Mosca horizon
- **Decision:** default z = years until 2035, labelled "ASSUMPTION ... a regulatory planning horizon, NOT a forecast". x = 10 and y = 5 are also labelled assumptions, and the reports mark which values are assumed per system.
- **Alternatives:** an expert-survey probability of a CRQC; no default at all.
- **Why:** 2035 comes from a published (draft) NIST document I could cite; I could not verify a survey figure here and did not want to invent one. Users are expected to replace all three numbers.

## D13. Warehouse demo: honest "after" state, reproducible reports
- **Decision:** the migrated copy (`after/`) fixes everything the stack allows today and **keeps** realistic interim choices: an ECDSA certificate, Ed25519 SSH keys, an X25519 TLS fallback, one ECDHE suite for TLS 1.2 clients, SAP's EC-only TLS suites and the unmigrated Java supplier feed. Reports are generated with a fixed `--timestamp`, and `tests/test_warehouse_demo.py` fails if they drift from a fresh scan.
- **Alternatives:** an "after" state with every finding fixed.
- **Why:** a fully green "after" would be fiction. Post-quantum certificates and SSH signature keys are not deployable in this scenario, and vendor or partner dependencies take longer. The diff then shows 5 *new* quantum-broken findings, which the case study explains instead of hiding.

## D14. Roadmap shows "overdue" instead of a start year in the past
- **Decision:** when x + y > z, the report says "now (overdue by N years)" rather than a start year.
- **Why:** "start by 2026" for a system 6 years late understates the urgency.
