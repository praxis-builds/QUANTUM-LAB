"use strict";
// Drives the real security.js (Security Lab) on the DOM stub against a real server.
// Usage: node tests/js/security_ui_smoke.js <port>
const assert = require("node:assert/strict");
const path = require("node:path");
const {createEnvironment} = require("./dom_stub.js");

const port = Number(process.argv[2]);
const env = createEnvironment();
const realFetch = globalThis.fetch;
globalThis.document = env.document;
globalThis.getComputedStyle = env.getComputedStyle;
let posts = 0;
globalThis.fetch = async (url, options = {}) => {
  if ((options.method || "GET") === "POST") posts++;
  const response = await realFetch(`http://127.0.0.1:${port}${url}`, {method: options.method || "GET", headers: options.headers, body: options.body});
  return {ok: response.ok, status: response.status, json: () => response.json()};
};
const $ = (id) => env.document.getElementById(id);
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
async function until(check, label, timeout = 60000) {
  const start = Date.now();
  while (Date.now() - start < timeout) { if (check()) return; await sleep(20); }
  throw new Error(`timed out waiting for: ${typeof label === "function" ? label() : label}`);
}

(async () => {
  // Values index.html provides.
  Object.assign($("bb84-qubits"), {value: "4000"}); Object.assign($("bb84-noise"), {value: "0.02"});
  Object.assign($("bb84-sample"), {value: "200"}); $("bb84-eve").checked = false;
  $("rsa-n").value = "21"; $("rsa-seed").value = "3"; $("grover-iterations").value = "3"; $("grover-pairs").value = "2";
  $("mosca-x").value = "10"; $("mosca-y").value = "5"; $("mosca-z").value = "9";
  $("bb84-results").hidden = true;
  require(path.join(__dirname, "..", "..", "src", "praxis_quantum_lab", "dashboard_assets", "security.js"));

  // Loading the tab simulates nothing; Mosca is computed locally.
  await sleep(200);
  assert.equal(posts, 0, "first load must not simulate");
  assert.match($("mosca-verdict").textContent, /AT RISK: x \+ y = 15 years > z = 9/);
  $("mosca-z").value = "20"; $("mosca-z").dispatch("input");
  assert.match($("mosca-verdict").textContent, /Not yet at risk/);
  assert.equal($("grover-key").children.length, 16);
  assert.equal($("grover-key").value, "11");

  // BB84 without Eve: a key is distilled.
  $("bb84-form").dispatch("submit");
  await until(() => /Secret key distilled|ABORT|Error/.test($("bb84-status").textContent), () => `bb84 (${$("bb84-status").textContent})`);
  assert.match($("bb84-status").textContent, /Secret key distilled/);
  assert.equal($("bb84-results").hidden, false);
  assert.match($("bb84-key").textContent, /bits \(keys equal: true\)/);
  // With Eve: the protocol aborts.
  $("bb84-eve").checked = true;
  $("bb84-form").dispatch("submit");
  await until(() => /ABORT|Error/.test($("bb84-status").textContent), () => `bb84 eve (${$("bb84-status").textContent})`);
  assert.match($("bb84-key").textContent, /none: aborted/);
  assert.match($("bb84-explain").textContent, /Eve measured every qubit/);

  // Toy RSA break.
  $("rsa-form").dispatch("submit");
  await until(() => /Key recovered|Error|no factors/.test($("rsa-status").textContent), () => `rsa (${$("rsa-status").textContent})`);
  assert.match($("rsa-steps").textContent, /21 = 3 × 7|N = 3 × 7/);
  assert.match($("rsa-steps").textContent, /decrypts to "HIDE"/);

  // Grover: at the optimum, then past it.
  $("grover-form").dispatch("submit");
  await until(() => /secret key came out|Error/.test($("grover-status").textContent), () => `grover (${$("grover-status").textContent})`);
  assert.ok($("grover-chart").children.length >= 4, "chart drawn");
  assert.match($("grover-explain").textContent, /Best: 3 iterations\./);
  $("grover-iterations").value = "6"; $("grover-iterations").dispatch("input");
  assert.equal($("grover-iterations-output").textContent, "6");
  $("grover-form").dispatch("submit");
  await until(() => /6 iterations/.test($("grover-status").textContent), "grover over-rotation");
  assert.match($("grover-explain").textContent, /over-rotation/);
  process.stdout.write("SECURITY-UI-SMOKE-OK");
})().catch((error) => { console.error(error); process.exit(1); });
