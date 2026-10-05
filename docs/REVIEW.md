# Review: final build (program step 8 and showcase features)

Built in one autonomous run on 2026-09-30/10-01, on top of `6c023ee`. Commits `81000a7` … (see `git log`), one per lesson or part, each made only after pytest's own exit code was 0. Nothing was pushed. Every decision is in [`DECISIONS.md`](DECISIONS.md) (D1–D19).

**Updated 2026-10-01 after an independent review.** [`REVIEW-FINDINGS.md`](REVIEW-FINDINGS.md) lists 18 findings and a set of smaller items, each with its status. The sections below describe the repository after those fixes; [What the review changed](#what-the-review-changed) and [Still open](#still-open) are new.

## What was built

| Part | What | Where |
|---|---|---|
| B | Optional `[pqc]` extra: liboqs-python 0.16.0.1 and cryptography 50.0.2, with a lock file. liboqs 0.16.0 is built locally into `~/_oqs` without OpenSSL. A guard keeps `import oqs` from ever auto-installing | `pyproject.toml`, `requirements-pqc.lock`, `lessons/_pqc.py` |
| A | Lessons 30–33: why RSA/ECC must go, ML-KEM, hybrid X25519 + ML-KEM-768 (labelled educational), ML-DSA. A C program calling liboqs, built only if liboqs is present | `lessons/30_…`–`33_…`, `lessons/c/` |
| C | `pq_inventory`, a read-only scanner: 62 source rules (6 languages), PEM/DER/SSH key and certificate parsing (post-quantum keys by OID), SSH/nginx/Apache/OpenSSL config parsing, SAP/AS2 heuristics, four risk classes with NIST replacements, JSON/HTML/Markdown/CycloneDX outputs, `diff`, `--fail-on`, exit codes 0–4, Mosca roadmap, safety limits | `tools/pq_inventory/`, `docs/pq-inventory.md`, `docs/ci/pq-inventory.yml` |
| D | Fictional warehouse app (before / partly migrated after), committed reports and diff, consulting-style case study | `examples/warehouse-demo/`, `docs/case-study.md` |
| E | Dashboard Security Lab tab: BB84, toy RSA break, Grover key search (three validated POST routes reusing lesson code), and a client-side Mosca calculator | `src/praxis_quantum_lab/security_lab.py`, `dashboard_assets/security.js` |
| F | GitHub Actions CI (core job and a non-blocking `[pqc]` job), README top section, program map and scanner usage, lessons index 01–33, CLAUDE.md | `.github/workflows/ci.yml`, `README.md`, `lessons/README.md`, `CLAUDE.md` |

## Key numbers

- **ML-KEM (FIPS 203)**, measured from liboqs: ML-KEM-768 public key 1,184 B, secret key 2,400 B, ciphertext 1,088 B, shared secret 32 B (512: 800/1,632/768; 1024: 1,568/3,168/1,568). Medians on this machine: keygen 21 µs, encapsulate 16 µs, decapsulate 18 µs, against RSA-2048 keygen 41 ms and decrypt 568 µs. A flipped ciphertext bit gives a different secret (implicit rejection).
- **Hybrid:** 1,216 bytes client to server and 1,120 bytes back. An attacker holding only one of the two secrets derives a different key.
- **ML-DSA (FIPS 204):** ML-DSA-65 public key 1,952 B and signature 3,309 B, against 65 B and 71 B for ECDSA P-256. SLH-DSA-SHA2-128s signature 7,856 B. Altered message, flipped signature bit and wrong key all fail.
- **Scanner:** precision 1.00 / recall 1.00 on the planted corpus (24 files, 64 planted findings plus decoys; **optimistic by construction**, see below). 23/23 genuine findings on this repo's own lessons (manual review; recall not measurable).
- **Case study:** before 37 findings (16 classically broken, 17 quantum-broken, 2 weakened); after wave 1, 1 / 11 / 0. Three of five systems overdue under the assumed z = 9 years.
- **Security Lab:** each simulation takes about 0.2–0.3 s (BB84 with 20,000 qubits, RSA N = 21, Grover with 8 iterations on 12 qubits).
- **Tests:** 900 passed and 0 skipped with the `[pqc]` extra and liboqs (2026-10-05), up from 741 before the review. In a core-only virtualenv (`.[dev]`, no cryptography, no liboqs-python): 872 passed, 28 skipped, every skip for the missing `[pqc]` extra (lessons 31–33 and the scanner and case-study tests that need `cryptography`). Both exit code 0. History: 725 / 16 at `dd01576`; 859 / 30 on 2026-10-01, when `markdown` and `jsonschema` were not yet in the `dev` extra. The first core-only re-run found one failing test, since fixed: with liboqs built in `~/_oqs` but liboqs-python absent, a guard test expected `oqs` to import. The C demo test runs in both because liboqs sits in `~/_oqs`; without it, that test skips as well.

## Unverified or only partly verified

- **CI runs and is green.** On GitHub Actions the `ci` workflow has passed on every push since `dd01576`, including both jobs (core, and the non-blocking `[pqc]` job with its liboqs build) on the latest commits. The `pages` workflow builds the static showcase and publishes it at <https://praxis-builds.github.io/QUANTUM-LAB/> (HTTP 200 on 2026-10-01). **Still untested as a workflow:** the sample `docs/ci/pq-inventory.yml`, which is meant to be copied into another repository.
- **NIST IR 8547 dates** (deprecate 2030, disallow 2035): the document is an initial public draft (12 Nov 2024, confirmed on csrc.nist.gov), but I could not read the PDF here. The dates come from consistent secondary summaries.
- **Chrome 131 / November 2024:** the Google Security Blog post (13 Sep 2024) confirms the switch to ML-KEM and codepoint 0x11EC. The exact release number comes from secondary sources.
- **CycloneDX CBOM:** validated on 2026-10-01 against the official CycloneDX 1.6 JSON schema (copies in `tests/fixtures/cyclonedx/`, source commit noted there): the two committed warehouse-demo CBOMs (18 and 15 components) and the corpus CBOM (36 components) have 0 errors, and a control with a null size, an unknown asset type and an unknown field is rejected. The first check was a one-off run in a throwaway environment; since 2026-10-05 `jsonschema` is in the `dev` extra and `tests/test_cbom_schema.py` runs the same check everywhere, CI included. Schema validity says the fields are well-formed, not that every modelling choice is the one a CBOM consumer expects.
- **Fowler et al. ~1% threshold** (lesson 25): flagged in that page as checked only indirectly. **NSA's QKD statement** (lesson 28): nsa.gov refuses automated access, so the quoted sentence was compared word for word with the Internet Archive's copy of the page (28 December 2023); its 26 October 2020 date is still from secondary sources.
- **Timings** are single-machine medians with liboqs built without OpenSSL, and only indicative.
- **Push behaviour:** no private keys are in the tree (D9, enforced by a test), but one throwaway, password-encrypted test key remains in git history (removed in `0830fa3`), and the committed public keys and certificates could still trigger a repository's secret-scanning rules. Not tested.

## Known weaknesses

- **Scanner accuracy is not independently measured.** I wrote the corpus and the rules together, so 1.00/1.00 shows the rules do what they were written for, not real-world accuracy. Known misses: multi-line calls, anything past the first 4,000 characters of a line, hand-written crypto (lesson 16's textbook RSA), operations on existing key objects, run-time AES key sizes (reported as "AES", assumed 128-bit), cipher-class keywords (`HIGH`, `DEFAULT`), UTF-16 files without a byte-order mark, composite certificates. SAP and AS2 findings are heuristic.
- **Classification choices are debatable** (D7): every SHA-1 use, including HMAC-SHA1, is CLASSICALLY-BROKEN; RSA below 2048 bits is CLASSICALLY-BROKEN rather than only QUANTUM-BROKEN; a cipher suite is labelled by its worst component.
- **The Mosca horizon is an assumption** (2035 from a draft NIST document). All x/y/z defaults are labelled as assumptions, but users must replace them.
- **Coupling:** the dashboard imports lesson modules (D15), so renaming a lesson helper can break the Security Lab. This is covered by its tests, not by structure.
- **Lessons 31–33 and the C demo only run with liboqs installed.** The core CI job skips them. The non-blocking `[pqc]` job is the only automated check.
- **liboqs** is described by its authors as a research and prototyping library. Lesson 32's hybrid has no authentication and is not production code.
- **The suite takes about 2.5 minutes** (Aer simulations, the real-server UI runs and the scanner tests).

## What the review changed

One commit per finding, `d1abc87` … `ff91491`, then the follow-up work listed under "Still open" (see `git log`); the per-finding status is in [`REVIEW-FINDINGS.md`](REVIEW-FINDINGS.md).

- **Scanner safety (High):** no source text or literal value reaches any output (evidence is a marker, D18); PEM scanning is linear with a 10-second per-file budget; FIFOs, sockets and devices are skipped before they are opened; ML-KEM, ML-DSA and SLH-DSA keys and certificates are recognised by OID and classified OK.
- **Scanner correctness (Medium):** the sample CI gate blocks QUANTUM-BROKEN as its comments say; a scan that read nothing exits 3 at every `--fail-on` level (D19); cipher strings are parsed with tables, selectors are heuristic; an unreadable key or certificate is UNKNOWN with the reason, never "RSA assumed".
- **Low:** TLS directives count only outside source code and docs; input errors exit 2 and crashes 4, so 1 only means "threshold reached"; the dashboard starts without `lessons/` and the Security Lab says why it is off; the liboqs guard accepts only what liboqs-python will load; the CBOM's references resolve; the encrypted test key is gone from the tree; a DH key no longer prints a deprecation warning or loses its size; Beauregard's cost and the depolarizing definition are corrected in the lessons.
- **Info items:** issuer signature algorithm on certificates, X448, `ssh-rsa` as SHA-1 in SSH directives, `sshd_config.d` drop-ins, `MinProtocol`, UTF-16 with a byte-order mark, a bounded skipped list, Markdown escaping, the headline count, the C demo's error paths, commit-pinned actions in the sample workflow.
- **Tests:** a run-time no-network guard, a byte-for-byte check of every committed demo report, `redact()`, the Security Lab's HTTP answers.
- **Follow-up (same day):** every Security Lab form has a seed field and a New seed button, validated like the API; distinct BB84 seeds never share an Aer run; the citations of review finding 18 were checked against the originals and corrected; the CBOM was validated against the official schema; the suite was re-run in a fresh core-only virtualenv; CI and Pages were confirmed on GitHub.
- **Committed reports:** the warehouse-demo reports were regenerated twice, for D18 (fingerprints) and for finding 13 (the two CBOM files only). The case-study counts did not change.

## Still open

Closed since the first version of this list: CI (green, see above), the Security Lab seed field and the seed aliasing, the core-only re-run, the CBOM schema check, and most of review finding 18.

- **Review finding 18, the remainder.** Checked against the originals on 2026-10-01 and now cited precisely: Shor–Preskill (quote verbatim), the NCSC white paper (three quotes verbatim, 24 March 2020), Brassard–Høyer–Tapp (LATIN'98; arXiv abstract), Bernstein (SHARCS'09; abstract quoted), NIST SP 800-22 Rev. 1a (April 2010; the lab's two tests reproduce its worked examples, now a test). **Not verified letter by letter:** the SP 800-90B abstract (read through a summarising fetch tool, labelled so in lesson 29), and the date of the NSA statement. Citations outside finding 18 (Pironio et al., Brassard–Lütkenhaus–Mor–Sanders, Fowler et al.) were not re-checked.
- **The sample CI workflow** `docs/ci/pq-inventory.yml` has never run; its action SHAs were looked up on GitHub on 2026-10-01.
- ~~The CBOM schema test and the Pages builder test skip~~: closed 2026-10-05, `markdown==3.11` and `jsonschema==4.26.0` are now pinned in the `dev` extra (approved by the owner), so both run here and in CI.
- **Documented rather than changed in the scanner:** the scan root is recorded as typed (an absolute path shows the user name); overlapping roadmap patterns count a finding in each matching system; lines are matched up to 4,000 characters; UTF-16 without a byte-order mark is skipped as binary.
- **Not run:** reads from character devices, the real liboqs auto-install path, composite certificates. Nothing renders the dashboard in a real browser, so the new seed row's layout is unchecked.
- **History:** the removed test key and the two home-directory paths in `docs/history/` remain in earlier commits.

## Decisions (summary; details in DECISIONS.md)
D1 liboqs-python on liboqs built without OpenSSL · D2 `[pqc]` extra with a separate lock · D3 scanner as an installed package · D4 JSON rules (YAML only if PyYAML is present) · D5 regex rules for code, parsers for formats · D6 severity order and `--fail-on` semantics · D7 debatable classifications · D8 comments skipped · D9 no private keys committed (SHA-1 certificate via the openssl CLI) · D10 line-independent fingerprints · D11 CBOM validated once against the official schema, no validator dependency · D12 default Mosca horizon 2035 as a labelled assumption · D13 honest "after" state in the demo · D14 "overdue" wording · D15 Security Lab reuses lesson modules · D16 Mosca in the browser · D17 Security Lab limits · D18 evidence is never stored · D19 an empty scan exits 3.
