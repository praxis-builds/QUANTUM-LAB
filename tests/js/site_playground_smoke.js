"use strict";
// The static site's Circuit Playground page, as built by tools/build_site.py: the real playground.js
// and security.js run on the DOM stub with the browser backend (circuit_sim.js + presets.js +
// playground_backend.js), loaded in the page's script order. Only element ids present in the built
// index.html exist, and any network call fails the test.
// Usage: node tests/js/site_playground_smoke.js <site>/playground
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {createEnvironment} = require("./dom_stub.js");

const dir = process.argv[2];
const page = fs.readFileSync(path.join(dir, "index.html"), "utf8");
const ids = new Set([...page.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]));
const scripts = [...page.matchAll(/<script src="([^"]+)" defer><\/script>/g)].map((m) => m[1]);
assert.deepEqual(scripts, ["circuit_sim.js", "presets.js", "playground_backend.js", "playground.js", "security.js"]);
assert.ok(!/<script(?![^>]*\bsrc=)/.test(page), "no inline scripts");

const env = createEnvironment();
const lookup = env.document.getElementById.bind(env.document);
env.document.getElementById = (id) => (ids.has(id) ? lookup(id) : null);
globalThis.window = globalThis;
globalThis.document = env.document;
globalThis.getComputedStyle = env.getComputedStyle;
globalThis.fetch = () => { throw new Error("the static page must not use the network"); };
const $ = (id) => env.document.getElementById(id);
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
async function until(check, label, timeout = 20000) {
  const start = Date.now();
  while (Date.now() - start < timeout) { if (check()) return; await sleep(20); }
  throw new Error(`timed out waiting for: ${typeof label === "function" ? label() : label}`);
}

(async () => {
  for (const name of scripts) {
    const exported = require(path.resolve(dir, name));
    if (name === "circuit_sim.js") globalThis.PlaygroundSim = exported;
    if (name === "security.js") globalThis.SecurityCore = exported;
  }
  await until(() => $("pg-preset-buttons").children.length === 17, "presets from presets.js");
  assert.match($("pg-status").textContent, /Nothing has been simulated yet/);

  // Bell preset, computed in the browser.
  $("pg-preset-buttons").children.find((b) => b.textContent === "Bell state").click();
  await until(() => $("pg-busy").textContent === "UP TO DATE", () => `bell (${$("pg-busy").textContent}, ${$("pg-error").textContent})`);
  assert.match($("pg-amplitudes").getAttribute("aria-label"), /\|00⟩ \+0\.707, \|11⟩ \+0\.707/);
  assert.match($("pg-histogram-caption").textContent, /browser sampling, not Aer/);
  assert.match($("pg-histogram").getAttribute("aria-label"), /00: \d+ of 1024 \(exact 0\.500\)/);
  const notes = $("pg-bloch").findAll((n) => n.tagName === "FIGCAPTION").map((c) => c.textContent);
  assert.ok(notes.every((t) => /entangled/.test(t)), notes.join(" | "));

  // A rotation and a Toffoli on 3 qubits (the bit-flip code preset), then step back to the start.
  $("pg-preset-buttons").children.find((b) => b.textContent === "Bit-flip code: one error fixed").click();
  await until(() => $("pg-busy").textContent === "UP TO DATE" && /One flipped qubit/.test($("pg-preset-caption").textContent)
    && $("pg-step").max === "8", () => `bit-flip (${$("pg-busy").textContent}, max ${$("pg-step").max}, ${$("pg-error").textContent})`);
  assert.match($("pg-histogram-caption").textContent, /measured q0/);
  $("pg-step-first").click();
  assert.match($("pg-step-label").textContent, /Step 0 \/ 8 · Start \|000⟩/);

  // An invalid edit is refused before it reaches the simulator, as on the dashboard.
  $("pg-seed").value = "-5"; $("pg-seed").dispatch("change");
  assert.match($("pg-error").textContent, /Seed must be a whole number/);

  // Mosca calculator: pure arithmetic in the page (the stub's inputs start empty, so set them).
  $("mosca-x").value = "10"; $("mosca-y").value = "5"; $("mosca-z").value = "9"; $("mosca-z").dispatch("input");
  assert.match($("mosca-verdict").textContent, /AT RISK: x \+ y = 15 years > z = 9/);
  $("mosca-x").value = "1"; $("mosca-y").value = "1"; $("mosca-z").value = "9"; $("mosca-z").dispatch("input");
  assert.match($("mosca-verdict").textContent, /Not yet at risk: x \+ y = 2 years <= z = 9/);
  process.stdout.write("SITE-PLAYGROUND-OK");
})().catch((error) => { console.error(error); process.exit(1); });
