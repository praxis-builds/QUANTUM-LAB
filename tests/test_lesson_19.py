import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from _lessons import load_lesson

# Stated ranges for the measured slopes of log2(expected oracle calls) against n.
QUANTUM_SLOPE = (0.4, 0.6)
CLASSICAL_SLOPE = (0.9, 1.1)


@pytest.mark.parametrize("n", [4, 5, 6])
def test_lesson_19_hash_circuit_computes_the_hash_for_every_input(n):
    lesson = load_lesson("19")
    circuit = QuantumCircuit(2 * n - 1)
    lesson.compute_hash(circuit, n)
    for x in range(2**n):
        out = Statevector.from_int(x, 2 ** (2 * n - 1)).evolve(circuit)
        index = int(np.argmax(np.abs(out.data)))
        assert index == x | (lesson.toy_hash(x, n) << n)
    twice = circuit.compose(circuit)
    assert Statevector.from_int(5, 2 ** (2 * n - 1)).evolve(twice).equiv(Statevector.from_int(5, 2 ** (2 * n - 1)))


def test_lesson_19_measured_square_root_scaling(tmp_path, monkeypatch):
    monkeypatch.setenv("PRAXIS_LESSONS_OUT", str(tmp_path))
    lesson = load_lesson("19")
    result = lesson.main()
    fits, rows = result["fits"], result["rows"]
    assert QUANTUM_SLOPE[0] <= fits["quantum"] <= QUANTUM_SLOPE[1]
    assert QUANTUM_SLOPE[0] <= fits["quantum_checked"] <= QUANTUM_SLOPE[1]
    assert CLASSICAL_SLOPE[0] <= fits["classical"] <= CLASSICAL_SLOPE[1]
    for n, row in rows.items():
        assert sum(lesson.toy_hash(x, n) == row["target"] for x in range(2**n)) == lesson.PREIMAGES
        assert row["p"] == pytest.approx(row["theory"], abs=0.03)
        assert row["classical_measured"] == pytest.approx(row["classical_theory"], rel=0.08)
    assert (tmp_path / "19_hash_scaling.png").exists()
