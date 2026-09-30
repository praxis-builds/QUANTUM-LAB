from _lessons import load_lesson


def test_lesson_22_bit_flip_code(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    result = load_lesson("22").main()
    assert {q: row["syndrome"] for q, row in result["single"].items()} == {0: "01", 1: "11", 2: "10"}
    assert all(row["all_corrected"] for row in result["single"].values()) and result["no_error"]
    assert all(row["failed"] for row in result["multi"].values())  # 2 or 3 flips defeat it
    assert {f for f, failed in result["patterns"].items() if failed} == {(0, 1, 1), (1, 0, 1), (1, 1, 0), (1, 1, 1)}
    for p, row in result["sweep"].items():
        # Stated tolerance (seeded): within 4 binomial standard deviations + 0.005 of 3p^2 - 2p^3.
        assert abs(row["measured"] - row["formula"]) <= 4 * row["sigma"] + 0.005, p
        assert abs(result["enumerated"][p] - row["formula"]) < 1e-12
        if p < 0.5:
            assert row["formula"] < p  # better than an unprotected qubit below break-even
    assert (tmp_path / "22_bit_flip_code.png").exists()
