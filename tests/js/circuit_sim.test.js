"use strict";
// The JavaScript Playground simulator against the Python one (tests/fixtures/playground_states.json):
// every preset step and 50 random circuits agree to 1e-12, the validator accepts and rejects the same
// requests with the same messages, and browser sampling is seeded and sound.
// Run: node tests/js/circuit_sim.test.js
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const S = require(path.join(__dirname, "..", "..", "src", "praxis_quantum_lab", "dashboard_assets", "circuit_sim.js"));
const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "fixtures", "playground_states.json"), "utf8"));
const TOL = 1e-12;
let compared = 0;

function close(actual, expected, where) {
  assert.ok(Math.abs(actual - expected) <= TOL, `${where}: ${actual} vs ${expected} (diff ${Math.abs(actual - expected)})`);
  compared += 1;
}

function check(name, record) {
  const parameters = S.parseRequest({qubits: record.qubits, gates: record.gates, shots: 1, seed: 0});
  const states = S.circuitStates(parameters);
  assert.deepEqual(record.gates.map(S.gateLabel), record.labels, `${name}: labels`);
  for (const [index, expected] of Object.entries(record.steps)) {
    const state = states[Number(index)];
    expected.amplitudes.forEach(([re, im], i) => { close(state.re[i], re, `${name} step ${index} re[${i}]`); close(state.im[i], im, `${name} step ${index} im[${i}]`); });
    S.probabilities(state).forEach((p, i) => close(p, expected.probabilities[i], `${name} step ${index} p[${i}]`));
    S.blochVectors(state, record.qubits).forEach((v, q) => v.forEach((c, k) => close(c, expected.bloch[q][k], `${name} step ${index} bloch q${q}[${k}]`)));
  }
  const result = S.simulate({qubits: record.qubits, gates: record.gates, shots: 100, seed: 7});
  assert.deepEqual(result.measured_qubits, record.measured_qubits, `${name}: measured qubits`);
  result.measured_probabilities.forEach((p, i) => assert.ok(Math.abs(p - record.measured_probabilities[i]) <= 1e-12, `${name}: marginal`));
}

for (const [id, record] of Object.entries(fixture.presets)) check(`preset ${id}`, record);
fixture.random.forEach((record, i) => check(`random #${i}`, record));
assert.equal(Object.keys(fixture.presets).length >= 17, true);
assert.equal(fixture.random.length, 50);

// Validation parity: the same verdict and the same message as the Python validator.
for (const {payload, accepted, error} of fixture.validation) {
  let message = null;
  try { S.parseRequest(payload); } catch (e) { assert.ok(e instanceof S.RequestError, String(e)); message = e.message; }
  assert.equal(message === null, accepted, `accepted mismatch for ${JSON.stringify(payload)}`);
  if (!accepted) assert.equal(message, error, `message for ${JSON.stringify(payload)}`);
}

// Responses have the server's fields plus the sampler label.
const bell = S.simulate({qubits: 2, gates: [{gate: "h", qubits: [0]}, {gate: "cx", qubits: [0, 1]}], shots: 8192, seed: 20260928});
for (const key of ["qubits", "gates", "shots", "seed", "basis", "basis_convention", "steps", "measured_qubits", "measured_labels", "measured_probabilities", "counts"]) {
  assert.ok(key in bell, key);
}
assert.equal(bell.sampler, "browser sampling, not Aer");
assert.deepEqual(bell.steps.map((s) => s.label), ["Start |00⟩", "H on q0", "CX on q0,q1"]);
assert.deepEqual(bell.steps[2].bloch_length, [0, 0]);

// Sampling: seeded (same seed, same counts), complete, and statistically sound (within 5 sigma).
const again = S.simulate({qubits: 2, gates: [{gate: "h", qubits: [0]}, {gate: "cx", qubits: [0, 1]}], shots: 8192, seed: 20260928});
assert.deepEqual(again.counts, bell.counts);
assert.equal(Object.values(bell.counts).reduce((a, b) => a + b, 0), 8192);
assert.equal(bell.counts["01"] + bell.counts["10"], 0);
const sigma = Math.sqrt(8192 * 0.25);
assert.ok(Math.abs(bell.counts["00"] - 4096) < 5 * sigma, `00: ${bell.counts["00"]}`);
const other = S.simulate({qubits: 2, gates: [{gate: "h", qubits: [0]}, {gate: "cx", qubits: [0, 1]}], shots: 8192, seed: 1});
assert.notDeepEqual(other.counts, bell.counts);
const random = S.prng(42), draws = Array.from({length: 20000}, random);
assert.ok(draws.every((x) => x >= 0 && x < 1));
assert.ok(Math.abs(draws.reduce((a, b) => a + b, 0) / draws.length - 0.5) < 0.01);

// %.3g as Python formats it
assert.deepEqual([0.5, 0.25, 1 / 3, 1, -0.5, 4, 1.23456, 0.0001234, 0.00001234, 123.4].map(S.formatG3),
                 ["0.5", "0.25", "0.333", "1", "-0.5", "4", "1.23", "0.000123", "1.23e-05", "123"]);
process.stdout.write(`CIRCUIT-SIM-OK ${compared}`);
