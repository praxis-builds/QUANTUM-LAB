from _lessons import load_lesson
from _pqc_skip import needs_pqc

FIPS_203_SIZES = {  # public key, secret key, ciphertext, shared secret (bytes)
    "ML-KEM-512": (800, 1632, 768, 32), "ML-KEM-768": (1184, 2400, 1088, 32), "ML-KEM-1024": (1568, 3168, 1568, 32),
}


@needs_pqc
def test_lesson_31_ml_kem_round_trip_sizes_and_implicit_rejection(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    result = load_lesson("31").main()
    for name, (pk, sk, ct, ss) in FIPS_203_SIZES.items():
        row = result["kem"][name]
        assert (row["public_key"], row["secret_key"], row["ciphertext"], row["shared_secret"]) == (pk, sk, ct, ss)
        assert row["agree"] and row["tampered_differs"]
    assert result["classical"]["RSA-2048 (OAEP)"]["ciphertext"] == 256 and result["classical"]["RSA-2048 (OAEP)"]["agree"]
    assert result["classical"]["X25519"]["public_key"] == 32 and result["classical"]["X25519"]["agree"]


def test_lesson_31_skips_cleanly_without_the_extra(monkeypatch):
    lesson = load_lesson("31")
    monkeypatch.setattr(lesson, "missing_reason", lambda: "pretend the extra is missing")
    assert lesson.main() == {"skipped": "pretend the extra is missing"}
