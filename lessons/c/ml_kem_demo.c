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

int main(void) {
    int status = EXIT_FAILURE;
    const char *failed = NULL; /* the step that failed, if any */
    uint8_t *public_key = NULL, *secret_key = NULL, *ciphertext = NULL, *secret_bob = NULL, *secret_alice = NULL;

    OQS_init();
    OQS_KEM *kem = OQS_KEM_new(OQS_KEM_alg_ml_kem_768);
    if (kem == NULL) {
        fprintf(stderr, "ML-KEM-768 is not enabled in this liboqs build\n");
        OQS_destroy();
        return EXIT_FAILURE;
    }
    public_key = malloc(kem->length_public_key);
    secret_key = malloc(kem->length_secret_key);
    ciphertext = malloc(kem->length_ciphertext);
    secret_bob = malloc(kem->length_shared_secret);
    secret_alice = malloc(kem->length_shared_secret);
    if (!public_key || !secret_key || !ciphertext || !secret_bob || !secret_alice) { failed = "out of memory"; goto cleanup; }

    if (OQS_KEM_keypair(kem, public_key, secret_key) != OQS_SUCCESS) { failed = "keypair"; goto cleanup; }
    if (OQS_KEM_encaps(kem, ciphertext, secret_bob, public_key) != OQS_SUCCESS) { failed = "encaps"; goto cleanup; }
    if (OQS_KEM_decaps(kem, secret_alice, ciphertext, secret_key) != OQS_SUCCESS) { failed = "decaps"; goto cleanup; }
    int agree = memcmp(secret_alice, secret_bob, kem->length_shared_secret) == 0;

    ciphertext[0] ^= 1; /* flip one bit: ML-KEM answers with an unrelated secret (implicit rejection) */
    if (OQS_KEM_decaps(kem, secret_alice, ciphertext, secret_key) != OQS_SUCCESS) { failed = "decaps (tampered)"; goto cleanup; }
    int tampered_differs = memcmp(secret_alice, secret_bob, kem->length_shared_secret) != 0;

    printf("liboqs %s, %s\n", OQS_version(), kem->method_name);
    printf("public key %zu bytes, secret key %zu bytes, ciphertext %zu bytes, shared secret %zu bytes\n",
           kem->length_public_key, kem->length_secret_key, kem->length_ciphertext, kem->length_shared_secret);
    printf("shared secrets agree: %s\n", agree ? "yes" : "NO");
    printf("tampered ciphertext gives a different secret: %s\n", tampered_differs ? "yes" : "NO");
    status = (agree && tampered_differs) ? EXIT_SUCCESS : EXIT_FAILURE;

cleanup: /* one exit path, also after an error: wipe the secrets, then free everything */
    if (failed != NULL) fprintf(stderr, "error: %s\n", failed);
    if (secret_key != NULL) OQS_MEM_secure_free(secret_key, kem->length_secret_key);
    if (secret_bob != NULL) OQS_MEM_secure_free(secret_bob, kem->length_shared_secret);
    if (secret_alice != NULL) OQS_MEM_secure_free(secret_alice, kem->length_shared_secret);
    free(public_key);
    free(ciphertext);
    OQS_KEM_free(kem);
    OQS_destroy();
    return status;
}
