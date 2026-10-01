/* Planted legacy crypto for pq_inventory tests (never compiled). */
#include <openssl/evp.h>
#include <openssl/rsa.h>

void legacy(void) {
    const EVP_MD *md = EVP_md5();
    const EVP_CIPHER *cipher = EVP_aes_128_cbc();
    RSA_generate_key_ex(rsa, 2048, e, NULL);
    EC_KEY *ec = EC_KEY_new_by_curve_name(NID_X9_62_prime256v1);
}
