import math

import numpy as np
import pytest

from praxis_quantum_lab.repair_comparison import fixed_split_data
from praxis_quantum_lab.repair_metrics import (
    accuracy_with_wilson,
    decision_agreement,
    kernel_alignment,
    svc_decision,
)


def test_alignment_identity_scale_invariance_and_orthogonality():
    matrix = np.array([[1.0, 0.3], [0.3, 1.0]])
    assert kernel_alignment(matrix, matrix) == pytest.approx(1.0)
    assert kernel_alignment(matrix, 5.0 * matrix) == pytest.approx(1.0)
    assert kernel_alignment(np.diag([1.0, 0.0]), np.diag([0.0, 1.0])) == 0.0
    with pytest.raises(ValueError):
        kernel_alignment(matrix, np.eye(3))
    with pytest.raises(ValueError):
        kernel_alignment(np.zeros((2, 2)), matrix)


def test_decision_agreement_on_hand_made_vectors():
    reference = np.array([-2.0, -1.0, 1.0, 2.0])
    same = decision_agreement(3.0 * reference, reference)
    assert same["pearson_r"] == pytest.approx(1.0)
    assert same["sign_agreement"] == 4
    flipped = decision_agreement(np.array([-2.0, 1.0, 1.0, 2.0]), reference)
    assert flipped["sign_agreement"] == 3
    assert math.isnan(decision_agreement(np.ones(4), reference)["pearson_r"])
    with pytest.raises(ValueError):
        decision_agreement(np.ones(3), reference)


def test_accuracy_with_wilson():
    result = accuracy_with_wilson(np.array([0, 1] * 6), np.array([0, 1] * 5 + [1, 0]))
    assert result["correct"] == 10 and result["total"] == 12
    assert result["wilson95"][0] == pytest.approx(0.552, abs=1e-3)
    assert result["wilson95"][1] == pytest.approx(0.953, abs=1e-3)


def test_exact_svc_decision_shape_and_saved_predictions():
    data = fixed_split_data()
    exact = data["exact_full"]
    decision, predictions = svc_decision(exact[:28, :28], exact[28:, :28], data["y_train"])
    assert decision.shape == (12,)
    assert predictions.shape == (12,)
    # sign of the decision function is the predicted class
    np.testing.assert_array_equal(predictions, (decision > 0).astype(int))
    assert np.mean(predictions == data["y_test"]) == pytest.approx(10 / 12)
