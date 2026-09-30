"use strict";
// Drives the real playground.js UI code on the DOM stub, against a real local dashboard server.
// Usage: node tests/js/playground_ui_smoke.js <port>
const assert = require("node:assert/strict");
const path = require("node:path");
const {createEnvironment} = require("./dom_stub.js");

const port = Number(process.argv[2]);
assert.ok(Number.isInteger(port) && port > 0, "pass the dashboard port");
const base = `http://127.0.0.1:${port}`;
const env = createEnvironment();
const calls = [];
let inject429 = 0;
globalThis.__realFetch = globalThis.fetch;
globalThis.document = env.document;
globalThis.getComputedStyle = env.getComputedStyle;
globalThis.fetch = async (url, options = {}) => {
  calls.push({url, method: options.method || "GET"});
  if (inject429 > 0 && url === "/api/circuit") {
    inject429 -= 1;
    return {ok: false, status: 429, json: async () => ({error: "busy"})};
  }
  const response = await fetch.real(`${base}${url}`, {method: options.method || "GET", headers: options.headers, body: options.body});
  return {ok: response.ok, status: response.status, json: () => response.json()};
};
fetch.real = globalThis.__realFetch;

const $ = (id) => env.document.getElementById(id);
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
async function until(check, label, timeout = 20000) {
  const start = Date.now();
  while (Date.now() - start < timeout) { if (check()) return; await sleep(20); }
  throw new Error(`timed out waiting for: ${typeof label === "function" ? label() : label}`);
}
const circuitCalls = () => calls.filter((c) => c.url === "/api/circuit").length;
const buttonIn = (id, text) => $(id).children.find((b) => b.textContent === text);
async function settled() {
  // Idle means: no debounce timer pending, nothing in flight, nothing queued.
  await until(() => ["UP TO DATE", "IDLE · NOTHING SIMULATED YET"].includes($("pg-busy").textContent),
    () => `settled (badge ${$("pg-busy").textContent}, error "${$("pg-error").textContent}")`);
}
const ampLabel = () => $("pg-amplitudes").getAttribute("aria-label");
const probLabel = () => $("pg-probabilities").getAttribute("aria-label");
const sphereNotes = () => $("pg-bloch").findAll((n) => n.tagName === "FIGCAPTION").map((c) => c.textContent);
const gateGroups = () => $("pg-circuit").children.filter((n) => n.classList.contains("pg-gate"));

(async () => {
  require(path.join(__dirname, "..", "..", "src", "praxis_quantum_lab", "dashboard_assets", "playground.js"));

  // First load: presets arrive by GET, nothing is simulated, the |00> state is drawn locally.
  await until(() => $("pg-preset-buttons").children.length === 15, "presets");
  await sleep(300);
  assert.equal(circuitCalls(), 0, "first load must not simulate");
  assert.match($("pg-status").textContent, /Nothing has been simulated yet/);
  assert.match(ampLabel(), /\|00⟩ \+1\.000/);
  assert.equal(sphereNotes().length, 2);
  assert.match($("pg-busy").textContent, /IDLE/);
  assert.match($("pg-histogram-caption").textContent, /No shots yet/);

  // Bell preset: amplitudes, entangled Bloch notes, histogram.
  buttonIn("pg-preset-buttons", "Bell state").click();
  await settled();
  assert.equal(circuitCalls(), 1);
  assert.match(ampLabel(), /\|00⟩ \+0\.707, \|11⟩ \+0\.707/);
  assert.match($("pg-preset-caption").textContent, /always agree/);
  for (const note of sphereNotes()) assert.match(note, /entangled: this qubit has no pure state of its own/);
  assert.match($("pg-histogram-caption").textContent, /1,024 shots/);
  assert.equal(gateGroups().length, 2);
  assert.match($("pg-step-label").textContent, /Step 2 \/ 2/);

  // Step mode replays without new requests.
  $("pg-step-first").click();
  assert.match($("pg-step-label").textContent, /Step 0 \/ 2/);
  assert.match(ampLabel(), /\|00⟩ \+1\.000/);
  $("pg-step-next").click();
  assert.match($("pg-step-label").textContent, /Step 1 \/ 2 · H on q0/);
  assert.match(ampLabel(), /\|00⟩ \+0\.707, \|01⟩ \+0\.707/);
  for (const note of sphereNotes()) assert.match(note, /pure state of its own/);
  assert.ok(gateGroups()[0].classList.contains("pg-current"));
  assert.ok(gateGroups()[1].classList.contains("pg-future"));
  $("pg-step").value = "2"; $("pg-step").dispatch("input");
  assert.match($("pg-step-label").textContent, /Step 2 \/ 2/);
  assert.equal(circuitCalls(), 1, "stepping must not re-request");

  // Interference, phase and Grover presets.
  buttonIn("pg-preset-buttons", "Interference (H·H)").click();
  await settled();
  assert.match(ampLabel(), /Amplitudes: \|0⟩ \+1\.000;/);
  buttonIn("pg-preset-buttons", "Phase is invisible until H (H·Z·H)").click();
  await settled();
  $("pg-step").value = "2"; $("pg-step").dispatch("input");
  assert.match(ampLabel(), /\|0⟩ \+0\.707, \|1⟩ −0\.707/);
  buttonIn("pg-preset-buttons", "Grover search on 2 qubits").click();
  await settled();
  assert.match(probLabel(), /Probabilities: \|11⟩ 1\.000\./);
  assert.match(ampLabel(), /\|11⟩ −1\.000/);
  buttonIn("pg-preset-buttons", "GHZ (3 qubits)").click();
  await settled();
  assert.equal($("pg-qubits").value, "3");
  assert.match(probLabel(), /\|000⟩ 0\.500, \|111⟩ 0\.500/);
  assert.equal(sphereNotes().length, 3);
  buttonIn("pg-preset-buttons", "Bernstein–Vazirani (s = 101)").click();
  await settled();
  assert.match(probLabel(), /Probabilities: \|101⟩ 1\.000\./);
  assert.match($("pg-preset-caption").textContent, /reads out s = 101/);
  buttonIn("pg-preset-buttons", "Phase estimation of S").click();
  await settled();
  assert.match($("pg-histogram-caption").textContent, /shots/);
  assert.match($("pg-preset-caption").textContent, /01 = 1\/4/);
  assert.match(probLabel(), /Probabilities: \|101⟩ 1\.000\./);
  buttonIn("pg-preset-buttons", "Grover search on 3 qubits").click();
  await settled();
  assert.match(probLabel(), /\|111⟩ 0\.945/);
  assert.match($("pg-gate-count").textContent, /^19 \/ 30 GATES/);
  buttonIn("pg-preset-buttons", "Bit-flip code: one error fixed").click();
  await settled();
  assert.match($("pg-preset-caption").textContent, /One flipped qubit, recovered/);
  assert.match(probLabel(), /\|110⟩ 0\.250, \|111⟩ 0\.750/);

  // Build by hand on 1 qubit with the palette and placement buttons.
  $("pg-reset").click();
  $("pg-qubits").value = "1"; $("pg-qubits").dispatch("change", {target: $("pg-qubits")});
  assert.equal(sphereNotes().length, 1);
  assert.ok(buttonIn("pg-palette-buttons", "CNOT").disabled, "two-qubit gates disabled on one qubit");
  buttonIn("pg-palette-buttons", "RY").click();
  assert.equal($("pg-angle-row").hidden, false);
  $("pg-angle").value = "0.5"; $("pg-angle").dispatch("input", {target: $("pg-angle")});
  buttonIn("pg-place-buttons", "q0").click();
  await settled();
  assert.match($("pg-status").textContent, /Added RY\(π\/2\) on q0/);
  assert.match(ampLabel(), /\|0⟩ \+0\.707, \|1⟩ \+0\.707/);

  // Measurement rule: nothing after M on that wire.
  buttonIn("pg-palette-buttons", "M").click();
  buttonIn("pg-place-buttons", "q0").click();
  buttonIn("pg-palette-buttons", "H").click();
  buttonIn("pg-place-buttons", "q0").click();
  assert.equal($("pg-error").hidden, false);
  assert.match($("pg-error").textContent, /already measured/);
  await settled();
  assert.match($("pg-histogram-caption").textContent, /measured q0/);

  // Remove a gate by clicking it, then by keyboard; undo restores.
  gateGroups()[1].click();
  assert.equal(gateGroups().length, 1);
  gateGroups()[0].dispatch("keydown", {key: "Delete"});
  assert.equal(gateGroups().length, 0);
  $("pg-undo").click();
  assert.equal(gateGroups().length, 1);
  await settled();

  // Two-qubit gates: control then target, and drag-and-drop onto a wire.
  $("pg-qubits").value = "2"; $("pg-qubits").dispatch("change", {target: $("pg-qubits")});
  buttonIn("pg-palette-buttons", "H").click();
  buttonIn("pg-place-buttons", "q1").click();
  buttonIn("pg-palette-buttons", "CNOT").click();
  buttonIn("pg-place-buttons", "q1").click();
  assert.match($("pg-place-prompt").textContent, /control q1; choose the target/);
  buttonIn("pg-place-buttons", "q0").click();
  const transfer = {data: "", setData(type, value) { this.data = value; }, getData() { return this.data; }};
  buttonIn("pg-palette-buttons", "Z").dispatch("dragstart", {dataTransfer: transfer});
  const wires = $("pg-circuit").children.filter((n) => n.classList.contains("pg-wire-target"));
  assert.equal(wires.length, 2);
  wires[0].dispatch("dragover");
  wires[0].dispatch("drop", {dataTransfer: transfer});
  await settled();
  assert.match($("pg-gate-count").textContent, /^4 \/ 30 GATES/);  // RY (restored by undo), H, CNOT, Z
  assert.match($("pg-status").textContent, /Added Z on q0/);

  // A three-qubit CCZ: three clicks, with a prompt for each.
  $("pg-qubits").value = "3"; $("pg-qubits").dispatch("change", {target: $("pg-qubits")});
  buttonIn("pg-palette-buttons", "CCZ").click();
  buttonIn("pg-place-buttons", "q2").click();
  buttonIn("pg-place-buttons", "q2").click();
  assert.match($("pg-error").textContent, /different qubit/);
  buttonIn("pg-place-buttons", "q0").click();
  assert.match($("pg-place-prompt").textContent, /first qubit q2, second qubit q0; choose the third qubit/);
  buttonIn("pg-place-buttons", "q1").click();
  await settled();
  assert.match($("pg-status").textContent, /Added CCZ on q2, q0, q1/);
  assert.match($("pg-gate-count").textContent, /^5 \/ 30 GATES/);
  $("pg-undo").click();
  await settled();
  $("pg-qubits").value = "2"; $("pg-qubits").dispatch("change", {target: $("pg-qubits")});
  await settled();

  // Rotating a Bloch sphere by keyboard and by pointer redraws without errors.
  const sphere = $("pg-bloch").find((n) => n.classList.contains("pg-sphere-svg"));
  const before = JSON.stringify(sphere.children.map((c) => c.attributes));
  sphere.dispatch("keydown", {key: "ArrowLeft"});
  sphere.dispatch("pointerdown", {clientX: 10, clientY: 10, pointerId: 1});
  sphere.dispatch("pointermove", {clientX: 60, clientY: 30, pointerId: 1});
  sphere.dispatch("pointerup", {pointerId: 1});
  assert.notEqual(JSON.stringify(sphere.children.map((c) => c.attributes)), before);

  // Shots and seed: validation, then convergence of the histogram with many shots.
  $("pg-shots").value = "0"; $("pg-shots").dispatch("change", {target: $("pg-shots")});
  assert.match($("pg-error").textContent, /Shots must be/);
  $("pg-shots").value = "8192"; $("pg-shots").dispatch("change", {target: $("pg-shots")});
  await settled();
  assert.match($("pg-histogram-caption").textContent, /8,192 shots/);
  const gap = Number(/largest gap \|sampled − exact\| = ([0-9]+\.[0-9]+)/.exec($("pg-histogram-caption").textContent)[1]);
  assert.ok(gap < 0.05, `gap ${gap}`);
  $("pg-seed").value = "12345"; $("pg-seed").dispatch("change", {target: $("pg-seed")});
  await settled();
  assert.match($("pg-histogram-caption").textContent, /seed 12345/);
  $("pg-shots-range").value = "0"; $("pg-shots-range").dispatch("input", {target: $("pg-shots-range")});
  assert.equal($("pg-shots-output").textContent, "1");
  await settled();

  // Busy server (429): the playground retries and still gets the result.
  inject429 = 2;
  buttonIn("pg-preset-buttons", "Phase kickback").click();
  await settled();
  assert.equal(inject429, 0);
  assert.match(sphereNotes()[0], /r = \(0\.00, 0\.00, −?1\.00\)|r = \(0\.00, 0\.00, -1\.00\)/);

  // The 30-gate cap.
  $("pg-reset").click();
  $("pg-qubits").value = "1"; $("pg-qubits").dispatch("change", {target: $("pg-qubits")});
  buttonIn("pg-palette-buttons", "X").click();
  for (let i = 0; i < 30; i++) buttonIn("pg-place-buttons", "q0").click();
  assert.match($("pg-gate-count").textContent, /^30 \/ 30/);
  buttonIn("pg-place-buttons", "q0").click();
  assert.match($("pg-error").textContent, /full \(30 gates\)/);
  await settled();
  assert.match(probLabel(), /\|0⟩ 1\.000/);

  process.stdout.write(`UI-SMOKE-OK ${circuitCalls()} circuit requests\n`);
  process.exit(0);
})().catch((error) => { console.error(error); process.exit(1); });
