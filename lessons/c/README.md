# C companion: ML-KEM through liboqs

`ml_kem_demo.c` does lesson 31's ML-KEM-768 round trip in C, calling the liboqs API directly: `OQS_KEM_new`, `OQS_KEM_keypair`, `OQS_KEM_encaps` and `OQS_KEM_decaps`. It also flips one ciphertext bit to show implicit rejection. This is what liboqs-python wraps.

    make -C lessons/c run            # liboqs in ~/_oqs (docs/DECISIONS.md, D1)
    make -C lessons/c run OQS_PREFIX=/opt/liboqs

If `include/oqs/oqs.h` or `lib/liboqs.so` is missing under `OQS_PREFIX`, `make` prints a `SKIP:` line with the reason and exits successfully, so nothing breaks on machines without liboqs. The binary goes to `lessons/c/build/` (git-ignored). Its exit status is 0 only if the secrets agree and the tampered ciphertext gives a different secret.

Expected output (liboqs 0.16.0):

    liboqs 0.16.0, ML-KEM-768
    public key 1184 bytes, secret key 2400 bytes, ciphertext 1088 bytes, shared secret 32 bytes
    shared secrets agree: yes
    tampered ciphertext gives a different secret: yes
