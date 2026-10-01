# Cryptography inventory: progress

Before: `examples/warehouse-demo/before` (2026-10-01T09:00:00+00:00)  
After: `examples/warehouse-demo/after` (2026-10-01T09:00:00+00:00)

| Risk | Before | After | Fixed | New | Unchanged |
|---|---:|---:|---:|---:|---:|
| CLASSICALLY-BROKEN | 16 | 1 | 15 | 0 | 1 |
| QUANTUM-BROKEN | 17 | 11 | 11 | 5 | 6 |
| QUANTUM-WEAKENED | 2 | 0 | 2 | 0 | 0 |
| OK | 2 | 14 | 1 | 13 | 1 |

## Fixed (risky findings that disappeared): 28

- `app/inventory_api.py`:13 QUANTUM-BROKEN RSA: RSA encryption/signature padding
- `config/nginx.conf`:7 QUANTUM-BROKEN ECDH: cipher suite ECDHE-RSA-AES128-GCM-SHA256 = ECDH + RSA-SIGNATURE + AES-128 + SHA-256
- `app/label_printer.js`:5 CLASSICALLY-BROKEN MD5: hash function
- `config/nginx.conf`:7 CLASSICALLY-BROKEN 3DES: cipher suite DES-CBC3-SHA = RSA-KEX + RSA-SIGNATURE + 3DES + HMAC-SHA1
- `config/nginx.conf`:6 CLASSICALLY-BROKEN TLS1.1: protocol TLSv1.1 enabled
- `app/label_printer.js`:9 CLASSICALLY-BROKEN 3DES: symmetric cipher
- `config/nginx.conf`:6 CLASSICALLY-BROKEN TLS1.0: protocol TLSv1 enabled
- `config/nginx.conf`:7 QUANTUM-BROKEN ECDH: cipher suite ECDHE-RSA-AES256-GCM-SHA384 = ECDH + RSA-SIGNATURE + AES-256 + SHA-384
- `config/sshd_config`:4 QUANTUM-BROKEN ECDH: KexAlgorithms ecdh-sha2-nistp256
- `certs/legacy-edi.pem`:1 QUANTUM-BROKEN RSA-SIGNATURE: certificate O=Northwind Warehouse DEMO - TEST ONLY,CN=edi.northwind.test; key RSA 2048-bit; expires 2036-09-28
- `certs/warehouse-api.pem`:1 QUANTUM-BROKEN RSA-SIGNATURE: certificate O=Northwind Warehouse DEMO - TEST ONLY,CN=inventory.northwind.test; key RSA 2048-bit; expires 2028-04-19
- `app/inventory_api.py`:21 CLASSICALLY-BROKEN SHA-1: hash function
- `app/inventory_api.py`:9 QUANTUM-WEAKENED AES-128: AES key generated with an explicit length
- `config/sshd_config`:4 QUANTUM-BROKEN DH: KexAlgorithms diffie-hellman-group14-sha1
- `ssh/deploy_key.pub`:1 QUANTUM-BROKEN RSA-SIGNATURE: SSH public key: ssh-rsa 2048-bit
- `erp/as2_partner_acme.properties`:3 CLASSICALLY-BROKEN 3DES: EDI/AS2 encryption algorithm
- `certs/legacy-edi.pem`:1 CLASSICALLY-BROKEN SHA-1: certificate O=Northwind Warehouse DEMO - TEST ONLY,CN=edi.northwind.test is signed with SHA1
- `config/nginx.conf`:8 QUANTUM-BROKEN ECDH: key-exchange group prime256v1
- `app/inventory_api.py`:8 QUANTUM-BROKEN RSA: RSA key generation (2048-bit)
- `erp/DEFAULT.PFL`:5 CLASSICALLY-BROKEN SHA-1: SAP password hash algorithm
- `erp/as2_partner_acme.properties`:4 CLASSICALLY-BROKEN SHA-1: EDI/AS2 signing / MIC hash
- `config/sshd_config`:4 CLASSICALLY-BROKEN SHA-1: KexAlgorithms diffie-hellman-group14-sha1
- `config/nginx.conf`:7 CLASSICALLY-BROKEN HMAC-SHA1: cipher suite AES128-SHA = RSA-KEX + RSA-SIGNATURE + AES-128 + HMAC-SHA1
- `config/sshd_config`:5 QUANTUM-WEAKENED AES-128: Ciphers aes128-ctr
- `ssh/authorized_keys`:1 QUANTUM-BROKEN RSA-SIGNATURE: SSH public key: ssh-rsa 2048-bit
- `app/inventory_api.py`:17 CLASSICALLY-BROKEN MD5: hash function
- `config/sshd_config`:6 CLASSICALLY-BROKEN HMAC-SHA1: MACs hmac-sha1
- `config/sshd_config`:5 CLASSICALLY-BROKEN 3DES: Ciphers 3des-cbc

## New (all findings that appeared, including OK): 18

- `ssh/authorized_keys`:1 QUANTUM-BROKEN EdDSA: SSH public key: ssh-ed25519
- `config/sshd_config`:4 OK HYBRID-PQ: KexAlgorithms mlkem768x25519-sha256
- `erp/as2_partner_acme.properties`:3 OK AES-256: EDI/AS2 encryption algorithm
- `certs/warehouse-api.pem`:1 QUANTUM-BROKEN ECDSA: certificate O=Northwind Warehouse DEMO - TEST ONLY,CN=inventory.northwind.test; key EC curve secp256r1; expires 2027-02-17
- `config/sshd_config`:5 OK AES-256: Ciphers aes256-gcm@openssh.com
- `app/label_printer.js`:9 OK AES-256: symmetric cipher
- `ssh/deploy_key.pub`:1 QUANTUM-BROKEN EdDSA: SSH public key: ssh-ed25519
- `config/nginx.conf`:10 OK HYBRID-PQ: key-exchange group X25519MLKEM768
- `config/sshd_config`:4 OK HYBRID-PQ: KexAlgorithms sntrup761x25519-sha512@openssh.com
- `config/sshd_config`:6 OK SHA-256: MACs hmac-sha2-256-etm@openssh.com
- `app/inventory_api.py`:7 OK ML-DSA: post-quantum signature (ML-DSA)
- `config/nginx.conf`:8 QUANTUM-BROKEN ECDH: cipher suite ECDHE-ECDSA-AES256-GCM-SHA384 = ECDH + ECDSA + AES-256 + SHA-384
- `app/inventory_api.py`:21 OK SHA-256: hash function
- `erp/as2_partner_acme.properties`:4 OK SHA-256: EDI/AS2 signing / MIC hash
- `app/inventory_api.py`:9 OK AES-256: AES key generated with an explicit length
- `app/inventory_api.py`:17 OK SHA-256: hash function
- `app/label_printer.js`:5 OK SHA-256: hash function
- `config/nginx.conf`:10 QUANTUM-BROKEN X25519: key-exchange group X25519

## Still open (risky findings in both scans): 7

- `app/SupplierFeed.java`:6 QUANTUM-BROKEN RSA: key pair generator
- `app/SupplierFeed.java`:16 QUANTUM-BROKEN ECDSA: signature algorithm
- `erp/DEFAULT.PFL`:3 QUANTUM-BROKEN ECDH: SAP profile TLS cipher suites (classical key exchange)
- `app/SupplierFeed.java`:12 CLASSICALLY-BROKEN SHA-1: hash function
- `erp/DEFAULT.PFL`:4 QUANTUM-BROKEN ECDH: SAP profile TLS cipher suites (classical key exchange)
- `app/SupplierFeed.java`:7 QUANTUM-BROKEN RSA: key size initialisation (2048-bit)
- `config/openssl.cnf`:3 QUANTUM-BROKEN RSA: new keys default to RSA 2048-bit
