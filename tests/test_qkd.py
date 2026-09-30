"""BB84, key post-processing and randomness helpers (lessons/_qkd.py)."""

from __future__ import annotations

import math
import sys

import numpy as np
import pytest

from _lessons import LESSONS

if str(LESSONS) not in sys.path:
    sys.path.insert(0, str(LESSONS))

import _qkd as qkd  # noqa: E402


def test_matching_bases_always_agree_and_mismatched_bases_are_coin_flips():
    round_ = qkd.bb84_round(8000, np.random.default_rng(11), base_run=5000)
    keep = qkd.sift(round_)
    assert np.all(round_["alice_bits"][keep] == round_["bob_bits"][keep])
    agree_wrong_basis = np.mean(round_["alice_bits"][~keep] == round_["bob_bits"][~keep])
    assert agree_wrong_basis == pytest.approx(0.5, abs=4 * math.sqrt(0.25 / (~keep).sum()))
    assert np.all(round_["eve_bits"] == -1)  # no Eve, no Eve results


def test_channel_noise_flips_either_basis_with_probability_p():
    round_ = qkd.bb84_round(20000, np.random.default_rng(12), base_run=5100, noise_p=0.1)
    for basis in (qkd.Z, qkd.X):
        mask = qkd.sift(round_) & (round_["alice_bases"] == basis)
        assert qkd.qber(round_, mask) == pytest.approx(0.1, abs=4 * math.sqrt(0.09 / mask.sum()))
    with pytest.raises(ValueError):
        qkd.channel_noise(0.8)


def test_binary_entropy():
    assert qkd.binary_entropy(0.5) == 1.0 and qkd.binary_entropy(0) == 0.0
    assert qkd.binary_entropy(0.11) == pytest.approx(0.4999, abs=1e-3)  # where 1 - 2h(Q) = 0


def test_toeplitz_hash_is_linear_has_the_right_length_and_matches_the_matrix():
    rng = np.random.default_rng(21)
    for n, m in ((64, 16), (200, 37), (9, 9)):
        seed = rng.integers(0, 2, n + m - 1)
        x, y = rng.integers(0, 2, n), rng.integers(0, 2, n)
        hx, hy = qkd.toeplitz_hash(x, m, seed), qkd.toeplitz_hash(y, m, seed)
        assert hx.shape == (m,)
        np.testing.assert_array_equal(qkd.toeplitz_hash(x ^ y, m, seed), hx ^ hy)  # linear over GF(2)
        np.testing.assert_array_equal(hx, qkd.toeplitz_matrix(n, m, seed) @ x % 2)
    matrix = qkd.toeplitz_matrix(5, 3, np.arange(7))
    assert all(matrix[i, j] == matrix[i + 1, j + 1] for i in range(2) for j in range(4))  # constant diagonals
    with pytest.raises(ValueError):
        qkd.toeplitz_hash(np.zeros(5, int), 3, np.zeros(6, int))


def test_parity_error_correction_fixes_errors_and_counts_leakage():
    rng = np.random.default_rng(22)
    alice = rng.integers(0, 2, 4000)
    bob = alice ^ (rng.random(4000) < 0.05)
    corrected, leaked = qkd.parity_error_correction(alice, bob, rng, estimated_q=0.05)
    assert np.array_equal(corrected, alice)
    assert 4000 * qkd.binary_entropy(0.05) < leaked < 4000  # at least the Shannon minimum, less than the key
