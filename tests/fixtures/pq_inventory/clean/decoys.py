"""Algorithms named only in strings and identifiers: nothing in this file should be reported."""

MESSAGE = "We replaced MD5 and RSA with SHA-256 and ML-KEM."
md5_column = "checksum"
config = {"key_size": "large"}


def rsa_like_padding(value):
    return value
