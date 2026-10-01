# Cryptography inventory: `examples/warehouse-demo/after`

_Generated 2026-10-01T09:00:00+00:00 by pq_inventory 0.1.0 (read-only scan; no key material included)._

## Executive summary

7 of 11 scanned files use cryptography that a future quantum computer would break, and 1 use cryptography that is already weak today.

| Risk | Findings | What it means |
|---|---:|---|
| CLASSICALLY-BROKEN | 1 | Already weak today, without any quantum computer. Fix first. |
| QUANTUM-BROKEN | 11 | Secure today, but a future large quantum computer breaks it (Shor's algorithm). Data recorded now can be decrypted later. |
| QUANTUM-WEAKENED | 0 | A quantum computer roughly halves its strength (Grover's algorithm). Upgrade during maintenance. |
| OK | 14 | No known quantum break. No action needed. |

11 files scanned, 11 with findings, 26 findings (4 heuristic), 0 files skipped.

## Migration roadmap (Mosca: at risk if x + y > z)

_ASSUMPTION for this case study: z = 9 years (2026 to 2035, the year NIST IR 8547's initial public draft proposes for disallowing quantum-vulnerable public-key algorithms). A planning horizon, NOT a forecast of when a quantum computer will exist._ z = 9 years.

| Priority | System | x | y | z | Slack (years) | Findings | Start by | Actions |
|---|---|---:|---:|---:|---:|---:|---|---|
| 1. Fix now: already weak without any quantum computer | Supplier EDI feed | 10 | 4 | 9 | -5 | 6 | now (overdue by 5 years) | SHA-1 (1) → SHA-256 or SHA-384 (FIPS 180-4) or SHA3-256 (FIPS 202); RSA (2) → ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition for key exchange; ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots for signatures; ECDSA (1) → ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots |
| 2. Migrate now: at risk under Mosca (x + y > z) | ERP (SAP) | 10 | 5 | 9 | -6 | 2 | now (overdue by 6 years) | ECDH (2) → ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition |
| 2. Migrate now: at risk under Mosca (x + y > z) | Inventory API (customer orders) | 7 | 3 | 9 | -1 | 10 | now (overdue by 1 year) | ECDSA (1) → ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots; ECDH (1) → ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition; X25519 (1) → ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition; RSA (1) → ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition for key exchange; ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots for signatures |
| 3. Plan migration: quantum-vulnerable, deadline from Mosca | Admin access (SSH) | 1 | 1 | 9 | +7 | 6 | 2033 | EdDSA (2) → ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots |
| 5. No action found | Label printing | 0.5 | 1 | 9 | +7.5 | 2 | - | none |

## Findings by file

### `app/SupplierFeed.java`

| Line | Risk | Algorithm | Detail | Recommended replacement |
|---:|---|---|---|---|
| 6 | QUANTUM-BROKEN | RSA | key pair generator | ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition for key exchange; ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots for signatures |
| 7 | QUANTUM-BROKEN | RSA | key size initialisation (2048-bit) | ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition for key exchange; ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots for signatures |
| 12 | CLASSICALLY-BROKEN | SHA-1 | hash function | SHA-256 or SHA-384 (FIPS 180-4) or SHA3-256 (FIPS 202) |
| 16 | QUANTUM-BROKEN | ECDSA | signature algorithm | ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots |

### `certs/warehouse-api.pem`

| Line | Risk | Algorithm | Detail | Recommended replacement |
|---:|---|---|---|---|
| 1 | QUANTUM-BROKEN | ECDSA | certificate O=Northwind Warehouse DEMO - TEST ONLY,CN=inventory.northwind.test; key EC curve secp256r1; expires 2027-02-17 | ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots |

### `config/nginx.conf`

| Line | Risk | Algorithm | Detail | Recommended replacement |
|---:|---|---|---|---|
| 8 | QUANTUM-BROKEN | ECDH | cipher suite ECDHE-ECDSA-AES256-GCM-SHA384 = ECDH + ECDSA + AES-256 + SHA-384 | ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition |
| 10 | OK | HYBRID-PQ | key-exchange group X25519MLKEM768 | none needed |
| 10 | QUANTUM-BROKEN | X25519 | key-exchange group X25519 | ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition |

### `config/openssl.cnf`

| Line | Risk | Algorithm | Detail | Recommended replacement |
|---:|---|---|---|---|
| 3 | QUANTUM-BROKEN | RSA | new keys default to RSA 2048-bit | ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition for key exchange; ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots for signatures |
| 4 | OK | SHA-256 | default digest sha256 | none needed |

### `erp/DEFAULT.PFL`

| Line | Risk | Algorithm | Detail | Recommended replacement |
|---:|---|---|---|---|
| 3 | QUANTUM-BROKEN | ECDH (heuristic) | SAP profile TLS cipher suites (classical key exchange) | ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition |
| 4 | QUANTUM-BROKEN | ECDH (heuristic) | SAP profile TLS cipher suites (classical key exchange) | ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition |

### `ssh/authorized_keys`

| Line | Risk | Algorithm | Detail | Recommended replacement |
|---:|---|---|---|---|
| 1 | QUANTUM-BROKEN | EdDSA | SSH public key: ssh-ed25519 | ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots |

### `ssh/deploy_key.pub`

| Line | Risk | Algorithm | Detail | Recommended replacement |
|---:|---|---|---|---|
| 1 | QUANTUM-BROKEN | EdDSA | SSH public key: ssh-ed25519 | ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots |

### `app/inventory_api.py`

| Line | Risk | Algorithm | Detail | Recommended replacement |
|---:|---|---|---|---|
| 7 | OK | ML-DSA | post-quantum signature (ML-DSA) | none needed |
| 9 | OK | AES-256 | AES key generated with an explicit length | none needed |
| 17 | OK | SHA-256 | hash function | none needed |
| 21 | OK | SHA-256 | hash function | none needed |

### `app/label_printer.js`

| Line | Risk | Algorithm | Detail | Recommended replacement |
|---:|---|---|---|---|
| 5 | OK | SHA-256 | hash function | none needed |
| 9 | OK | AES-256 | symmetric cipher | none needed |

### `config/sshd_config`

| Line | Risk | Algorithm | Detail | Recommended replacement |
|---:|---|---|---|---|
| 4 | OK | HYBRID-PQ | KexAlgorithms mlkem768x25519-sha256 | none needed |
| 4 | OK | HYBRID-PQ | KexAlgorithms sntrup761x25519-sha512@openssh.com | none needed |
| 5 | OK | AES-256 | Ciphers aes256-gcm@openssh.com | none needed |
| 6 | OK | SHA-256 | MACs hmac-sha2-256-etm@openssh.com | none needed |

### `erp/as2_partner_acme.properties`

| Line | Risk | Algorithm | Detail | Recommended replacement |
|---:|---|---|---|---|
| 3 | OK | AES-256 (heuristic) | EDI/AS2 encryption algorithm | none needed |
| 4 | OK | SHA-256 (heuristic) | EDI/AS2 signing / MIC hash | none needed |

