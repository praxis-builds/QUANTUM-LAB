from _lessons import load_lesson
from _pqc_skip import needs_pqc

FIPS_204_SIZES = {"ML-DSA-44": (1312, 2420), "ML-DSA-65": (1952, 3309), "ML-DSA-87": (2592, 4627)}  # public key, signature


@needs_pqc
def test_lesson_33_ml_dsa_verifies_and_rejects_tampering(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    result = load_lesson("33").main()
    for name, (pk, sig) in FIPS_204_SIZES.items():
        row = result["pq"][name]
        assert (row["public_key"], row["signature"]) == (pk, sig)
        assert row["valid"] and not row["tampered_message"] and not row["tampered_signature"] and not row["wrong_key"]
    assert result["slh"]["SLH_DSA_PURE_SHA2_128S"]["signature"] == 7856
    assert result["slh"]["SLH_DSA_PURE_SHA2_128S"]["valid"]
    ecdsa = result["classical"]["ECDSA P-256"]
    assert ecdsa["valid"] and not ecdsa["tampered_message"] and 68 <= ecdsa["signature"] <= 72
