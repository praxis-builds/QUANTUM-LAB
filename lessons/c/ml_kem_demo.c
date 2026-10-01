/*
 * ML-KEM-768 round trip calling liboqs directly (lesson 31's C companion).
 * Build: make   (needs liboqs headers and library; OQS_PREFIX defaults to ~/_oqs)
 * Run:   make run
 * Exit status 0 = the shared secrets agree and a tampered ciphertext gives a different secret.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <oqs/oqs.h>

static int fail(const char *what, OQS_KEM *kem) {
    fprintf(stderr, "error: %s\n", what);
    OQS_KEM_free(kem);
    return EXIT_FAILURE;
}

int main(void) {
    OQS_init();
    OQS_KEM *kem = OQS_KEM_new(OQS_KEM_alg_ml_kem_768);
    if (kem == NULL) {
        fprintf(stderr, "ML-KEM-768 is not enabled in this liboqs build\n");
        return EXIT_FAILURE;
    }
    uint8_t *public_key = malloc(kem->length_public_key);
    uint8_t *secret_key = malloc(kem->length_secret_key);
    uint8_t *ciphertext = malloc(kem->length_ciphertext);
    uint8_t *secret_bob = malloc(kem->length_shared_secret);
    uint8_t *secret_alice = malloc(kem->length_shared_secret);
    if (!public_key || !secret_key || !ciphertext || !secret_bob || !secret_alice) return fail("out of memory", kem);

    if (OQS_KEM_keypair(kem, public_key, secret_key) != OQS_SUCCESS) return fail("keypair", kem);
    if (OQS_KEM_encaps(kem, ciphertext, secret_bob, public_key) != OQS_SUCCESS) return fail("encaps", kem);
    if (OQS_KEM_decaps(kem, secret_alice, ciphertext, secret_key) != OQS_SUCCESS) return fail("decaps", kem);
    int agree = memcmp(secret_alice, secret_bob, kem->length_shared_secret) == 0;

    ciphertext[0] ^= 1; /* flip one bit: ML-KEM answers with an unrelated secret (implicit rejection) */
    if (OQS_KEM_decaps(kem, secret_alice, ciphertext, secret_key) != OQS_SUCCESS) return fail("decaps (tampered)", kem);
    int tampered_differs = memcmp(secret_alice, secret_bob, kem->length_shared_secret) != 0;

    printf("liboqs %s, %s\n", OQS_version(), kem->method_name);
    printf("public key %zu bytes, secret key %zu bytes, ciphertext %zu bytes, shared secret %zu bytes\n",
           kem->length_public_key, kem->length_secret_key, kem->length_ciphertext, kem->length_shared_secret);
    printf("shared secrets agree: %s\n", agree ? "yes" : "NO");
    printf("tampered ciphertext gives a different secret: %s\n", tampered_differs ? "yes" : "NO");

    OQS_MEM_secure_free(secret_key, kem->length_secret_key);
    OQS_MEM_secure_free(secret_bob, kem->length_shared_secret);
    OQS_MEM_secure_free(secret_alice, kem->length_shared_secret);
    free(public_key);
    free(ciphertext);
    OQS_KEM_free(kem);
    OQS_destroy();
    return (agree && tampered_differs) ? EXIT_SUCCESS : EXIT_FAILURE;
}
