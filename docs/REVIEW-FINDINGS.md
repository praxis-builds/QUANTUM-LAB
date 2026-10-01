# Review findings: full repository review at `dd01576`

A read-only review of the whole repository, starting from [`REVIEW.md`](REVIEW.md) and [`DECISIONS.md`](DECISIONS.md). Reproductions wrote only to a scratch directory outside the repository, and the tree was clean before and after the review.

**Status (2026-10-01, after the fixes):** the findings below are kept as written at review time; the **Status** columns and the *Status* notes say what happened to each. 17 of the 18 numbered findings are fixed, the code changes each with a regression test; #18 is partly done. Of the 17 Info items, 12 are fixed, 3 are documented without a behaviour change, and 2 are documented and left open. The suite now has 859 tests, all passing with the `[pqc]` extra and liboqs (exit code 0, 135 s). What is still open is collected in [`REVIEW.md`](REVIEW.md#still-open).

- **Test suite:** `pytest` passed 741 tests at `dd01576` (exit code 0, 131 s), with the `[pqc]` extra and liboqs.
- **GitHub Actions:** no run results were pasted, so none are reported. [`REVIEW.md:28`](REVIEW.md) still applies: CI has never run.
- **Severity scale:**
  - **High:** leaks secrets, hangs, or gets the core security verdict wrong.
  - **Medium:** a security gate that fails open, or a false crypto claim in reports.
  - **Low:** limited impact, or a mismatch between the docs and the code.
  - **Info:** worth knowing, no action needed.

| # | Severity | Where | Finding | Status |
|---|---|---|---|---|
| 1 | High | `tools/pq_inventory/model.py:11` | Hard-coded keys and passwords are copied verbatim into `scan.json`, which the sample CI workflow uploads | Fixed in `d1abc87`: evidence is only a `[redacted]` marker (D18) |
| 2 | High | `tools/pq_inventory/detect_keys.py:14` | The PEM regex is quadratic: a crafted 2 MiB file stalls a scan for about 33 min | Fixed in `4a37735`: linear marker pairing, 10 s per-file budget |
| 3 | High | `tools/pq_inventory/walker.py:60-64` | A FIFO, or any other non-regular file, hangs the scan forever | Fixed in `58f6f55`: non-regular files are skipped before opening |
| 4 | High | `tools/pq_inventory/detect_keys.py:35-53` | Real ML-DSA and ML-KEM keys and certificates are reported as UNKNOWN / QUANTUM-WEAKENED | Fixed in `678d253`: recognised by OID, classified OK |
| 5 | Medium | `docs/ci/pq-inventory.yml:24-26` | The sample CI gate lets quantum-broken crypto through, although its comments say it blocks it | Fixed in `b819277`: the sample gates on `quantum-broken` |
| 6 | Medium | `tools/pq_inventory/walker.py:36`, `cli.py:36-37` | Scans that read nothing pass every `--fail-on` gate | Fixed in `ec7e395`: an empty scan exits 3 (D19) |
| 7 | Medium | `tools/pq_inventory/algorithms.py:101-148` | Cipher strings are misparsed: `ECDHE+AESGCM` is read as RSA key transport, and NULL, anon and PSK suites are wrong | Fixed in `3829fa6`: table-driven parser; selectors are heuristic |
| 8 | Medium | `tools/pq_inventory/detect_keys.py:99-104` | A certificate the parser can't read is reported as "RSA assumed", with a wrong install hint | Fixed in `a1636a7`: UNKNOWN with the reason, never "RSA assumed" |
| 9 | Low | `tools/pq_inventory/scanner.py:38` | TLS and OpenSSL directive patterns fire inside source code (false positives not flagged as heuristic) | Fixed in `400e4c8`: directives count only outside source code and docs |
| 10 | Low | `tools/pq_inventory/cli.py:3,67,70,90` | Input errors exit with 1, the "threshold reached" code, instead of the documented 2 | Fixed in `f1b66f8`: input errors exit 2, crashes exit 4 |
| 11 | Low | `src/praxis_quantum_lab/security_lab.py:17` | Without `lessons/` (a wheel install) the whole dashboard fails to start | Fixed in `72c4aae`: the dashboard starts; the tab reports why it is off |
| 12 | Low | `lessons/_pqc.py:21-29` | The liboqs guard can still let `import oqs` download and build liboqs | Fixed in `8b9c5bb`: the guard accepts only what liboqs-python will load |
| 13 | Low | `tools/pq_inventory/reports.py:183-202` | The CBOM has dangling refs, null sizes and uninformative names, including in the committed reports | Fixed in `a789ff7`: refs resolve, no nulls, readable names; demo CBOMs regenerated |
| 14 | Low | `tests/fixtures/generate_pq_inventory_keys.py:50` | A decryptable private key is committed, contrary to D9 and REVIEW.md | Fixed in `0830fa3`: file removed; it remains in git history (D9) |
| 15 | Low | `tools/pq_inventory/detect_keys.py:25,51` | One shared import, plus the FFDH deprecation: key parsing can switch off silently | Fixed in `678d253` (separate import) and `13719d9` (no warning, size kept under warnings-as-errors) |
| 16 | Low | `lessons/14_shor_15.md:27`, `15_shor_21.md:29` | Beauregard's cost is misquoted: it is O(n³ log n) gates, not O(n³) | Fixed in `c75d01b` |
| 17 | Low | `lessons/21_why_errors_matter.md:4` | The definition of depolarizing noise doesn't match Qiskit's channel | Fixed in `c75d01b`, with a test against the Qiskit channel |
| 18 | Low | `lessons/21_why_errors_matter.md:11` and others | One number is unsourced, and some citations come from memory | **Partly** (`c75d01b`): the gate-error figure is labelled an order-of-magnitude assumption; the citations from memory and the quotes are still not checked against the originals |

Info-level items, weak tests and smaller doc mismatches are listed after the detailed findings, each with its own status.

---

## High

### 1. Hard-coded keys and passwords are copied verbatim into `scan.json`, which the sample CI workflow uploads
- **Where:**
  - `tools/pq_inventory/model.py:11` (`_SECRETISH = [A-Za-z0-9+/=_-]{40,}`) and `:15-17` (`redact`) mask only runs of 40 or more such characters.
  - `model.py:43` stores the line as `evidence`.
  - That evidence goes to `scan.json` (`reports.py:39-41`) and is carried into `diff.json` (`cli.py:95`).
  - `docs/ci/pq-inventory.yml:27-32` uploads `pq-report/` as an artifact on every pull request and push (`if: always()`).
- **What's wrong:** the line a crypto rule flags is often exactly where a hard-coded key or password sits, as in `DES3.new(b"…")`. Several kinds of secret survive redaction:
  - 16-byte AES keys in hex (32 characters);
  - 24-character 3DES keys;
  - anything containing `!`, `&` or a space, which covers most passwords.

  The HTML, Markdown and CBOM reports are clean; `scan.json` is not. [`docs/pq-inventory.md:30`](pq-inventory.md) says "Only metadata is reported".
- **How verified:** I scanned a scratch tree of three files.
  - `scan.json` evidence contained `"hunter2-hunter2-hunter2!"`, `b"Sup3rS3cretKey!!24bytes!"` and `partner password: Tr0ub4dor&3` verbatim.
  - `report.html`, `report.md` and `cbom.cdx.json` contained none of them.
  - `redact()` left `bytes.fromhex("00112233445566778899aabbccddeeff")` unchanged. It kept a 39-character run and masked a 40-character one.
- **Suggested fix:**
  - By default, store only the matched API token (for example `DES3.new`) plus the line number. Alternatively, mask every string or bytes literal, and every run of 8 or more hex or base64 characters, before storing.
  - Make full evidence opt-in (`--evidence`, with a warning).
  - Add `redact` tests for short keys and passwords.
  - In the sample workflow, upload only `report.md`, `report.html` and `cbom.cdx.json`, or set a short `retention-days`.

### 2. The PEM regex is quadratic: a crafted 2 MiB file stalls a scan for about 33 min
- **Where:** `tools/pq_inventory/detect_keys.py:14` (`-----BEGIN ([A-Z0-9 ]+)-----\s*(.*?)-----END \1-----`, `re.S`), applied to whole files at `:123`.
- **What's wrong:** for every BEGIN header without a matching END, the lazy `(.*?)` scans to the end of the file, so the cost is O(n²) in the number of headers. Files are scanned one after another, so k crafted files cost k times as much. A pull request can add such files, which matters for the sample CI workflow.
- **How verified:** I timed `PEM_BLOCK.finditer` on repeated `-----BEGIN A-----` lines with no END.

  | Input size | Time |
  |---|---|
  | 25 KB | 0.28 s |
  | 50 KB | 1.13 s |
  | 100 KB | 4.52 s |

  Each doubling of the input quadruples the time. Extrapolated, one 2 MiB file takes about 33 min, and 2 MiB is under the default `--max-file-size` (`walker.py:13`).
- **Suggested fix:**
  - Find BEGIN and END markers in one linear pass, for example `re.finditer(rb"-----(BEGIN|END) ([A-Z0-9 ]{1,64})-----")`.
  - Pair each BEGIN with the next END of the same label, and cap the block length (for example at 64 KiB).
  - Add a regression test: a crafted 2 MiB file scans in under 1 s.

### 3. A FIFO, or any other non-regular file, hangs the scan forever
- **Where:** `tools/pq_inventory/walker.py:56-64`. It calls `path.stat()`, checks the size at `:60` and calls `path.read_bytes()` at `:64`, without checking for a regular file.
- **What's wrong:**
  - A FIFO has `st_size` 0, so it passes the size limit, and `read_bytes()` then blocks forever.
  - Character devices such as `/dev/zero` also report size 0 and take the same path. They would read until memory runs out.
  - Git cannot store FIFOs or devices, so a fresh CI checkout is safe. Local scans of live trees are not: home directories, `/etc`, container roots, `/`.
- **How verified:** I scanned a scratch tree holding `a.py` and a `mkfifo` pipe. `timeout 10 python -m pq_inventory scan …` was killed with exit code 124. The device case is inferred from the same code path; I did not run it.
- **Suggested fix:**
  - Skip anything that is not `stat.S_ISREG` and log it as "not a regular file".
  - Open with `O_NONBLOCK | O_NOFOLLOW` and read at most `max_bytes + 1` bytes, so the limit also holds for files that grow during the scan.
  - Add a test with `os.mkfifo`.

### 4. Real ML-DSA and ML-KEM keys and certificates are reported as UNKNOWN / QUANTUM-WEAKENED
- **Where:**
  - `tools/pq_inventory/detect_keys.py:35-53`: `key_facts` has no ML-DSA or ML-KEM branch and falls through to `"UNKNOWN"` at `:53`.
  - `tools/pq_inventory/algorithms.py:75` classifies unknown names as QUANTUM-WEAKENED, "unrecognised algorithm: review manually".
- **What's wrong:** the keys and certificates that a migration produces (FIPS 203/204) are flagged, while source code that calls ML-KEM or ML-DSA is rated OK (`01abf3d`). As a result:
  - a fully migrated repository fails `--fail-on quantum-weakened`;
  - the reports and the CBOM list these assets as "UNKNOWN".
- **How verified:** with cryptography 50.0.2 I generated an ML-DSA-65 public key, an ML-KEM-768 public key and a self-signed ML-DSA-65 certificate. All three were reported with algorithm `UNKNOWN`, `key_size` null and risk QUANTUM-WEAKENED. Their details read "public key: MLDSA65PublicKey", "public key: MLKEM768PublicKey" and "certificate CN=pq.test.invalid; key MLDSA65PublicKey".
- **Suggested fix:**
  - Import `mldsa` and `mlkem` in their own optional `try`.
  - Map their keys to `ML-DSA` and `ML-KEM` with the parameter set (44/65/87 and 512/768/1024), classified OK.
  - Map unknown SPKI OIDs (SLH-DSA, composite) through an OID table instead of returning UNKNOWN.
  - Add tests with keys generated at run time (D9).

## Medium

### 5. The sample CI gate lets quantum-broken crypto through, although its comments say it blocks it
- **Where:** `docs/ci/pq-inventory.yml:1` ("fail a pull request that introduces quantum-broken or weak crypto") and `:24` ("Exit code 1 if any finding is QUANTUM-BROKEN or CLASSICALLY-BROKEN"), against `:26` (`--fail-on classically-broken`).
- **What's wrong:** `--fail-on X` means "X or worse" ([`pq-inventory.md:14`](pq-inventory.md)). This gate therefore fails only on CLASSICALLY-BROKEN findings, and RSA or ECC passes. Anyone who copies the sample gets a weaker gate than the comment promises. `README.md:48` uses `--fail-on quantum-broken`.
- **How verified:** I scanned a tree containing only the committed EC P-256 public key, which is QUANTUM-BROKEN. `--fail-on classically-broken` exited 0; `--fail-on quantum-broken` exited 1.
- **Suggested fix:** use `--fail-on quantum-broken`, keeping the diff-based variant for migrations, or correct both comments.

### 6. Scans that read nothing pass every `--fail-on` gate
- **Where:**
  - `tools/pq_inventory/walker.py:36-38`: a symlinked root is skipped entirely.
  - `tools/pq_inventory/cli.py:36-37`: `--max-file-size` and `--max-files` accept 0 and negative values.
  - `cli.py:81`: the gate only looks at findings.
- **What's wrong:** such a scan reports "0 of 0 scanned files" and exits 0, so the CI gate fails open. Causes include a symlinked checkout path or a typo in a limit.
- **How verified:** both of these runs reported 0 files scanned and exited 0:
  - `scan <symlink to tests/fixtures/pq_inventory> --fail-on quantum-weakened`
  - `scan tests/fixtures/pq_inventory --max-file-size -1 --fail-on quantum-weakened`
- **Suggested fix:**
  - Follow a symlinked *root* explicitly (the user chose it; it is not a link inside the tree), or exit 2 with a message.
  - Validate in argparse that the limits are greater than 0.
  - Exit 2 when `files_scanned == 0`, unless `--allow-empty` is given.

### 7. Cipher strings are misparsed: `ECDHE+AESGCM` is read as RSA key transport, and NULL, anon and PSK suites are wrong
- **Where:**
  - `tools/pq_inventory/algorithms.py:135-148`: `parse_cipher_string` keeps `+`-joined selectors as suite names.
  - `algorithms.py:101-132`: `suite_algorithms` assumes `RSA-KEX` + `RSA-SIGNATURE` whenever it finds no (EC)DHE token (`:114-118`), and has no NULL, eNULL, aNULL, PSK or anonymous handling.
- **What's wrong:** I confirmed each case below by calling the functions directly.

  | Input | Reported | Problem |
  |---|---|---|
  | `EECDH+AESGCM`, `ECDHE+AESGCM` | RSA-KEX + RSA-SIGNATURE | An ECDHE-only nginx config is called "RSA key transport … no forward secrecy" |
  | `EECDH+AESGCM:EDH+AESGCM:!aNULL:!MD5` | both selectors returned as suites | Selectors are not suite names |
  | `NULL-SHA256` | QUANTUM-BROKEN only | No encryption at all; this is classically broken |
  | `ADH-AES128-SHA256` | DH, QUANTUM-BROKEN | Anonymous DH allows a trivial MITM; classically broken |
  | `PSK-AES128-GCM-SHA256` | RSA-KEX | There is no RSA in a PSK suite |
  | `aNULL` as a positive token | RSA-KEX | Means "no authentication", not RSA |
- **Suggested fix:**
  - Treat `+` tokens as selector expressions: map the parts (kEECDH/EECDH → ECDH, aRSA → RSA-SIGNATURE, AESGCM → AES-GCM) and mark the result heuristic.
  - Add classes: NULL and eNULL, and aNULL/ADH/AECDH, as CLASSICALLY-BROKEN; PSK and SRP with their own key exchange.
  - Fall back to RSA-KEX only for names in a static list of OpenSSL suites.
  - Add these cases to `test_cipher_suite_parsing`.

### 8. A certificate the parser can't read is reported as "RSA assumed", with a wrong install hint
- **Where:** `tools/pq_inventory/detect_keys.py:81-104`.
  - When a CERTIFICATE block can't be parsed, the exception is caught at `:94-100`.
  - The block is then reported as algorithm `RSA`, flagged heuristic, with "certificate not parsed (install the [pqc] extra for details); RSA assumed" (`:103-104`).
  - A `ValueError` or `TypeError` takes the `:94-98` branch instead, which also falls back to RSA.
- **What's wrong:**
  - The install hint appears even when cryptography is installed.
  - "RSA" is a guess. It is flagged heuristic, but it still counts as QUANTUM-BROKEN in the totals and in `--fail-on`, because `cli.py:47-49` ignores the flag.
  - Any certificate whose key type cryptography cannot load lands here. cryptography 50.0.2 has `mldsa` and `mlkem` modules but no SLH-DSA module, so SLH-DSA or composite certificates should end up here too (expected; not tested with a real one).
- **How verified:** with cryptography 50.0.2 installed, I scanned a certificate with an unsupported SPKI OID (`1.2.840.10045.2.9`; `public_key()` raises `UnsupportedAlgorithm`). It was reported as `RSA`, QUANTUM-BROKEN, with the install hint.
- **Suggested fix:**
  - Show the hint only when `HAVE_CRYPTOGRAPHY` is false.
  - On a parse failure, report the SPKI OID: look it up in a known-OID table, or else report `UNKNOWN` (heuristic).
  - Never assume RSA.

## Low

### 9. TLS and OpenSSL directive patterns fire inside source code (false positives not flagged as heuristic)
- **Where:** `tools/pq_inventory/scanner.py:38` runs `detect_tls` on every text file. The patterns in `detect_configs.py:38-47` only require a line to start with the directive name.
- **What's wrong:** assignments in source code become findings that are not flagged as heuristic, which inflates the counts. The planted corpus, with its 1.00 precision, cannot show this.
- **How verified:** a scratch `settings.py` containing `ssl_ciphers = "ECDHE+AESGCM"` and `default_bits = 4096` produced two QUANTUM-BROKEN findings, neither flagged heuristic:
  - "cipher suite ECDHE+AESGCM = RSA-KEX + RSA-SIGNATURE" (made worse by #7);
  - "new keys default to RSA 4096-bit".
- **Suggested fix:**
  - Run `detect_tls` only on config-like files: `*.conf`, `*.cnf`, nginx, httpd and openssl names.
  - Alternatively, mark matches in known source-code extensions as heuristic.
  - Reject `=` after nginx directives.

### 10. Input errors exit with 1, the "threshold reached" code, instead of the documented 2
- **Where:** `tools/pq_inventory/cli.py:3` and [`pq-inventory.md:14`](pq-inventory.md) promise exit code 2 for usage and input errors. An unhandled exception exits with 1, the same code as "threshold reached", so CI cannot tell a crash from a finding.
- **How verified:** each of these ended in a traceback and exit code 1.

  | Input | Error | Why it escapes |
  |---|---|---|
  | `diff` on a JSON file without `findings` | `KeyError` (`diff.py:16`) | `cli.py:90` catches only OSError and JSONDecodeError |
  | `--systems` with `"z_years": "soon"` | `ValueError` (`roadmap.py:52`) | `roadmap.build` at `cli.py:70` is outside the `try` at `:61-66` |
  | `--out` naming an existing file | `FileExistsError` (`cli.py:67`) | Not caught |
- **Suggested fix:**
  - Add one top-level handler that maps `OSError`, `ValueError`, `KeyError` and `TypeError` to exit code 2 with a one-line message.
  - Validate the shape of `scan.json` in `diff.load` and the config types in `load_config`.
  - Add a test for each case.

### 11. Without `lessons/` (a wheel install) the whole dashboard fails to start
- **Where:**
  - `src/praxis_quantum_lab/security_lab.py:17` sets `LESSONS_DIR = parents[2] / "lessons"`.
  - `preload()` (`:37-40`) runs inside `preload_simulators` (`dashboard_server.py:424`), which `make_server` calls.
- **What's wrong:** when `lessons/` is missing, `make_server` raises an exception. Every tab goes down (Playground, Bell Lab, Observatory), not just the Security Lab. D15 accepts that the dashboard needs a checkout, but this failure mode is worse than D15 describes.
- **How verified:**
  - The built wheel has 45 files, none under `lessons/`.
  - `security_lab.preload()` with `LESSONS_DIR` pointing at a missing directory raises `FileNotFoundError: …/_qkd.py`.
- **Suggested fix:** catch the error in `preload` and disable the three routes (503 with a reason, plus a note in the tab). Alternatively, document "editable install only" in `README.md` and `docs/dashboard.md`.

### 12. The liboqs guard can still let `import oqs` download and build liboqs
- **Where:**
  - `lessons/_pqc.py:21-29` accepts any `liboqs.so*` under `lib/` or `lib64/`, or anything `find_library("oqs")` returns.
  - liboqs-python's loader (`oqs/oqs.py:117-160` in the venv) tries exactly `<dir>/liboqs.so`, plus `find_library`.
  - If that fails, `oqs.py:273` calls `_install_liboqs`, which clones and builds liboqs from GitHub.
- **What's wrong:** the guard passes in two cases where the loader then fails:
  - only a versioned file exists (for example `liboqs.so.9` from a runtime package, with no dev symlink);
  - `liboqs.so` is a dangling link.

  In both cases `import oqs` then auto-installs. D1, [`REVIEW.md:9`](REVIEW.md) ("A guard keeps `import oqs` from ever auto-installing") and the docstring at `_pqc.py:33` all rule this out.
- **How verified:** I pointed `OQS_INSTALL_PATH` at a directory containing only `lib/liboqs.so.9`.
  - `liboqs_library_path()` returned that file.
  - `lib/liboqs.so` does not exist, and `find_library("oqs")` returns `None`, so the loader would reach `_install_liboqs`.
  - I did not run the import itself, because it would go to the network.
- **Suggested fix:**
  - Before importing `oqs`, check what it will actually load: `root/sub/"liboqs.so"` resolves to a file and `ctypes.CDLL` loads it, or `find_library` succeeds.
  - Add a test with a fake directory.

### 13. The CBOM has dangling refs, null sizes and uninformative names, including in the committed reports
- **Where:**
  - `tools/pq_inventory/reports.py:183-189` builds `algorithmRef` and `signatureAlgorithmRef` as `crypto/algorithm/<algorithm>` without a size. Algorithm components, though, get a `-<size>` suffix (`:191-192`).
  - `:185` writes `"size": null` when the key size is unknown.
  - `:202` derives each component's name from `ref.split("/")[2]`.
- **What's wrong:**
  - References point at components that don't exist.
  - `size` can be null, while the CycloneDX 1.6 schema types it as an integer (I am going from memory here; D11 says the CBOM is not validated).
  - Key components are named "public-key" or "private-key", and certificates by a hex fingerprint.
- **How verified:** I checked the committed CBOMs in `examples/warehouse-demo/reports/`.
  - `before/`: 4 dangling refs (`crypto/algorithm/RSA-SIGNATURE`).
  - `after/`: 2 dangling refs (`crypto/algorithm/EdDSA`) and 2 null sizes.
  - Names seen include "public-key" and "5d2f20b9d6f662c2".
- **Suggested fix:**
  - Reference the sized component, or emit an unsized algorithm component for every reference.
  - Omit unknown sizes.
  - Name keys "algorithm-size kind" and certificates by subject.
  - Test that every `*Ref` resolves to a `bom-ref`.
  - The committed reports would need regenerating; I'll do that only with your OK.

### 14. A decryptable private key is committed, contrary to D9 and REVIEW.md
- **Where:**
  - `tests/fixtures/pq_inventory/keys/encrypted_private_key.pem`, whose password (`test-only-password`) is in `tests/fixtures/generate_pq_inventory_keys.py:50`.
  - The D9 heading ([`DECISIONS.md:45`](DECISIONS.md)) and [`REVIEW.md:34`](REVIEW.md) say no private keys are committed.
- **What's wrong:**
  - Anyone can decrypt the key with the committed password. It is a throwaway test key, not a real secret.
  - Secret scanners flag files like this, which is the reason D9 itself gives.
  - D9's body mentions the encrypted key, but its heading and REVIEW.md do not.
- **How verified:** `load_pem_private_key(data, password=b"test-only-password")` returned a 3,072-bit `RSAPrivateKey`.
- **Suggested fix:** generate the key at test time, like the plain keys, and delete the file. Otherwise, keep it and reword D9 and REVIEW.md: "one throwaway, password-encrypted test key; the password is public".

### 15. One shared import, plus the FFDH deprecation: key parsing can switch off silently
- **Where:** `tools/pq_inventory/detect_keys.py:22-28` imports `dh, dsa, ec, ed448, ed25519, rsa, x448, x25519` inside one `try`; `:51` then accesses `dh`.
- **What's wrong:**
  - cryptography 50 warns "Diffie-Hellman over finite fields (FFDH) is deprecated and support will be removed in a future release" every time a key reaches line 51. Every ML-DSA and ML-KEM key does (#4).
  - Once `dh` is removed, the single `ImportError` sets `HAVE_CRYPTOGRAPHY = False`. That silently turns off all key and certificate parsing, leaving only the PEM-header fallback and "RSA assumed".
- **How verified:** scanning the ML-DSA and ML-KEM files with `-W always` printed that `CryptographyDeprecationWarning` six times, from `detect_keys.py:51`.
- **Suggested fix:**
  - Import `dh` separately, setting it to `None` on `ImportError`, and check it last and only if present.
  - Add a test with `dh` hidden.

### 16. Beauregard's cost is misquoted: it is O(n³ log n) gates, not O(n³)
- **Where:** `lessons/14_shor_15.md:27` and `lessons/15_shor_21.md:29` say "2n + 3 qubits and O(n³) gates".
- **What's wrong:** the abstract says "2n+3 qubits and O(n³ lg(n)) elementary quantum gates in a depth of O(n³)" (Beauregard, *QIC* 3(2), 175–185, 2003; arXiv:quant-ph/0205095).
- **How verified:** I fetched the arXiv abstract page.
- **Suggested fix:** write "O(n³ log n) gates, in depth O(n³)".

### 17. The definition of depolarizing noise doesn't match Qiskit's channel
- **Where:** `lessons/21_why_errors_matter.md:4` says "with probability p, the qubits it touched are hit by a random Pauli error". The code uses Qiskit's `depolarizing_error(p, 1|2)` (`lessons/_qec.py:42`).
- **What's wrong:**
  - In Qiskit, with probability p the state is replaced by the maximally mixed state. That is a uniformly random Pauli, *including the identity*.
  - So a real error happens with probability 3p/4 on one qubit and 15p/16 on two.
  - The "(1 − p)^G" rule at line 6 therefore slightly overstates the error rate of what is simulated. That is fine for a rough rule, but the definition is wrong.
- **How verified:**
  - `depolarizing_error(0.1, 1)` has identity weight 0.925, so errors occur with probability 0.075 = 3p/4.
  - `depolarizing_error(0.1, 2)` has error weight 0.09375 = 15p/16.
- **Suggested fix:** "with probability p the qubits are replaced by a completely random state (a real Pauli error with probability 3p/4 for one qubit, 15p/16 for two)".

### 18. One number is unsourced, and some citations come from memory
- **Where and what's wrong:**
  - `lessons/21_why_errors_matter.md:11` gives "p = 10⁻³, a typical error rate for today's best two-qubit gates" with no source or date.
  - These citations come from memory. They are correct as far as I know, but I did not check them against the documents in this review:
    - NIST SP 800-90B (2018), `lessons/29_quantum_randomness.md:29`;
    - Brassard–Høyer–Tapp (1998) and Bernstein (2009), `lessons/20_grover_reality_check.md:36`;
    - NIST SP 800-22 Rev. 1a, `lessons/_qkd.py:172` and `lessons/29_quantum_randomness.py:71`.
  - The quotes in lessons 28–29 that count as checked (Shor–Preskill, NCSC) were read through a summarising web-fetch tool, not compared word for word with the originals.
- **How verified:** I read the pages and the earlier session notes.
- **Suggested fix:**
  - Give a dated source for the gate-error figure, or say "order of magnitude".
  - Check the quotes word for word against the PDFs, or label them as paraphrases.

---

## Info

| Where | Note | Status |
|---|---|---|
| `detect_keys.py:63` | A certificate's signature algorithm is labelled from the *subject's* key. I generated an EC leaf signed by an RSA CA (`sha256WithRSAEncryption`); it was reported as "ECDSA". Use `cert.signature_algorithm_oid`. | Fixed (`f70df55`): a second finding names the issuer's signature scheme when it differs from the key; the CBOM references it. |
| `detect_keys.py:49-50` | X448 keys are labelled `X25519`, with size 448. | Fixed (`f70df55`): named X448. |
| `detect_configs.py:31` | In `HostKeyAlgorithms`/`PubkeyAcceptedAlgorithms`, `ssh-rsa` means RSA with SHA-1. Under D7 that is CLASSICALLY-BROKEN, but it is mapped to RSA-SIGNATURE (QUANTUM-BROKEN). As a key type in `authorized_keys` it is only the key format, so the fix belongs in the directive path. | Fixed (`f70df55`): `ssh-rsa`/`ssh-dss` in these directives also count as SHA-1. |
| `scanner.py:15-17` | `_is_ssh_config` misses `sshd_config.d/*.conf` drop-ins: the name lacks "ssh" and the path lacks "/.ssh/". | Fixed (`f70df55`): "ssh" in any directory name counts. |
| `detect_configs.py:45` | `MinProtocol = TLSv1` flags TLS 1.0 only, but TLS 1.1 is enabled as well. | Fixed (`f70df55`): every version from the minimum up to TLS 1.1 is reported. |
| `detect_source.py:89-90` | Lines over 4,000 characters are truncated (minified JS). This is not mentioned in `docs/pq-inventory.md`. | Documented in `docs/pq-inventory.md` (`f70df55`); behaviour unchanged. |
| `walker.py:68-71` | The NUL-byte test skips UTF-16 text files (common for Windows configs) as "binary file". | Fixed for files with a byte-order mark (`f70df55`). **Open:** UTF-16 without one is still skipped as binary (documented). |
| `walker.py:49-51` | After `--max-files`, the walk continues and every further file goes into `skipped`, which grows without bound in memory and in `scan.json`. | Fixed (`f70df55`): the walk stops with one skipped entry. |
| `scanner.py:24`, `reports.py:48,214` | The root path is recorded as given. An absolute path such as `/home/<user>/…` ends up in `scan.json`, the Markdown header and the CBOM serial number. | Documented, not changed (`f70df55`): the root is recorded as typed; pass a relative path. |
| `reports.py:66,69` | Markdown is not escaped beyond replacing `\|`. A file name with a backtick, or a crafted certificate CN, can inject Markdown (for example a link) into `report.md`. Found by reading the code. | Fixed (`f70df55`): `report.md` and `diff.md` escape text from the scanned tree. |
| `reports.py:33-34` | The headline counts only QUANTUM-BROKEN files as "would break". A file whose only finding is RSA-1024 (CLASSICALLY-BROKEN, also breakable by Shor's algorithm) is left out of that count. | Fixed (`f70df55`): short RSA/DSA/DH keys count as quantum-breakable in the headline. |
| `roadmap.py:55-58` | Overlapping path patterns count a finding in every matching system. I verified this with one finding and the systems `*` and `src/*`: it was counted in both. Not documented. The committed demo is unaffected: per-system sums equal the totals. | Documented, not changed (`f70df55`). |
| `docs/ci/pq-inventory.yml:13,14,22,29` | The scanner is installed from an unpinned git ref, and the actions are pinned by tag. A security gate should pin a commit. | Fixed (`0eca9c1`): actions pinned to commit SHAs, the scanner install takes a commit placeholder. The workflow has still never run. |
| `security.js:93,167` | The UI always sends seed 20260928, so repeated runs give identical results. The API accepts any seed. | **Open:** documented in `docs/dashboard.md` (`ff91491`); the forms still have no seed field (a UI change, not cheap). |
| `security_lab.py:83` | `seed % 100_000` aliasing: seeds s and s + 100,000 share Aer base runs. | **Open:** documented in `docs/dashboard.md` (`ff91491`); not changed, because larger Aer seeds are unverified here. |
| `lessons/c/ml_kem_demo.c:31-39` | The error paths free only `kem`: buffers leak and `secret_key` is not wiped. Harmless in a demo that exits, but the file is presented as a model. | Fixed (`0eca9c1`): one cleanup path frees and wipes. |
| `docs/history/codex-handoff-2026-09-29.md` | Contains two absolute `/home/praxis` paths, which reveal the local username. | Fixed (`0eca9c1`) in the current file; the paths remain in git history. |

## Weak tests

These tests pass but would not catch the problems listed:
- **No-network check** (`tests/test_pq_inventory.py:162-164`): a substring grep over the source. `from socket import create_connection` or `os.popen` would pass it. A runtime guard would be stronger: monkeypatch `socket.socket.connect` and `subprocess.Popen` to raise during a scan. *Status: done (`8afbef7`); a full scan and diff run with connections and process creation patched to raise.*
- **Demo drift test** (`tests/test_warehouse_demo.py:23-25`): compares fingerprint sets only. Risk, replacement, detail, roadmap and the committed `report.md`/`report.html`/CBOM can all drift without a failure. *Status: done (`8afbef7`); every committed report file is compared byte for byte with what the documented commands write.*
- **CBOM test** (`tests/test_pq_inventory.py:195-203`): checks shape only. It does not check that refs resolve or that sizes are integers, which would have caught #13. *Status: done with #13 (`a789ff7`).*
- **Security Lab HTTP happy path** (`tests/test_security_lab.py:110-112`): asserts the status code and one key. The content is checked in the non-HTTP tests, which is acceptable. *Status: done (`8afbef7`); the route's answer must equal the checked function's result.*
- **Missing tests:**
  - no `redact()` unit test (#1);
  - no test with a FIFO (#3) or a crafted PEM file (#2);
  - no ML-DSA or ML-KEM key or certificate (#4);
  - no empty scan under `--fail-on` (#6).

  *Status: all added, the last four with their fixes and the `redact()` test in `8afbef7`.*

## Docs that disagree with the code (small)

*Status: all three fixed in `ff91491`.*

- **`lessons/README.md:43`:** the "Run all their checks" line omits the helper tests `test_qft.py`, `test_shor.py`, `test_grover_n.py`, `test_qec.py` and `test_qkd.py`.
- **`README.md:86-101`:** "Project layout" lists only the original six modules. Missing:
  - modules: `dashboard_server.py`, `circuit_playground.py`, `observatory.py`, `security_lab.py`, `finite_shot_*.py`, `bell_noise_analytics.py`;
  - directories: `lessons/`, `tools/`, `examples/`, `.github/`.
- **`docs/dashboard.md:243`:** "What the tests cover" does not mention `tests/test_security_lab.py`.

## Checked and OK

- **Dashboard:**
  - binds 127.0.0.1 and checks the `Host` header (`dashboard_server.py:279`);
  - fixed route maps for docs, POST and static files (`:18`, `:28`, `:35`); static files come from that map, never from a path join;
  - Security Lab parsers: exact field sets, integers that reject booleans, finite floats and ranges; bodies of 256 bytes at most, a JSON content type, duplicate keys and NaN rejected; a busy server returns 429. All tested in `tests/test_security_lab.py`.
  - The CSP test covers `security.js`, and no dashboard script uses `innerHTML`.
- **Path traversal: none found.**
  - Output files have fixed names inside `--out`.
  - Lesson modules load from a hard-coded name list (`security_lab.py:39`).
  - The walker never follows symlinks, including loops and escapes (tested).
- **Scanner safety:**
  - private-key material never appears in reports (`tests/test_pq_inventory.py:99-121`, plus my check of HTML, Markdown and CBOM above);
  - the HTML report is escaped (tested);
  - the per-line regexes are bounded: the worst I measured was 3.7 ms on a 4,000-character line;
  - the wheel ships `pq_inventory/rules/default_rules.json`.
- **`examples/` holds no real secrets.** It contains only generated public keys and certificates, config files and code. "Password" appears only as SAP parameter names (`login/password_hash_algorithm`) and in token-signing code without key material. `test_demo_contains_no_private_keys` passes.
- **CI:** `setup-python`'s pip cache keys on `pyproject.toml` by default, and the `[pqc]` job is non-blocking (`ci.yml:33`), as documented.
- **Claims:** liboqs's README does call the library intended for research and prototyping, matching `REVIEW.md:43`.
- **Tests:** I found no tautological assertions.

## Not verified

- The CBOM against the official CycloneDX 1.6 schema (D11; no validator is installed). *Still not validated after #13.*
- Reads from character devices (#3) and the actual oqs auto-install (#12). Both are inferred from the code; I did not run them. *Still not run: the fixes are tested with a FIFO, a socket and a fake liboqs directory.*
- Real SLH-DSA or composite certificates (#8). *An SLH-DSA certificate signed with liboqs is now a corpus fixture and is classified OK; composite certificates are still untested.*
- Anything about GitHub Actions: no results were pasted. *Unchanged: CI has still never run.*
