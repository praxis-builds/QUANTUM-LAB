# Case study: post-quantum cryptography readiness for Northwind Warehouse

*A demonstration engagement on a fictional client. The application, its configuration and every key are invented for this repository ([`examples/warehouse-demo/`](../examples/warehouse-demo/README.md)). The method, tooling and numbers are real: every figure below comes from the committed scanner reports.*

## 1. Summary for management

Northwind Warehouse runs an inventory API, a supplier EDI feed, an SAP system, label printing and an SSH bastion. We inventoried the cryptography in their code and configuration. We classified every use by how it fails: already weak today, broken by a future quantum computer, or only weakened by one. Then we ranked the systems by how long their data must stay secret.

- **Before:** 37 findings in 12 files. **16 are weak today** (MD5, SHA-1, 3DES, TLS 1.0/1.1) and **17 would fall to a quantum computer** (RSA, elliptic-curve and Diffie-Hellman key exchange and signatures). 10 of the 12 files contain quantum-vulnerable cryptography.
- **Three systems are already late** under the agreed planning assumption (the 2035 horizon): ERP by 6 years, the supplier EDI feed by 5, and the inventory API by 1. Data they protect today must stay secret beyond the date by which they can realistically be migrated.
- **After the first migration wave:** today's weaknesses fall from **16 to 1** and quantum-vulnerable findings from **17 to 11**. Hybrid post-quantum key exchange is live on the public TLS endpoint and the SSH bastion, and order tokens are signed with ML-DSA.
- **What remains** is mostly outside the client's direct control: public certificates (no deployable post-quantum certificates yet), SAP's TLS stack (vendor dependency), and one supplier integration (partner coordination). These form wave 2 and wave 3.

## 2. Scope and method

| | |
|---|---|
| Scope | 12 files: Python API, Node.js label service, Java supplier feed, nginx, OpenSSL and sshd configuration, two certificates, SSH keys, an SAP profile, an AS2 partner file |
| Tool | `pq_inventory` (this repository), read-only, offline. It reports key and certificate metadata only, never key material |
| Classification | CLASSICALLY-BROKEN (weak today) > QUANTUM-BROKEN (Shor) > QUANTUM-WEAKENED (Grover) > OK, each with a NIST replacement (FIPS 203/204/205, AES-256, SHA-2) |
| Prioritisation | Mosca's inequality, x + y > z: x = years the data must stay secret, y = years to migrate, z = years until a cryptographically relevant quantum computer |
| Planning assumption | **z = 9 years** (2026 to 2035, the year NIST IR 8547's initial public draft proposes for disallowing quantum-vulnerable public-key algorithms). A planning horizon agreed with the client, **not a forecast**. x and y per system come from the client's retention and change-management estimates ([`systems.json`](../examples/warehouse-demo/systems.json)) |

Reports: before ([HTML](../examples/warehouse-demo/reports/before/report.html), [Markdown](../examples/warehouse-demo/reports/before/report.md), [CBOM](../examples/warehouse-demo/reports/before/cbom.cdx.json)), after ([HTML](../examples/warehouse-demo/reports/after/report.html), [Markdown](../examples/warehouse-demo/reports/after/report.md)), and the [progress diff](../examples/warehouse-demo/reports/diff/diff.md).

## 3. Before: what we found

| Risk | Findings | Typical examples |
|---|---:|---|
| CLASSICALLY-BROKEN | 16 | MD5 ETags and label IDs, SHA-1 barcode checksums and supplier fingerprints, 3DES print-job sealing and AS2 encryption, TLS 1.0/1.1 enabled, 3DES/SHA-1 cipher suites, a SHA-1-signed EDI certificate, SAP passwords hashed with salted SHA-1 |
| QUANTUM-BROKEN | 17 | RSA-2048 order-token signing, RSA and ECDSA in the supplier feed, ECDHE and RSA in TLS, DH/ECDH in SSH, RSA certificates and SSH keys, EC-only SAP TLS suites |
| QUANTUM-WEAKENED | 2 | AES-128 for stock snapshots, aes128-ctr in SSH |
| OK | 2 | SHA-256 used correctly in places |

By system, with the planning assumption z = 9 years:

| System | x (secret) | y (migrate) | Slack z − (x + y) | Before | Priority |
|---|---:|---:|---:|---|---|
| ERP (SAP) | 10 | 5 | **−6** | 1 weak, 2 quantum-broken | Fix now, then migrate (overdue) |
| Supplier EDI feed | 10 | 4 | **−5** | 4 weak, 4 quantum-broken | Fix now, then migrate (overdue) |
| Inventory API (customer orders) | 7 | 3 | **−1** | 6 weak, 7 quantum-broken, 1 weakened | Fix now, then migrate (overdue) |
| Admin access (SSH) | 1 | 1 | +7 | 3 weak, 4 quantum-broken, 1 weakened | Fix now; quantum migration by 2033 |
| Label printing | 0.5 | 1 | +7.5 | 2 weak | Fix now (no quantum exposure) |

Five of the findings are **heuristic** (SAP profile and AS2 patterns) and were confirmed by hand with the system owners before acting on them.

## 4. Migration plan

**Wave 1 (executed): remove today's weaknesses, add post-quantum key exchange where the stack supports it.**
1. Hashes: MD5 and SHA-1 → SHA-256 (API, label service); AS2 signing → SHA-256.
2. Ciphers: 3DES → AES-256-GCM (label service, AS2); AES-128 → AES-256 (API storage, SSH).
3. TLS front end: TLS 1.2 minimum plus TLS 1.3; weak suites removed; key exchange **X25519MLKEM768 first** (hybrid ML-KEM, FIPS 203), with X25519 kept only as a fallback for clients without ML-KEM.
4. SSH: hybrid post-quantum key exchange (`mlkem768x25519-sha256`, `sntrup761x25519-sha512@openssh.com`), AES-256-GCM, HMAC-SHA-256. Deploy key moved from RSA to Ed25519.
5. API order tokens: RSA-2048 signatures → **ML-DSA-65** (FIPS 204).
6. Retire the SHA-1-signed EDI certificate. Re-issue the API certificate with ECDSA P-256 (smaller and faster than RSA, but **still quantum-vulnerable**: see wave 2).
7. SAP password hashing: salted SHA-1 → salted SHA-512 with more iterations.

**Wave 2 (next 12–24 months): dependencies outside the code.**
- Supplier feed (Java): RSA/ECDSA → ML-DSA-65 signatures, SHA-1 → SHA-256. Agree the change and a dual-signature transition period with ACME Logistics.
- SAP TLS: move to hybrid post-quantum suites as soon as the vendor supports them. Until then, minimise what crosses those links.
- TLS 1.2 fallback (ECDHE): retire the old handheld scanners that need it.

**Wave 3 (as the ecosystem allows): certificates and long-lived trust.**
- Public certificates and SSH host/user keys: move to ML-DSA (or composite/hybrid certificates) once CAs, browsers and OpenSSH support them. Track this; it cannot be done unilaterally today.

## 5. After: wave 1 results

| Risk | Before | After | Fixed | New | Still open |
|---|---:|---:|---:|---:|---:|
| CLASSICALLY-BROKEN | 16 | **1** | 15 | 0 | 1 |
| QUANTUM-BROKEN | 17 | **11** | 11 | 5 | 6 |
| QUANTUM-WEAKENED | 2 | **0** | 2 | 0 | 0 |
| OK | 2 | **14** | 1 | 13 | 1 |

How to read the five *new* quantum-broken findings: they are deliberate interim choices, not regressions. They are the ECDSA API certificate, the Ed25519 SSH key (in two files), the X25519 TLS fallback, and the single ECDHE suite kept for TLS 1.2 clients. Each replaced something weaker or bigger, and each is listed in wave 2 or 3. The remaining classically broken finding is SHA-1 in the supplier feed (wave 2).

Updated priorities: the supplier EDI feed is now the top item (still one weakness today, and 5 years overdue). ERP and the inventory API move to "migrate now" (no weaknesses today, quantum exposure remains). SSH moves to "plan by 2033". Label printing has nothing left.

## 6. Assumptions and limitations

- **Fictional client.** The code, configuration and keys exist only in this repository. No real system was scanned.
- **z is an assumption.** Nobody knows when a cryptographically relevant quantum computer will exist. Change z in `systems.json` and the ranking updates. The x and y values are the "client's" estimates, invented for the demo.
- **Scanner limits** (see [`docs/pq-inventory.md`](pq-inventory.md)): line-based rules can miss multi-line calls and hand-written cryptography; SAP and AS2 findings are heuristic; run-time key sizes are not visible to a static scan. The tool finds *where* cryptography is used; deciding *how* to migrate each use still takes engineering judgement.
- **Post-quantum certificates** were not available to deploy in this scenario, which is why certificates stay quantum-vulnerable after wave 1.

## Appendix: reproduce

    python examples/warehouse-demo/generate_demo_keys.py    # only to regenerate keys/certificates
    python -m pq_inventory scan examples/warehouse-demo/before --out examples/warehouse-demo/reports/before \
        --systems examples/warehouse-demo/systems.json --timestamp 2026-10-01T09:00:00+00:00
    python -m pq_inventory scan examples/warehouse-demo/after  --out examples/warehouse-demo/reports/after \
        --systems examples/warehouse-demo/systems.json --timestamp 2026-10-01T09:00:00+00:00
    python -m pq_inventory diff examples/warehouse-demo/reports/before/scan.json \
        examples/warehouse-demo/reports/after/scan.json --out examples/warehouse-demo/reports/diff

`tests/test_warehouse_demo.py` checks that the committed reports still match a fresh scan.
