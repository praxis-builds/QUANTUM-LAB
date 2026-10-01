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
const sentSeeds = [];
globalThis.fetch = async (url, options = {}) => {
  if ((options.method || "GET") === "POST") { posts++; sentSeeds.push([url, JSON.parse(options.body).seed]); }
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
  $("bb84-seed").value = "20260928"; $("grover-seed").value = "20260928";
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
  assert.deepEqual(sentSeeds.at(-1), ["/api/security/bb84", 20260928]);
  // A seed the API would reject is refused in the form: nothing is sent.
  for (const bad of ["", "-1", "1.5", "2147483648", "abc"]) {
    $("bb84-seed").value = bad;
    const before = posts;
    $("bb84-form").dispatch("submit");
    await until(() => /Seed must be a whole number from 0 to 2147483647/.test($("bb84-status").textContent), `bad seed ${bad}`);
    assert.equal(posts, before, `seed ${bad} must not be sent`);
    assert.equal($("bb84-run").disabled, false);
  }
  // "New seed" writes a valid seed into the field, and that seed is the one sent.
  $("bb84-new-seed").click();
  const fresh = Number($("bb84-seed").value);
  assert.ok(Number.isInteger(fresh) && fresh >= 0 && fresh <= 2147483647 && String(fresh) === $("bb84-seed").value);
  $("bb84-status").textContent = "";
  $("bb84-form").dispatch("submit");
  await until(() => /Secret key distilled|ABORT|Error/.test($("bb84-status").textContent), () => `bb84 new seed (${$("bb84-status").textContent})`);
  assert.deepEqual(sentSeeds.at(-1), ["/api/security/bb84", fresh]);
  $("bb84-seed").value = "20260928";
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
  assert.deepEqual(sentSeeds.at(-1), ["/api/security/rsa", 3]);
  $("rsa-new-seed").click();
  assert.match($("rsa-seed").value, /^\d{1,10}$/);

  // Grover: at the optimum, then past it.
  $("grover-form").dispatch("submit");
  await until(() => /secret key came out|Error/.test($("grover-status").textContent), () => `grover (${$("grover-status").textContent})`);
  assert.ok($("grover-chart").children.length >= 4, "chart drawn");
  assert.deepEqual(sentSeeds.at(-1), ["/api/security/grover", 20260928]);
  $("grover-new-seed").click();
  assert.match($("grover-seed").value, /^\d{1,10}$/);
  $("grover-seed").value = "5";
  assert.match($("grover-explain").textContent, /Best: 3 iterations\./);
  $("grover-iterations").value = "6"; $("grover-iterations").dispatch("input");
  assert.equal($("grover-iterations-output").textContent, "6");
  $("grover-form").dispatch("submit");
  await until(() => /6 iterations/.test($("grover-status").textContent), "grover over-rotation");
  assert.deepEqual(sentSeeds.at(-1), ["/api/security/grover", 5]);
  assert.match($("grover-explain").textContent, /over-rotation/);
  process.stdout.write("SECURITY-UI-SMOKE-OK");
})().catch((error) => { console.error(error); process.exit(1); });
