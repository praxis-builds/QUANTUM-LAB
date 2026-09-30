"use strict";
// Pure-logic tests for PlaygroundCore (no DOM). Run: node tests/js/playground_core.test.js
const assert = require("node:assert/strict");
const path = require("node:path");
const C = require(path.join(__dirname, "..", "..", "src", "praxis_quantum_lab", "dashboard_assets", "playground.js"));

const g = (gate, qubits, angle) => (angle === undefined ? {gate, qubits} : {gate, qubits, angle});
const close = (a, b, tol = 1e-9) => assert.ok(Math.abs(a - b) <= tol, `${a} != ${b}`);

// layout: parallel gates share a column; a two-qubit gate reserves the wires it crosses
assert.deepEqual(C.layoutColumns([g("h", [0]), g("h", [1])]), [0, 0]);
assert.deepEqual(C.layoutColumns([g("h", [0]), g("cx", [0, 1]), g("h", [1])]), [0, 1, 2]);
assert.deepEqual(C.layoutColumns([g("cx", [0, 2]), g("h", [1])]), [0, 1]);
assert.deepEqual(C.layoutColumns([]), []);

// placement rules mirror the server
assert.equal(C.placementProblem([], g("h", [0]), 1), null);
assert.match(C.placementProblem([g("measure", [0])], g("h", [0]), 1), /already measured/);
assert.equal(C.placementProblem([g("measure", [0])], g("h", [1]), 2), null);
assert.match(C.placementProblem(Array(30).fill(g("h", [0])), g("h", [0]), 1), /full \(30 gates\)/);
assert.match(C.placementProblem([], g("cx", [1, 1]), 2), /different qubits/);
assert.match(C.placementProblem([], g("h", [2]), 2), /inside the circuit/);
assert.match(C.placementProblem([], g("rx", [0], 5 * Math.PI), 1), /angle/);
assert.equal(C.placementProblem([], g("rx", [0], -4 * Math.PI), 1), null);
assert.deepEqual(C.keepWithinQubits([g("h", [0]), g("cx", [0, 2]), g("x", [1])], 2), [g("h", [0]), g("x", [1])]);

// request body: only allowed keys; angle only for rotations
const body = C.buildRequest(2, [{gate: "h", qubits: [0], angle: 1, extra: 1}, g("ry", [1], 0.5)], 64, 7);
assert.deepEqual(body, {qubits: 2, gates: [g("h", [0]), g("ry", [1], 0.5)], shots: 64, seed: 7});
assert.notEqual(C.circuitKey(1, [g("h", [0])]), C.circuitKey(2, [g("h", [0])]));

// shots slider is logarithmic and covers exactly 1..8192
assert.equal(C.shotsFromSlider(0), 1);
assert.equal(C.shotsFromSlider(100), 8192);
for (let v = 1; v <= 100; v++) assert.ok(C.shotsFromSlider(v) >= C.shotsFromSlider(v - 1));
assert.equal(C.sliderFromShots(1024), 77);
for (const [text, expected] of [["12", 12], [" 8192 ", 8192], ["1.5", null], ["-1", null], ["", null], ["1e3", null], ["8193", null], ["abc", null]]) {
  assert.equal(C.parseBoundedInt(text, 1, 8192), expected, text);
}

// labels and colours
assert.equal(C.piLabel(Math.PI / 2), "π/2");
assert.equal(C.piLabel(-Math.PI), "−π");
assert.equal(C.piLabel(0), "0");
assert.equal(C.piLabel(2 * Math.PI), "2π");
assert.equal(C.piLabel(3 * Math.PI / 4), "3π/4");
close(C.phaseHue(0), 170);
close(C.phaseHue(Math.PI), 350);
close(Math.abs(C.phaseHue(Math.PI) - C.phaseHue(0)), 180);
assert.notEqual(C.phaseColor(0.7, 0), C.phaseColor(-0.7, 0));
assert.equal(C.phaseColor(0, 0), "hsl(215 12% 45%)");
assert.equal(C.formatAmplitude(-Math.SQRT1_2, 0), "−0.707");
assert.equal(C.formatAmplitude(Math.SQRT1_2, 0), "+0.707");
assert.equal(C.formatAmplitude(0, Math.SQRT1_2), "+0.707i");
assert.equal(C.formatAmplitude(0.5, 0.5), "0.707∠π/4");
assert.equal(C.formatAmplitude(1e-9, -1e-9), "0");

// Bloch projection: default view puts |0> up, +y right, +x toward the viewer (down-left); lengths preserved
const view = {az: -0.5, el: 0.35};
const pz = C.project([0, 0, 1], view.az, view.el), py = C.project([0, 1, 0], view.az, view.el), px = C.project([1, 0, 0], view.az, view.el);
assert.ok(pz.v > 0.9 && Math.abs(pz.h) < 1e-12);
assert.ok(py.h > 0.8);
assert.ok(px.h < 0 && px.v < 0 && px.depth > 0);
for (const v of [[1, 0, 0], [0, 1, 0], [0, 0, 1], [0.6, -0.48, 0.64]]) {
  const p = C.project(v, 1.3, -0.7);
  close(p.h ** 2 + p.v ** 2 + p.depth ** 2, v.reduce((s, c) => s + c * c, 0));
}

// initial state and notes
const start = C.initialStep(3);
assert.equal(start.amplitudes.length, 8);
assert.deepEqual(start.bloch, [[0, 0, 1], [0, 0, 1], [0, 0, 1]]);
assert.equal(start.label, "Start |000⟩");
assert.deepEqual(C.basisLabels(2), ["00", "01", "10", "11"]);
assert.equal(C.blochNote(1), "pure state of its own");
assert.equal(C.blochNote(0), "entangled: this qubit has no pure state of its own");
assert.equal(C.blochNote(0.5), "entangled: this qubit has no pure state of its own");
assert.equal(C.describeGate(g("cx", [0, 1])), "CNOT control q0 → target q1");
assert.equal(C.describeGate(g("rz", [2], Math.PI / 4)), "RZ(π/4) on q2");
assert.equal(C.describeGate(g("cp", [0, 2], -Math.PI / 2)), "CP(−π/2) control q0 → target q2");
assert.equal(C.describeGate(g("ccz", [0, 1, 2])), "CCZ on q0, q1, q2");
assert.equal(C.describeGate(g("ccx", [1, 2, 0])), "CCX controls q1, q2 → target q0");
assert.match(C.placementProblem([], g("ccx", [1, 1, 0]), 3), /different qubits/);
assert.match(C.placementProblem([], g("ccz", [0, 1, 1]), 3), /different qubits/);
assert.match(C.placementProblem([], g("ccz", [0, 1, 2]), 2), /inside the circuit/);
assert.equal(C.placementProblem([], g("ccz", [2, 0, 1]), 3), null);
assert.match(C.placementProblem([], g("cp", [0, 1], 5 * Math.PI), 2), /angle/);
assert.equal(C.placementProblem([], g("cp", [0, 1], Math.PI / 4), 2), null);
close(C.largestGap({"0": 60, "1": 40}, ["0", "1"], [0.5, 0.5], 100), 0.1);

// constants for the Python cross-check
process.stdout.write(JSON.stringify({MAX_QUBITS: C.MAX_QUBITS, MAX_GATES: C.MAX_GATES, MAX_SHOTS: C.MAX_SHOTS, MAX_SEED: C.MAX_SEED, PALETTE: C.PALETTE, ANGLE: Object.keys(C.GATES).filter((k) => C.GATES[k].angle), TWO: Object.keys(C.GATES).filter((k) => C.GATES[k].arity === 2), THREE: Object.keys(C.GATES).filter((k) => C.GATES[k].arity === 3)}));
