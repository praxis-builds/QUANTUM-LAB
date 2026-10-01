"use strict";
// Pure-logic tests for SecurityCore (no DOM). Run: node tests/js/security_core.test.js
const assert = require("node:assert/strict");
const path = require("node:path");
const C = require(path.join(__dirname, "..", "..", "src", "praxis_quantum_lab", "dashboard_assets", "security.js"));

// requests are clamped to the server's limits and use the exact field sets
assert.deepEqual(C.bb84Request({qubits: "50", noise: "0.9", sample: "99999", eve: 1, seed: -5}), {qubits: 200, noise: 0.2, sample: 2000, eve: true, seed: 0});
assert.deepEqual(Object.keys(C.bb84Request({})).sort(), ["eve", "noise", "qubits", "sample", "seed"]);
assert.deepEqual(C.rsaRequest({n: "15", seed: "3"}), {n: 15, seed: 3});
assert.equal(C.rsaRequest({n: "33", seed: 1}).n, 21);
assert.deepEqual(C.groverRequest({key: "20", iterations: "-1", pairs: "1", seed: "4"}), {key: 15, iterations: 0, pairs: 1, seed: 4});
assert.equal(C.groverRequest({pairs: "7"}).pairs, 2);

// Mosca: at risk exactly when x + y > z
assert.equal(C.moscaVerdict(10, 5, 9).atRisk, true);
assert.match(C.moscaVerdict(10, 5, 9).text, /6 years overdue/);
assert.equal(C.moscaVerdict(4, 5, 9).atRisk, false);  // 9 > 9 is false
assert.match(C.moscaVerdict(1, 1, 9).text, /7 years of slack/);
assert.equal(C.moscaVerdict("x", 1, 1).valid, false);
assert.equal(C.moscaVerdict(-1, 1, 1).valid, false);

// chart geometry
assert.deepEqual(C.chartPoints([0, 1], 100, 50, 10), [[10, 40], [90, 10]]);
assert.equal(C.percent(0.25), "25.0%");
process.stdout.write("SECURITY-CORE-OK");
