"""Circuit Playground: strict validation, exact states, presets, Bloch vectors, HTTP routes."""

from __future__ import annotations

import json
import math
from http.client import HTTPConnection
from threading import Thread

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from praxis_quantum_lab import circuit_playground as cp
from praxis_quantum_lab import dashboard_server as dashboard


def request(qubits=1, gates=None, shots=64, seed=7):
    return {"qubits": qubits, "gates": gates if gates is not None else [], "shots": shots, "seed": seed}


def gate(name, *wires, angle=None):
    return cp._gate(name, *wires, angle=angle)


def final_state(payload):
    return cp.circuit_states(cp.parse_circuit_request(payload))[-1]


# ---------------------------------------------------------------- validation

@pytest.mark.parametrize(
    "payload",
    [
        None, [], "x", {}, {"qubits": 1},
        {**request(), "extra": 1},
        request(qubits=0), request(qubits=4), request(qubits=True), request(qubits=1.0), request(qubits="1"),
        request(shots=0), request(shots=8193), request(shots=True), request(shots=64.0),
        request(seed=-1), request(seed=2**31), request(seed=False),
        request(gates="h"), request(gates={"gate": "h"}),
        request(gates=[gate("h", 0)] * 31),
        request(gates=[{"gate": "h"}]),
        request(gates=[{"qubits": [0]}]),
        request(gates=[{"gate": "h", "qubits": [0], "extra": 1}]),
        request(gates=[{"gate": "bogus", "qubits": [0]}]),
        request(gates=[{"gate": 5, "qubits": [0]}]),
        request(gates=[{"gate": "h", "qubits": 0}]),
        request(gates=[{"gate": "h", "qubits": [0, 0]}]),
        request(gates=[{"gate": "h", "qubits": [1]}]),
        request(gates=[{"gate": "h", "qubits": [-1]}]),
        request(gates=[{"gate": "h", "qubits": [True]}]),
        request(gates=[{"gate": "h", "qubits": [0.0]}]),
        request(qubits=2, gates=[{"gate": "cx", "qubits": [0]}]),
        request(qubits=2, gates=[{"gate": "cx", "qubits": [1, 1]}]),
        request(qubits=2, gates=[{"gate": "swap", "qubits": [0, 2]}]),
        request(gates=[{"gate": "rx", "qubits": [0]}]),
        request(gates=[{"gate": "h", "qubits": [0], "angle": 1.0}]),
        request(gates=[{"gate": "rx", "qubits": [0], "angle": True}]),
        request(gates=[{"gate": "rx", "qubits": [0], "angle": "1"}]),
        request(gates=[{"gate": "rx", "qubits": [0], "angle": float("nan")}]),
        request(gates=[{"gate": "ry", "qubits": [0], "angle": float("inf")}]),
        request(gates=[{"gate": "rz", "qubits": [0], "angle": 4 * math.pi + 1e-9}]),
        request(gates=[{"gate": "rz", "qubits": [0], "angle": -4 * math.pi - 1e-9}]),
        request(gates=[{"gate": "rz", "qubits": [0], "angle": 10**400}]),
        request(gates=[{"gate": "rz", "qubits": [0], "angle": -(10**400)}]),
        request(qubits=2, gates=[{"gate": "cp", "qubits": [0, 1]}]),
        request(qubits=2, gates=[{"gate": "cp", "qubits": [0], "angle": 1.0}]),
        request(qubits=2, gates=[{"gate": "cp", "qubits": [1, 1], "angle": 1.0}]),
        request(qubits=2, gates=[{"gate": "cp", "qubits": [0, 1], "angle": 4 * math.pi + 1e-9}]),
        request(qubits=2, gates=[{"gate": "cp", "qubits": [0, 1], "angle": float("nan")}]),
        request(qubits=2, gates=[{"gate": "cz", "qubits": [0, 1], "angle": 1.0}]),
        request(gates=[{"gate": "cp", "qubits": [0, 1], "angle": 1.0}]),
        request(qubits=3, gates=[{"gate": "ccz", "qubits": [0, 1]}]),
        request(qubits=3, gates=[{"gate": "ccz", "qubits": [0, 1, 1]}]),
        request(qubits=3, gates=[{"gate": "ccz", "qubits": [0, 1, 2], "angle": 1.0}]),
        request(qubits=3, gates=[{"gate": "ccz", "qubits": [0, 1, 3]}]),
        request(qubits=2, gates=[{"gate": "ccz", "qubits": [0, 1, 2]}]),
        request(qubits=3, gates=[{"gate": "cx", "qubits": [0, 1, 2]}]),
        request(qubits=3, gates=[{"gate": "ccx", "qubits": [0, 1]}]),
        request(qubits=3, gates=[{"gate": "ccx", "qubits": [0, 0, 1]}]),
        request(qubits=3, gates=[{"gate": "ccx", "qubits": [0, 1, 2], "angle": 1.0}]),
        request(qubits=2, gates=[{"gate": "ccx", "qubits": [0, 1, 2]}]),
        request(gates=[gate("measure", 0), gate("h", 0)]),
        request(gates=[gate("measure", 0), gate("measure", 0)]),
        request(qubits=2, gates=[gate("measure", 1), gate("cx", 0, 1)]),
    ],
)
def test_circuit_request_rejects_invalid_values(payload):
    with pytest.raises(ValueError):
        cp.parse_circuit_request(payload)


def test_circuit_request_accepts_limits():
    parsed = cp.parse_circuit_request(request(qubits=3, gates=[gate("h", 0)] * 30, shots=8192, seed=2**31 - 1))
    assert len(parsed["gates"]) == 30
    edge = cp.parse_circuit_request(request(gates=[gate("rx", 0, angle=4 * math.pi), gate("ry", 0, angle=-4 * math.pi)]))
    assert edge["gates"][0]["angle"] == pytest.approx(4 * math.pi)
    integer_angle = cp.parse_circuit_request(request(gates=[gate("rz", 0, angle=1)]))
    assert integer_angle["gates"][0]["angle"] == 1.0 and type(integer_angle["gates"][0]["angle"]) is float
    # a measured qubit does not block gates on other qubits
    cp.parse_circuit_request(request(qubits=2, gates=[gate("measure", 0), gate("h", 1)]))


def test_measure_is_deferred_and_never_collapses_the_exact_state():
    plain = final_state(request(gates=[gate("h", 0)]))
    measured = final_state(request(gates=[gate("h", 0), gate("measure", 0)]))
    np.testing.assert_allclose(plain, measured)


# ---------------------------------------------------------- exact simulation

def qiskit_state(num_qubits, gates):
    circuit = QuantumCircuit(num_qubits)
    for item in gates:
        if item["gate"] == "measure":
            continue
        if "angle" in item:
            getattr(circuit, item["gate"])(item["angle"], *item["qubits"])
        else:
            getattr(circuit, item["gate"])(*item["qubits"])
    return Statevector(circuit).data


@pytest.mark.parametrize("seed", range(8))
@pytest.mark.parametrize("num_qubits", [1, 2, 3])
def test_numpy_state_matches_qiskit_for_random_circuits(num_qubits, seed):
    rng = np.random.default_rng([num_qubits, seed])
    names = ["h", "x", "y", "z", "s", "t", "rx", "ry", "rz"] + (["cx", "cz", "cp", "swap"] if num_qubits > 1 else [])
    names += ["ccz", "ccx"] if num_qubits == 3 else []
    gates = []
    for _ in range(int(rng.integers(5, 25))):
        name = names[int(rng.integers(len(names)))]
        if name in ("ccz", "ccx"):
            gates.append(gate(name, *[int(w) for w in rng.permutation(3)]))
        elif name in {"cx", "cz", "cp", "swap"}:
            wires = [int(w) for w in rng.choice(num_qubits, size=2, replace=False)]
            angle = float(rng.uniform(-4 * math.pi, 4 * math.pi)) if name == "cp" else None
            gates.append(gate(name, *wires, angle=angle))
        elif name in {"rx", "ry", "rz"}:
            gates.append(gate(name, int(rng.integers(num_qubits)), angle=float(rng.uniform(-4 * math.pi, 4 * math.pi))))
        else:
            gates.append(gate(name, int(rng.integers(num_qubits))))
    ours = final_state(request(qubits=num_qubits, gates=gates))
    np.testing.assert_allclose(ours, qiskit_state(num_qubits, gates), atol=1e-12)
    assert np.linalg.norm(ours) == pytest.approx(1.0)


def test_basis_convention_is_little_endian():
    state = final_state(request(qubits=3, gates=[gate("x", 0)]))
    assert np.argmax(np.abs(state)) == 1  # |001>: q0 is the rightmost bit
    state = final_state(request(qubits=3, gates=[gate("x", 2)]))
    assert np.argmax(np.abs(state)) == 4
    state = final_state(request(qubits=2, gates=[gate("x", 0), gate("cx", 0, 1)]))
    assert np.argmax(np.abs(state)) == 3  # |11>


# ------------------------------------------------------------------- presets

PRESET = {preset["id"]: preset for preset in cp.PRESETS}


def preset_state(name):
    preset = PRESET[name]
    return final_state(request(qubits=preset["qubits"], gates=preset["gates"]))


def test_all_fifteen_presets_validate_and_have_captions():
    assert [p["id"] for p in cp.PRESETS] == [
        "superposition", "interference", "phase", "bell", "ghz", "grover", "kickback",
        "dj_constant", "dj_balanced", "bv_101", "simon_11", "qft_period2", "qpe_s", "bitflip_code", "grover3",
    ]
    assert len(cp.presets_payload()["presets"]) == 15
    assert all(p["qubits"] <= cp.MAX_QUBITS == 3 for p in cp.PRESETS)  # the limit was not raised
    for preset in cp.PRESETS:
        assert preset["caption"] and preset["title"]
        assert len(preset["gates"]) <= cp.MAX_GATES


def test_preset_superposition_interference_and_phase():
    np.testing.assert_allclose(np.abs(preset_state("superposition")) ** 2, [0.5, 0.5], atol=1e-12)
    np.testing.assert_allclose(preset_state("interference"), [1, 0], atol=1e-12)  # H.H returns |0>
    np.testing.assert_allclose(np.abs(preset_state("phase")) ** 2, [0, 1], atol=1e-12)  # H.Z.H = X


def test_preset_bell_and_ghz_probabilities():
    np.testing.assert_allclose(np.abs(preset_state("bell")) ** 2, [0.5, 0, 0, 0.5], atol=1e-12)
    ghz = np.abs(preset_state("ghz")) ** 2
    assert ghz[0] == pytest.approx(0.5) and ghz[7] == pytest.approx(0.5) and ghz.sum() == pytest.approx(1.0)


def test_preset_grover_success_is_one():
    state = preset_state("grover")
    assert abs(state[3]) ** 2 == pytest.approx(1.0, abs=1e-12)  # marked item |11>
    assert state[3].real == pytest.approx(-1.0)  # a global sign only


def test_preset_kickback_control_becomes_one_and_target_stays_minus():
    payload = request(qubits=2, gates=PRESET["kickback"]["gates"])
    steps = dashboard_free_steps(payload)
    bloch = steps[-1]["bloch"]
    np.testing.assert_allclose(bloch[0], [0, 0, -1], atol=1e-12)  # q0 = |1>
    np.testing.assert_allclose(bloch[1], [-1, 0, 0], atol=1e-12)  # q1 = |->


def input_marginals(name):
    """Exact probabilities of q1 q0 (the algorithm inputs) at the end of a 3-qubit preset."""
    probabilities = np.abs(preset_state(name)) ** 2
    return cp.marginal_probabilities(probabilities, [0, 1])


def test_preset_deutsch_jozsa_constant_reads_00_and_balanced_never_does():
    np.testing.assert_allclose(input_marginals("dj_constant"), [1, 0, 0, 0], atol=1e-12)
    np.testing.assert_allclose(input_marginals("dj_balanced"), [0, 0, 0, 1], atol=1e-12)  # 11 = the parity pattern
    for name in ("dj_constant", "dj_balanced"):
        measured = sorted(g["qubits"][0] for g in PRESET[name]["gates"] if g["gate"] == "measure")
        assert measured == [0, 1]  # the histogram shows only the inputs


def test_preset_bernstein_vazirani_returns_101_with_probability_one():
    np.testing.assert_allclose(np.abs(preset_state("bv_101")) ** 2, np.eye(8)[0b101], atol=1e-12)


def test_preset_simon_outcomes_are_orthogonal_to_s():
    marginals = input_marginals("simon_11")
    np.testing.assert_allclose(marginals, [0.5, 0, 0, 0.5], atol=1e-12)
    for y, probability in enumerate(marginals):
        if probability > 1e-12:
            assert bin(y & 0b11).count("1") % 2 == 0  # y . s = 0 mod 2
    result = cp.simulate_circuit(request(qubits=3, gates=PRESET["simon_11"]["gates"], shots=2000, seed=5))
    assert result["counts"]["01"] == result["counts"]["10"] == 0
    assert result["counts"]["00"] + result["counts"]["11"] == 2000


def test_cp_gate_phases_only_the_11_component():
    state = final_state(request(qubits=2, gates=[gate("h", 0), gate("h", 1), gate("cp", 0, 1, angle=math.pi / 3)]))
    np.testing.assert_allclose(state, 0.5 * np.array([1, 1, 1, np.exp(1j * math.pi / 3)]), atol=1e-12)
    cz = final_state(request(qubits=2, gates=[gate("h", 0), gate("h", 1), gate("cz", 0, 1)]))
    cp_pi = final_state(request(qubits=2, gates=[gate("h", 0), gate("h", 1), gate("cp", 1, 0, angle=math.pi)]))
    np.testing.assert_allclose(cp_pi, cz, atol=1e-12)  # CP(pi) = CZ, and CP is symmetric in its qubits
    result = cp.simulate_circuit(request(qubits=2, gates=[gate("x", 0), gate("x", 1), gate("cp", 0, 1, angle=1.0)], shots=16))
    assert result["counts"]["11"] == 16  # the Aer path accepts CP
    assert result["steps"][-1]["label"].startswith("CP (")


def test_preset_qft_period2_gives_peaks_at_0_and_4():
    np.testing.assert_allclose(np.abs(preset_state("qft_period2")) ** 2, [0.5, 0, 0, 0, 0.5, 0, 0, 0], atol=1e-12)
    qft = QuantumCircuit(3)
    for item in PRESET["qft_period2"]["gates"][2:]:
        getattr(qft, item["gate"])(*([item["angle"]] if "angle" in item else []), *item["qubits"])
    from qiskit.circuit.library import QFTGate
    from qiskit.quantum_info import Operator
    np.testing.assert_allclose(Operator(qft).data, Operator(QFTGate(3)).data, atol=1e-12)  # the preset's QFT is the QFT


def test_preset_qpe_s_reads_01_with_probability_one():
    np.testing.assert_allclose(input_marginals("qpe_s"), [0, 1, 0, 0], atol=1e-12)  # m = 1: phase 1/4
    assert abs(preset_state("qpe_s")[0b101]) ** 2 == pytest.approx(1.0)  # the eigenstate |1> on q2 is untouched
    result = cp.simulate_circuit(request(qubits=3, gates=PRESET["qpe_s"]["gates"], shots=500, seed=9))
    assert result["counts"] == {"00": 0, "01": 500, "10": 0, "11": 0}


def test_ccz_flips_only_the_111_component_on_any_qubit_order():
    for wires in ([0, 1, 2], [2, 0, 1]):
        state = final_state(request(qubits=3, gates=[gate("h", 0), gate("h", 1), gate("h", 2), gate("ccz", *wires)]))
        expected = np.full(8, 8**-0.5)
        expected[7] *= -1
        np.testing.assert_allclose(state, expected, atol=1e-12)
    result = cp.simulate_circuit(request(qubits=3, gates=[gate("x", 0), gate("x", 1), gate("x", 2), gate("ccz", 0, 1, 2)], shots=8))
    assert result["counts"]["111"] == 8 and result["steps"][-1]["label"] == "CCZ on q0,q1,q2"


def test_ccx_flips_the_target_only_when_both_controls_are_one():
    for controls, expected in (((0, 0), 0b000), ((1, 0), 0b010), ((0, 1), 0b100), ((1, 1), 0b111)):
        prep = [gate("x", q) for q, bit in zip((1, 2), controls) if bit]
        state = final_state(request(qubits=3, gates=[*prep, gate("ccx", 1, 2, 0)]))
        assert abs(state[expected]) == pytest.approx(1.0), controls
    result = cp.simulate_circuit(request(qubits=3, gates=[gate("x", 0), gate("x", 1), gate("ccx", 0, 1, 2)], shots=8))
    assert result["counts"]["111"] == 8 and result["steps"][-1]["label"] == "CCX on q0,q1,q2"


def test_preset_bitflip_code_recovers_the_state_after_one_flip():
    preset = PRESET["bitflip_code"]
    assert [g["gate"] for g in preset["gates"]].count("x") == 1  # exactly one injected error
    state = preset_state("bitflip_code")
    theta = 2 * math.pi / 3
    np.testing.assert_allclose(cp.bloch_vectors(state, 3)[0], [math.sin(theta), 0, math.cos(theta)], atol=1e-12)  # q0 = |psi>
    np.testing.assert_allclose(cp.bloch_vectors(state, 3)[1], [0, 0, -1], atol=1e-12)  # syndrome q1 = 1
    np.testing.assert_allclose(cp.bloch_vectors(state, 3)[2], [0, 0, -1], atol=1e-12)  # syndrome q2 = 1
    without_fix = final_state(request(qubits=3, gates=preset["gates"][:-2]))  # drop the Toffoli (and measure)
    assert cp.bloch_vectors(without_fix, 3)[0][2] == pytest.approx(-math.cos(theta))  # the flip would remain
    result = cp.simulate_circuit(request(qubits=3, gates=preset["gates"], shots=4000, seed=6))
    assert result["measured_qubits"] == [0]
    np.testing.assert_allclose(result["measured_probabilities"], [0.25, 0.75], atol=1e-12)
    assert abs(result["counts"]["1"] / 4000 - 0.75) < 0.03


def test_preset_grover3_finds_111_and_fits_the_gate_cap():
    preset = PRESET["grover3"]
    assert len(preset["gates"]) == 19 <= cp.MAX_GATES == 30
    probabilities = np.abs(preset_state("grover3")) ** 2
    assert probabilities[7] == pytest.approx(math.sin(5 * math.asin(8**-0.5)) ** 2, abs=1e-12)  # 0.945, 2 iterations
    assert probabilities[7] > 0.94
    # RY(pi/2) is exactly "H then X", and RY(-pi/2) is exactly "X then H" (no global phase).
    h = np.array([[1, 1], [1, -1]]) / np.sqrt(2)
    x = np.array([[0, 1], [1, 0]])
    np.testing.assert_allclose(cp.rotation_matrix("ry", math.pi / 2), x @ h, atol=1e-12)
    np.testing.assert_allclose(cp.rotation_matrix("ry", -math.pi / 2), h @ x, atol=1e-12)


def dashboard_free_steps(payload):
    parameters = cp.parse_circuit_request(payload)
    states = cp.circuit_states(parameters)
    return [cp._step(i, "", s, parameters["qubits"]) for i, s in enumerate(states)]


# --------------------------------------------------------------- Bloch vectors

def test_bloch_vectors_of_known_states():
    def vector(gates):
        return cp.bloch_vectors(final_state(request(gates=gates)), 1)[0]

    np.testing.assert_allclose(vector([]), [0, 0, 1], atol=1e-12)
    np.testing.assert_allclose(vector([gate("x", 0)]), [0, 0, -1], atol=1e-12)
    np.testing.assert_allclose(vector([gate("h", 0)]), [1, 0, 0], atol=1e-12)  # |+> -> +x
    np.testing.assert_allclose(vector([gate("h", 0), gate("s", 0)]), [0, 1, 0], atol=1e-12)  # |+i> -> +y
    np.testing.assert_allclose(vector([gate("h", 0), gate("z", 0)]), [-1, 0, 0], atol=1e-12)


def test_bloch_length_is_one_for_product_states_and_zero_for_entangled():
    product = final_state(request(qubits=3, gates=[gate("h", 0), gate("ry", 1, angle=0.7), gate("x", 2)]))
    for vector in cp.bloch_vectors(product, 3):
        assert np.linalg.norm(vector) == pytest.approx(1.0)
    for name, count in (("bell", 2), ("ghz", 3)):
        for vector in cp.bloch_vectors(preset_state(name), count):
            assert np.linalg.norm(vector) == pytest.approx(0.0, abs=1e-12)
    # a CZ between |+> and |+> entangles; partially rotated control gives 0 < |r| < 1
    partial = final_state(request(qubits=2, gates=[gate("ry", 0, angle=0.6), gate("h", 1), gate("cz", 0, 1)]))
    lengths = [np.linalg.norm(v) for v in cp.bloch_vectors(partial, 2)]
    assert all(0.0 < length < 1.0 for length in lengths)


def test_bloch_vectors_follow_qubit_indices():
    state = final_state(request(qubits=2, gates=[gate("x", 1)]))
    vectors = cp.bloch_vectors(state, 2)
    np.testing.assert_allclose(vectors[0], [0, 0, 1], atol=1e-12)
    np.testing.assert_allclose(vectors[1], [0, 0, -1], atol=1e-12)


# --------------------------------------------------------------- simulate_circuit

def test_simulate_circuit_result_shape_counts_and_determinism():
    payload = request(qubits=2, gates=PRESET["bell"]["gates"], shots=500, seed=11)
    first = cp.simulate_circuit(payload)
    second = cp.simulate_circuit(payload)
    assert first == second
    assert len(first["steps"]) == 3
    assert first["basis"] == ["00", "01", "10", "11"]
    assert sum(first["counts"].values()) == 500
    assert first["counts"]["01"] == 0 and first["counts"]["10"] == 0
    assert first["measured_qubits"] == [0, 1]
    np.testing.assert_allclose(first["measured_probabilities"], [0.5, 0, 0, 0.5], atol=1e-12)
    other_seed = cp.simulate_circuit({**payload, "seed": 12})
    assert other_seed["counts"] != first["counts"]
    json.dumps(first, allow_nan=False)


def test_measure_selects_the_histogram_qubits_and_marginals():
    payload = request(qubits=2, gates=[*PRESET["bell"]["gates"], gate("measure", 1)], shots=300, seed=3)
    result = cp.simulate_circuit(payload)
    assert result["measured_qubits"] == [1]
    assert result["measured_labels"] == ["0", "1"]
    np.testing.assert_allclose(result["measured_probabilities"], [0.5, 0.5], atol=1e-12)
    assert set(result["counts"]) == {"0", "1"} and sum(result["counts"].values()) == 300
    # measuring q0 only in a state with q0 = 1, q1 = 0 gives a deterministic histogram
    result = cp.simulate_circuit(request(qubits=2, gates=[gate("x", 0), gate("measure", 0)], shots=50))
    assert result["counts"] == {"0": 0, "1": 50}
    # label order: highest measured qubit on the left
    result = cp.simulate_circuit(request(qubits=3, gates=[gate("x", 2), gate("measure", 0), gate("measure", 2)], shots=20))
    assert result["counts"] == {"00": 0, "01": 0, "10": 20, "11": 0}
    np.testing.assert_allclose(result["measured_probabilities"], [0, 0, 1, 0], atol=1e-12)


def test_empty_circuit_and_aer_agree_with_exact_probabilities():
    result = cp.simulate_circuit(request(qubits=3, gates=[], shots=32))
    assert result["counts"]["000"] == 32
    result = cp.simulate_circuit(request(qubits=1, gates=[gate("h", 0)], shots=8192, seed=1))
    assert abs(result["counts"]["0"] / 8192 - 0.5) < 0.03


def test_rounding_removes_negative_zero_and_noise():
    result = cp.simulate_circuit(request(gates=[gate("h", 0), gate("h", 0)]))
    amplitudes = result["steps"][-1]["amplitudes"]
    assert amplitudes == [[1.0, 0.0], [0.0, 0.0]]
    assert math.copysign(1.0, amplitudes[1][0]) == 1.0


# -------------------------------------------------------------------- HTTP

@pytest.fixture(scope="module")
def server():
    srv = dashboard.make_server(port=0)
    thread = Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield srv
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=5)


def send(server, method, path, body=None, headers=None):
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=30)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


JSON = {"Content-Type": "application/json"}


def post_circuit(server, body, headers=JSON):
    return send(server, "POST", "/api/circuit", body if isinstance(body, str) else json.dumps(body), headers)


def test_http_circuit_happy_path(server):
    status, headers, body = post_circuit(server, request(qubits=2, gates=PRESET["bell"]["gates"], shots=128, seed=5))
    assert status == 200 and "application/json" in headers["Content-Type"]
    result = json.loads(body)
    assert sum(result["counts"].values()) == 128
    assert result["steps"][-1]["probabilities"] == pytest.approx([0.5, 0, 0, 0.5])


@pytest.mark.parametrize(
    "body,headers,expected",
    [
        ("x" * 4097, JSON, 413),
        ("{}", {"Content-Type": "text/plain"}, 415),
        ("not json", JSON, 400),
        ("[]", JSON, 400),
        ("{}", JSON, 400),
        ('{"qubits":1,"qubits":2,"gates":[],"shots":1,"seed":1}', JSON, 400),
        ('{"qubits":1,"gates":[],"shots":1,"seed":NaN}', JSON, 400),
        ('{"qubits":1,"gates":[{"gate":"rx","qubits":[0],"angle":NaN}],"shots":1,"seed":1}', JSON, 400),
        ('{"qubits":1,"gates":[{"gate":"rx","qubits":[0],"angle":Infinity}],"shots":1,"seed":1}', JSON, 400),
        ('{"qubits":1,"gates":[{"gate":"h","gate":"x","qubits":[0]}],"shots":1,"seed":1}', JSON, 400),
        (json.dumps(request(qubits=4)), JSON, 400),
        ('{"qubits":1,"gates":[{"gate":"rx","qubits":[0],"angle":1' + '0' * 400 + '}],"shots":1,"seed":1}', JSON, 400),
        ('{"qubits":1,"gates":[{"gate":"rx","qubits":[0],"angle":1e400}],"shots":1,"seed":1}', JSON, 400),
    ],
)
def test_http_circuit_rejects_bad_requests(server, body, headers, expected):
    status, _, payload = post_circuit(server, body, headers)
    assert status == expected
    assert "error" in json.loads(payload)


def test_http_body_limits_are_per_route(server):
    big_but_valid = request(qubits=3, gates=[gate("rx", 0, angle=1.2345678901234567)] * 30, shots=8192, seed=2**31 - 1)
    size = len(json.dumps(big_but_valid))
    assert 1024 < size <= cp.MAX_CIRCUIT_BODY_BYTES  # a maximal circuit needs more than the Bell cap
    status, _, _ = post_circuit(server, big_but_valid)
    assert status == 200
    status, _, _ = send(server, "POST", "/api/bell", "x" * 1025, JSON)
    assert status == 413  # the Bell cap is unchanged


def test_http_unknown_post_routes_and_methods(server):
    for path in ("/api/other", "/api/circuit/", "/api/circuit?x=1", "/"):
        status, _, _ = send(server, "POST", path, "{}", JSON)
        assert status in (400, 404)
    status, _, _ = send(server, "PUT", "/api/circuit", "{}")
    assert status == 405
    status, _, _ = send(server, "GET", "/api/circuit")
    assert status == 404


def test_http_presets_route_is_static_and_never_simulates(server, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("presets must not simulate")

    monkeypatch.setattr(dashboard, "simulate_circuit", unexpected)
    monkeypatch.setattr(dashboard, "simulate_bell", unexpected)
    status, headers, body = send(server, "GET", "/api/circuit-presets")
    assert status == 200 and "application/json" in headers["Content-Type"]
    assert len(json.loads(body)["presets"]) == 15
    status, _, _ = send(server, "GET", "/api/circuit-presets?x=1")
    assert status == 400


def test_http_circuit_route_rejects_foreign_host_and_origin(server):
    for extra in ({"Host": "example.com"}, {"Origin": "https://example.com"}):
        status, _, _ = post_circuit(server, request(), {**JSON, **extra})
        assert status == 403
