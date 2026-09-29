import numpy as np
import pytest

from praxis_quantum_lab.complex_math import as_complex_vector, magnitude_squared


def test_magnitude_squared_uses_complex_conjugation() -> None:
    assert np.isclose(magnitude_squared(3 + 4j), 25.0)


def test_complex_vector_rejects_non_vector_input() -> None:
    with pytest.raises(ValueError, match="one-dimensional"):
        as_complex_vector([[1, 0], [0, 1]])
