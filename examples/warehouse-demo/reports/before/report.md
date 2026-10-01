# Cryptography inventory: `examples/warehouse-demo/before`

_Generated 2026-10-01T09:00:00+00:00 by pq_inventory 0.1.0 (read-only scan; no key material included)._

## Executive summary

10 of 12 scanned files use cryptography that a future quantum computer would break, and 8 use cryptography that is already weak today.

| Risk | Findings | What it means |
|---|---:|---|
| CLASSICALLY-BROKEN | 16 | Already weak today, without any quantum computer. Fix first. |
| QUANTUM-BROKEN | 17 | Secure today, but a future large quantum computer breaks it (Shor's algorithm). Data recorded now can be decrypted later. |
| QUANTUM-WEAKENED | 2 | A quantum computer roughly halves its strength (Grover's algorithm). Upgrade during maintenance. |
| OK | 2 | No known quantum break. No action needed. |

12 files scanned, 12 with findings, 37 findings (5 heuristic), 0 files skipped.

## Migration roadmap (Mosca: at risk if x + y > z)

_ASSUMPTION for this case study: z = 9 years (2026 to 2035, the year NIST IR 8547's initial public draft proposes for disallowing quantum-vulnerable public-key algorithms). A planning horizon, NOT a forecast of when a quantum computer will exist._ z = 9 years.

| Priority | System | x | y | z | Slack (years) | Findings | Start by | Actions |
|---|---|---:|---:|---:|---:|---:|---|---|
| 1. Fix now: already weak without any quantum computer | ERP (SAP) | 10 | 5 | 9 | -6 | 3 | now (overdue by 6 years) | SHA-1 (1) → SHA-256 or SHA-384 (FIPS 180-4) or SHA3-256 (FIPS 202); ECDH (2) → ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition |
| 1. Fix now: already weak without any quantum computer | Supplier EDI feed | 10 | 4 | 9 | -5 | 8 | now (overdue by 5 years) | SHA-1 (3) → SHA-256 or SHA-384 (FIPS 180-4) or SHA3-256 (FIPS 202); 3DES (1) → AES-256-GCM (FIPS 197, SP 800-38D); RSA (2) → ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition for key exchange; ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots for signatures; ECDSA (1) → ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots; RSA-SIGNATURE (1) → ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots |
| 1. Fix now: already weak without any quantum computer | Inventory API (customer orders) | 7 | 3 | 9 | -1 | 16 | now (overdue by 1 year) | MD5 (1) → SHA-256 or SHA-384 (FIPS 180-4) or SHA3-256 (FIPS 202); SHA-1 (1) → SHA-256 or SHA-384 (FIPS 180-4) or SHA3-256 (FIPS 202); TLS1.0 (1) → TLS 1.3 (TLS 1.2 minimum); TLS1.1 (1) → TLS 1.3 (TLS 1.2 minimum); 3DES (1) → AES-256-GCM (FIPS 197, SP 800-38D); HMAC-SHA1 (1) → HMAC-SHA-256; RSA (3) → ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition for key exchange; ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots for signatures; RSA-SIGNATURE (1) → ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots; ECDH (3) → ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition; AES-128 (1) → AES-256-GCM (FIPS 197, SP 800-38D) |
| 1. Fix now: already weak without any quantum computer | Admin access (SSH) | 1 | 1 | 9 | +7 | 8 | 2033 | SHA-1 (1) → SHA-256 or SHA-384 (FIPS 180-4) or SHA3-256 (FIPS 202); 3DES (1) → AES-256-GCM (FIPS 197, SP 800-38D); HMAC-SHA1 (1) → HMAC-SHA-256; DH (1) → ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition; ECDH (1) → ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition; RSA-SIGNATURE (2) → ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots; AES-128 (1) → AES-256-GCM (FIPS 197, SP 800-38D) |
| 1. Fix now: already weak without any quantum computer | Label printing | 0.5 | 1 | 9 | +7.5 | 2 | - | MD5 (1) → SHA-256 or SHA-384 (FIPS 180-4) or SHA3-256 (FIPS 202); 3DES (1) → AES-256-GCM (FIPS 197, SP 800-38D) |

## Findings by file

### `app/SupplierFeed.java`

| Line | Risk | Algorithm | Detail | Recommended replacement |
|---:|---|---|---|---|
| 6 | QUANTUM-BROKEN | RSA | key pair generator | ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition for key exchange; ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots for signatures |
| 7 | QUANTUM-BROKEN | RSA | key size initialisation (2048-bit) | ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition for key exchange; ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots for signatures |
| 12 | CLASSICALLY-BROKEN | SHA-1 | hash function | SHA-256 or SHA-384 (FIPS 180-4) or SHA3-256 (FIPS 202) |
| 16 | QUANTUM-BROKEN | ECDSA | signature algorithm | ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots |

### `app/inventory_api.py`

| Line | Risk | Algorithm | Detail | Recommended replacement |
|---:|---|---|---|---|
| 8 | QUANTUM-BROKEN | RSA | RSA key generation (2048-bit) | ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition for key exchange; ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots for signatures |
| 9 | QUANTUM-WEAKENED | AES-128 | AES key generated with an explicit length | AES-256-GCM (FIPS 197, SP 800-38D) |
| 13 | QUANTUM-BROKEN | RSA | RSA encryption/signature padding | ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition for key exchange; ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots for signatures |
| 13 | OK | SHA-256 | hash function | none needed |
| 17 | CLASSICALLY-BROKEN | MD5 | hash function | SHA-256 or SHA-384 (FIPS 180-4) or SHA3-256 (FIPS 202) |
| 21 | CLASSICALLY-BROKEN | SHA-1 | hash function | SHA-256 or SHA-384 (FIPS 180-4) or SHA3-256 (FIPS 202) |

### `app/label_printer.js`

| Line | Risk | Algorithm | Detail | Recommended replacement |
|---:|---|---|---|---|
| 5 | CLASSICALLY-BROKEN | MD5 | hash function | SHA-256 or SHA-384 (FIPS 180-4) or SHA3-256 (FIPS 202) |
| 9 | CLASSICALLY-BROKEN | 3DES | symmetric cipher | AES-256-GCM (FIPS 197, SP 800-38D) |

### `certs/legacy-edi.pem`

| Line | Risk | Algorithm | Detail | Recommended replacement |
|---:|---|---|---|---|
| 1 | QUANTUM-BROKEN | RSA-SIGNATURE | certificate O=Northwind Warehouse DEMO - TEST ONLY,CN=edi.northwind.test; key RSA 2048-bit; expires 2036-09-28 | ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots |
| 1 | CLASSICALLY-BROKEN | SHA-1 | certificate O=Northwind Warehouse DEMO - TEST ONLY,CN=edi.northwind.test is signed with SHA1 | SHA-256 or SHA-384 (FIPS 180-4) or SHA3-256 (FIPS 202) |

### `config/nginx.conf`

| Line | Risk | Algorithm | Detail | Recommended replacement |
|---:|---|---|---|---|
| 6 | CLASSICALLY-BROKEN | TLS1.0 | protocol TLSv1 enabled | TLS 1.3 (TLS 1.2 minimum) |
| 6 | CLASSICALLY-BROKEN | TLS1.1 | protocol TLSv1.1 enabled | TLS 1.3 (TLS 1.2 minimum) |
| 7 | CLASSICALLY-BROKEN | 3DES | cipher suite DES-CBC3-SHA = RSA-KEX + RSA-SIGNATURE + 3DES + HMAC-SHA1 | AES-256-GCM (FIPS 197, SP 800-38D) |
| 7 | QUANTUM-BROKEN | ECDH | cipher suite ECDHE-RSA-AES128-GCM-SHA256 = ECDH + RSA-SIGNATURE + AES-128 + SHA-256 | ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition |
| 7 | QUANTUM-BROKEN | ECDH | cipher suite ECDHE-RSA-AES256-GCM-SHA384 = ECDH + RSA-SIGNATURE + AES-256 + SHA-384 | ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition |
| 7 | CLASSICALLY-BROKEN | HMAC-SHA1 | cipher suite AES128-SHA = RSA-KEX + RSA-SIGNATURE + AES-128 + HMAC-SHA1 | HMAC-SHA-256 |
| 8 | QUANTUM-BROKEN | ECDH | key-exchange group prime256v1 | ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition |

### `config/sshd_config`

| Line | Risk | Algorithm | Detail | Recommended replacement |
|---:|---|---|---|---|
| 4 | QUANTUM-BROKEN | DH | KexAlgorithms diffie-hellman-group14-sha1 | ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition |
| 4 | QUANTUM-BROKEN | ECDH | KexAlgorithms ecdh-sha2-nistp256 | ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition |
| 4 | CLASSICALLY-BROKEN | SHA-1 | KexAlgorithms diffie-hellman-group14-sha1 | SHA-256 or SHA-384 (FIPS 180-4) or SHA3-256 (FIPS 202) |
| 5 | CLASSICALLY-BROKEN | 3DES | Ciphers 3des-cbc | AES-256-GCM (FIPS 197, SP 800-38D) |
| 5 | QUANTUM-WEAKENED | AES-128 | Ciphers aes128-ctr | AES-256-GCM (FIPS 197, SP 800-38D) |
| 6 | CLASSICALLY-BROKEN | HMAC-SHA1 | MACs hmac-sha1 | HMAC-SHA-256 |

### `erp/DEFAULT.PFL`

| Line | Risk | Algorithm | Detail | Recommended replacement |
|---:|---|---|---|---|
| 3 | QUANTUM-BROKEN | ECDH (heuristic) | SAP profile TLS cipher suites (classical key exchange) | ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition |
| 4 | QUANTUM-BROKEN | ECDH (heuristic) | SAP profile TLS cipher suites (classical key exchange) | ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition |
| 5 | CLASSICALLY-BROKEN | SHA-1 (heuristic) | SAP password hash algorithm | SHA-256 or SHA-384 (FIPS 180-4) or SHA3-256 (FIPS 202) |

### `erp/as2_partner_acme.properties`

| Line | Risk | Algorithm | Detail | Recommended replacement |
|---:|---|---|---|---|
| 3 | CLASSICALLY-BROKEN | 3DES (heuristic) | EDI/AS2 encryption algorithm | AES-256-GCM (FIPS 197, SP 800-38D) |
| 4 | CLASSICALLY-BROKEN | SHA-1 (heuristic) | EDI/AS2 signing / MIC hash | SHA-256 or SHA-384 (FIPS 180-4) or SHA3-256 (FIPS 202) |

### `certs/warehouse-api.pem`

| Line | Risk | Algorithm | Detail | Recommended replacement |
|---:|---|---|---|---|
| 1 | QUANTUM-BROKEN | RSA-SIGNATURE | certificate O=Northwind Warehouse DEMO - TEST ONLY,CN=inventory.northwind.test; key RSA 2048-bit; expires 2028-04-19 | ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots |

### `config/openssl.cnf`

| Line | Risk | Algorithm | Detail | Recommended replacement |
|---:|---|---|---|---|
| 3 | QUANTUM-BROKEN | RSA | new keys default to RSA 2048-bit | ML-KEM-768 (NIST FIPS 203); hybrid X25519MLKEM768 during the transition for key exchange; ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots for signatures |
| 4 | OK | SHA-256 | default digest sha256 | none needed |

### `ssh/authorized_keys`

| Line | Risk | Algorithm | Detail | Recommended replacement |
|---:|---|---|---|---|
| 1 | QUANTUM-BROKEN | RSA-SIGNATURE | SSH public key: ssh-rsa 2048-bit | ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots |

### `ssh/deploy_key.pub`

| Line | Risk | Algorithm | Detail | Recommended replacement |
|---:|---|---|---|---|
| 1 | QUANTUM-BROKEN | RSA-SIGNATURE | SSH public key: ssh-rsa 2048-bit | ML-DSA-65 (NIST FIPS 204); SLH-DSA (FIPS 205) for long-lived roots |

