"use strict";
// Drives the real app.js (Bell Lab + Kernel Observatory) on the DOM stub against a real server.
// Usage: node tests/js/app_ui_smoke.js <port> [--fail-repairs]
const assert = require("node:assert/strict");
const path = require("node:path");
const {createEnvironment} = require("./dom_stub.js");

const port = Number(process.argv[2]);
const failRepairs = process.argv.includes("--fail-repairs");
const env = createEnvironment();
const realFetch = globalThis.fetch;
globalThis.document = env.document;
globalThis.getComputedStyle = env.getComputedStyle;
globalThis.fetch = async (url, options = {}) => {
  if (failRepairs && url === "/api/kernel-repairs") return {ok: false, status: 503, json: async () => ({error: "Saved repair results unavailable or inconsistent."})};
  const response = await realFetch(`http://127.0.0.1:${port}${url}`, {method: options.method || "GET", headers: options.headers, body: options.body});
  return {ok: response.ok, status: response.status, json: () => response.json()};
};
const $ = (id) => env.document.getElementById(id);
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
async function until(check, label, timeout = 30000) {
  const start = Date.now();
  while (Date.now() - start < timeout) { if (check()) return; await sleep(20); }
  throw new Error(`timed out waiting for: ${typeof label === "function" ? label() : label}`);
}
function choose(kind) {
  for (const k of ["raw", "clipped", "higham"]) $(`kernel-kind-${k}`).checked = k === kind;
  $(`kernel-kind-${kind}`).dispatch("change");
}

(async () => {
  // Values the HTML would provide.
  $("channel").value = "bit_flip"; $("strength").value = "0.2"; $("shots").value = "256"; $("seed").value = "42";
  for (const id of ["bell-area", "kernel-area", "kernel-results"]) $(id).hidden = true;
  $("kernel-kind-higham").disabled = true;  // as in index.html until the comparison loads
  $("density-source").value = "aer"; $("density-component").value = "real"; $("kernel-kind-raw").checked = true;
  require(path.join(__dirname, "..", "..", "src", "praxis_quantum_lab", "dashboard_assets", "app.js"));

  // Tabs: three areas, one visible at a time.
  $("bell-tab").click();
  assert.equal($("bell-area").hidden, false); assert.equal($("playground-area").hidden, true);
  assert.equal($("bell-tab").getAttribute("aria-pressed"), "true");

  // Bell Lab still works end to end.
  $("step-bell").click();
  await until(() => /Completed stage 1\/3/.test($("bell-status").textContent), () => `bell step (${$("bell-status").textContent})`);
  $("bell-form").dispatch("submit");
  await until(() => /Completed stage 3\/3/.test($("bell-status").textContent), () => `bell run (${$("bell-status").textContent})`);
  $("reset-bell").click();
  await until(() => /Completed stage 0\/3/.test($("bell-status").textContent), "bell reset");

  // Observatory: saved results, then the repair comparison.
  $("kernel-tab").click();
  assert.equal($("kernel-area").hidden, false); assert.equal($("bell-area").hidden, true);
  await until(() => /^Loaded finite_shot_kernel_psd_repair\.json/.test($("kernel-status").textContent), () => `kernel results (${$("kernel-status").textContent} ${$("kernel-error").textContent})`);
  assert.equal($("kernel-results").hidden, false);
  assert.equal($("psd-badge").textContent, "INDEFINITE");
  if (failRepairs) {
    await until(() => /unavailable/.test($("kernel-repairs-status").textContent), "repairs failure note");
    assert.equal($("kernel-kind-higham").disabled, true);
    choose("clipped");
    assert.equal($("psd-badge").textContent, "PSD WITHIN TOLERANCE");
    assert.match($("distance-note").textContent, /unavailable/);
    assert.equal($("spectrum-caption").textContent, "Spectrum unavailable.");
    process.stdout.write("APP-SMOKE-OK (repairs unavailable)\n");
    process.exit(0);
  }
  await until(() => /Higham comparison ready/.test($("kernel-repairs-status").textContent), () => `repairs (${$("kernel-repairs-status").textContent})`);
  assert.equal($("kernel-kind-higham").disabled, false);
  assert.match($("spectrum-caption").textContent, /^Raw sampled kernel: \d+ negative eigenvalues/);
  assert.match($("spectrum-caption").textContent, /rank 16 of 40/);
  const rows = $("distance-body").children.map((r) => r.children.map((c) => c.textContent));
  assert.deepEqual(rows.map((r) => r[0]), ["Raw", "Clipped", "Higham"]);
  assert.equal(rows[0][2], "1.00×");
  const [raw, clipped, higham] = rows.map((r) => Number(r[1]));
  assert.ok(higham < raw && raw < clipped, rows.join(" | "));

  choose("clipped");
  assert.equal($("psd-badge").textContent, "PSD WITHIN TOLERANCE");
  assert.match($("kernel-scope").textContent, /TRANSDUCTIVE · Clipping/);
  assert.match($("spectrum-caption").textContent, /^Clipped · transductive: 0 negative eigenvalues/);
  choose("higham");
  assert.equal($("psd-badge").textContent, "PSD WITHIN TOLERANCE");
  assert.match($("kernel-scope").textContent, /TRANSDUCTIVE · Higham/);
  assert.match($("kernel-repair-note").textContent, /nearest PSD, unit-diagonal matrix/);
  assert.match($("spectrum-caption").textContent, /^Higham · transductive: 0 negative eigenvalues/);
  assert.ok($("distance-body").children[2].classList.contains("selected"));
  assert.match($("kernel-split").textContent, /No classifier metrics were saved for Higham/);
  $("kernel-row").value = "3"; $("kernel-col").value = "7"; $("kernel-row").dispatch("input");
  assert.match($("kernel-cell-value").textContent, /^K\(3, 7\) = 0\.\d{6}$/);

  // Changing budget and seed keeps the Higham view consistent.
  $("kernel-budget").value = "2048"; $("kernel-budget").dispatch("change");
  assert.match($("spectrum-caption").textContent, /^Higham · transductive: 0 negative/);
  const second = $("kernel-seed").options[1].value;
  $("kernel-seed").value = second; $("kernel-seed").dispatch("change");
  assert.match($("distance-note").textContent, /Higham 0\.\d\d×/);

  $("playground-tab").click();
  assert.equal($("playground-area").hidden, false); assert.equal($("kernel-area").hidden, true);
  process.stdout.write("APP-SMOKE-OK\n");
  process.exit(0);
})().catch((error) => { console.error(error); process.exit(1); });
