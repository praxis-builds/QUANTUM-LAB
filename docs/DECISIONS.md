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
