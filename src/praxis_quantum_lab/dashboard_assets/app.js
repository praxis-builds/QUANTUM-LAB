"use strict";

// All computation is served by the project API; this file only renders results.
const byId = (id) => document.getElementById(id);
const basis = ["00", "01", "10", "11"];
let bellResult = null;
let bellBusy = false;
let bellRequestSettings = null;
let kernelData = null;
let kernelLoading = false;
let selectedMatrix = null;
let kernelRepairs = null;
let repairsLoading = false;

const channelNotes = {
  bit_flip: "E(ρ) = (1 − p)ρ + pXρX. Strength p is the bit-flip probability.",
  amplitude_damping: "K₀ = diag(1, √(1 − γ)); K₁ = √γ |0⟩⟨1|. Strength γ is the relaxation probability.",
  depolarizing: "E(ρ) = (1 − p)ρ + pI/2 on q0. Strength p is the mixing weight, not the total Pauli-error probability."
};

function number(value, digits = 4) {
  if (!Number.isFinite(value)) return "—";
  return value.toFixed(digits);
}
function scientific(value) {
  if (!Number.isFinite(value)) return "—";
  return value === 0 ? "0" : value.toExponential(3);
}
function percent(value) { return Number.isFinite(value) ? `${(100 * value).toFixed(1)}%` : "—"; }

async function requestJSON(url, options = {}) {
  const response = await fetch(url, {cache: "no-store", ...options});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.error === "string" ? data.error : `Request failed (${response.status}).`);
  return data;
}

const AREAS = ["playground", "bell", "kernel"];
function chooseArea(area) {
  for (const name of AREAS) {
    const active = name === area;
    byId(`${name}-area`).hidden = !active;
    byId(`${name}-tab`).classList.toggle("active", active);
    byId(`${name}-tab`).setAttribute("aria-pressed", String(active));
  }
  if (area === "kernel" && !kernelData && !kernelLoading) loadKernelData();
}
for (const name of AREAS) byId(`${name}-tab`).addEventListener("click", () => chooseArea(name));

function currentBellSettings() {
  return {
    channel: byId("channel").value,
    strength: Number(byId("strength").value),
    shots: Number(byId("shots").value),
    seed: Number(byId("seed").value)
  };
}

function settingsChanged() {
  byId("strength-output").textContent = number(Number(byId("strength").value), 2);
  byId("channel-help").textContent = channelNotes[byId("channel").value];
  if (bellResult && JSON.stringify(currentBellSettings()) !== bellRequestSettings) {
    byId("bell-status").textContent = "Settings changed. The panels still show the last completed simulation; run or step to apply these settings.";
  } else if (bellResult) {
    byId("bell-status").textContent = `Completed stage ${bellResult.step}/3 · ${bellResult.shots.toLocaleString()} shots · seed ${bellResult.seed}.`;
  }
}

for (const id of ["channel", "strength", "shots", "seed"]) byId(id).addEventListener("input", settingsChanged);

function setBellBusy(busy) {
  bellBusy = busy;
  byId("bell-form").setAttribute("aria-busy", String(busy));
  for (const control of byId("bell-form").querySelectorAll("button, input, select")) control.disabled = busy;
  byId("step-bell").disabled = busy || (bellResult !== null && bellResult.step >= 3);
  byId("run-bell").textContent = busy ? "Simulating locally…" : "Run full circuit →";
}

async function simulateBell(step) {
  if (bellBusy || !byId("bell-form").reportValidity()) return;
  const settings = currentBellSettings();
  setBellBusy(true);
  byId("bell-error").hidden = true;
  byId("bell-status").textContent = "Running the project density-matrix calculation and local Qiskit Aer…";
  try {
    const data = await requestJSON("/api/bell", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({...settings, step})
    });
    bellResult = data;
    bellRequestSettings = JSON.stringify(settings);
    renderBell();
    byId("bell-status").textContent = `Completed stage ${data.step}/3 · ${data.shots.toLocaleString()} shots · seed ${data.seed}.`;
  } catch (error) {
    byId("bell-error").textContent = `Simulation failed: ${error.message}`;
    byId("bell-error").hidden = false;
    byId("bell-status").textContent = bellResult ? "Last completed results remain displayed." : "No simulation results yet.";
  } finally { setBellBusy(false); }
}
byId("bell-form").addEventListener("submit", (event) => { event.preventDefault(); simulateBell(3); });
byId("step-bell").addEventListener("click", () => simulateBell(Math.min((bellResult?.step ?? 0) + 1, 3)));
byId("reset-bell").addEventListener("click", () => simulateBell(0));

function renderBell() {
  const data = bellResult;
  ["gate-h", "gate-cx", "gate-noise"].forEach((id, index) => {
    byId(id).classList.toggle("applied", index < data.step);
    byId(id).classList.toggle("current", index + 1 === data.step);
  });
  const stageLabels = ["INITIAL |00⟩", "H ON q0", "BELL STATE", "NOISE ON q0"];
  byId("circuit-stage").textContent = stageLabels[data.step];
  byId("circuit-stage").classList.add("good");
  const descriptions = [
    "Both qubits are initialized in |00⟩. No preparation gate has been applied.",
    "H(q0) creates (|00⟩ + |01⟩)/√2. q0 is the rightmost bit.",
    "CX(q0 → q1) prepares |Φ+⟩ = (|00⟩ + |11⟩)/√2.",
    `Noise applied to q0 after Bell preparation. ${data.parameter_convention}`
  ];
  byId("stage-description").textContent = descriptions[data.step];
  byId("aer-fidelity").textContent = number(data.aer_bell_fidelity);
  byId("custom-fidelity").textContent = number(data.custom_bell_fidelity);
  byId("bell-error-norm").textContent = scientific(data.frobenius_error);
  byId("probability-empty").hidden = true;
  byId("probability-results").hidden = false;
  const body = byId("probability-body");
  body.replaceChildren();
  for (const state of basis) {
    const row = document.createElement("tr");
    const label = document.createElement("td"); label.textContent = `|${state}⟩`;
    const probability = document.createElement("td");
    const value = document.createElement("div"); value.className = "probability-cell";
    const text = document.createElement("span"); text.textContent = percent(data.aer_probabilities[state]);
    const track = document.createElement("div"); track.className = "probability-track"; track.setAttribute("aria-hidden", "true");
    const fill = document.createElement("div"); fill.className = "probability-fill"; fill.style.width = `${Math.max(0, Math.min(1, data.aer_probabilities[state])) * 100}%`;
    track.append(fill); value.append(text, track); probability.append(value);
    const count = document.createElement("td"); count.textContent = String(data.counts[state] ?? 0);
    row.append(label, probability, count); body.append(row);
  }
  byId("counts-caption").textContent = `Aer exact probabilities · ${data.shots.toLocaleString()} sampled measurements. Sampling introduces variation in counts.`;
  renderDensity();
}

// Canvas coordinates are fixed logical units. CSS scales the canvases responsively.
// Canvas colours come from the CSS theme tokens; the cache is cleared when the theme changes.
let themeCache = {};
function themeColor(name, fallback) {
  if (!(name in themeCache)) {
    let value = "";
    try { value = getComputedStyle(document.documentElement).getPropertyValue(name).trim(); } catch (error) { value = ""; }
    themeCache[name] = value;
  }
  return themeCache[name] || fallback;
}
function themeRGB(name, fallback) {
  const parts = themeColor(name, "").split(",").map((part) => Number(part.trim()));
  return parts.length === 3 && parts.every(Number.isFinite) ? parts : fallback;
}
function context(canvas) {
  const width = Number(canvas.getAttribute("width"));
  const height = Number(canvas.getAttribute("height"));
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, width, height);
  ctx.font = "12px ui-monospace, Consolas, monospace";
  ctx.fillStyle = themeColor("--muted", "#a6b5c8");
  return {ctx, width, height};
}

function mixColor(start, end, fraction) {
  return `rgb(${start.map((value, index) => Math.round(value + (end[index] - value) * fraction)).join(",")})`;
}
function heatColor(value, signed) {
  const t = Math.min(1, Math.max(0, Math.abs(value)));
  const zero = themeRGB("--heat-zero", [23, 36, 52]);
  const end = signed && value < 0 ? themeRGB("--heat-negative", [186, 117, 172]) : themeRGB("--heat-positive", [92, 205, 193]);
  return mixColor(zero, end, t);
}
function renderEmptyDensity() {
  const {ctx, width, height} = context(byId("density-canvas"));
  ctx.textAlign = "center";
  ctx.fillText("No simulated state yet", width / 2, height / 2 - 7);
  ctx.fillText("Use Run, Step, or Reset", width / 2, height / 2 + 17);
}

function renderDensity() {
  if (!bellResult) return;
  const source = byId("density-source").value;
  const component = byId("density-component").value;
  const matrix = bellResult[`${source}_density_matrix`];
  const componentIndex = component === "real" ? 0 : 1;
  const values = matrix.map((row) => row.map((cell) => cell[componentIndex]));
  const canvas = byId("density-canvas");
  const {ctx} = context(canvas);
  const left = 76, top = 42, cellSize = 75;
  ctx.textAlign = "center";
  values.forEach((row, i) => {
    ctx.fillStyle = themeColor("--muted", "#a6b5c8"); ctx.fillText(basis[i], left - 26, top + i * cellSize + cellSize / 2 + 4);
    ctx.fillText(basis[i], left + i * cellSize + cellSize / 2, top - 16);
    row.forEach((value, j) => {
      const x = left + j * cellSize, y = top + i * cellSize;
      ctx.fillStyle = heatColor(value, true); ctx.fillRect(x, y, cellSize - 2, cellSize - 2);
      ctx.fillStyle = Math.abs(value) > .65 ? themeColor("--heat-text-strong", "#102726") : themeColor("--heat-text-weak", "#edf6fa");
      ctx.fillText(number(value, 3), x + cellSize / 2, y + cellSize / 2 + 4);
    });
  });
  drawScale(ctx, left, 367, 300, true);
  canvas.setAttribute("aria-label", `${source === "aer" ? "Aer" : "Project"} density matrix ${component} component. Values available in the expandable table.`);
  const maxImaginary = Math.max(...matrix.flat().map((cell) => Math.abs(cell[1])));
  byId("density-caption").textContent = `${component === "real" ? "Real" : "Imaginary"} component · rows/columns: 00, 01, 10, 11. Max |imaginary entry| = ${scientific(maxImaginary)}. Fixed color scale −1 to +1.`;
  const table = byId("density-table"); table.replaceChildren();
  const caption = document.createElement("caption"); caption.textContent = `Complex entries · ${source === "aer" ? "Qiskit Aer" : "Project calculation"}`; table.append(caption);
  const head = document.createElement("thead"), hrow = document.createElement("tr");
  for (const label of ["ρ", ...basis]) {const th = document.createElement("th");th.scope = "col";th.textContent = label;hrow.append(th);} head.append(hrow); table.append(head);
  const body = document.createElement("tbody");
  matrix.forEach((row, i) => {const tr = document.createElement("tr"); const label = document.createElement("th");label.scope = "row";label.textContent = basis[i];tr.append(label);row.forEach(([real, imag]) => {const td = document.createElement("td");td.textContent = `${number(real)} ${imag < 0 ? "−" : "+"} ${number(Math.abs(imag))}i`;tr.append(td);});body.append(tr);});
  table.append(body); byId("density-values").hidden = false;
}
byId("density-source").addEventListener("change", renderDensity);
byId("density-component").addEventListener("change", renderDensity);

function drawScale(ctx, left, top, width, signed) {
  for (let i = 0; i < width; i++) {const value = signed ? (2 * i / (width - 1) - 1) : i / (width - 1);ctx.fillStyle = heatColor(value, signed);ctx.fillRect(left + i, top, 1, 8);}
  ctx.fillStyle = themeColor("--muted", "#a6b5c8");ctx.textAlign = "left";ctx.fillText(signed ? "−1" : "0", left, top + 26);
  ctx.textAlign = "center";ctx.fillText(signed ? "0" : "0.5", left + width / 2, top + 26);
  ctx.textAlign = "right";ctx.fillText("+1", left + width, top + 26);
}

async function loadKernelData() {
  if (kernelLoading) return;
  kernelLoading = true; byId("kernel-error").hidden = true; byId("retry-kernel").hidden = true;
  byId("kernel-status").textContent = "Reading the saved PSD-repair experiment…";
  try {
    kernelData = await requestJSON("/api/kernel-results");
    const budget = byId("kernel-budget"); budget.replaceChildren();
    kernelData.shot_budgets.forEach((item) => {const option = document.createElement("option");option.value = String(item.shots);option.textContent = `${item.shots.toLocaleString()} shots`;budget.append(option);});
    budget.disabled = false; populateSeeds();
    byId("kernel-results").hidden = false;
    byId("kernel-status").textContent = "Loaded finite_shot_kernel_psd_repair.json. These are saved results; no experiment is running.";
    loadKernelRepairs();
  } catch (error) {
    kernelData = null; byId("kernel-error").textContent = `Could not load saved results: ${error.message}`; byId("kernel-error").hidden = false;
    byId("retry-kernel").hidden = false; byId("kernel-status").textContent = "Saved results are unavailable.";
  } finally { kernelLoading = false; }
}
function currentBudget() {return kernelData.shot_budgets.find((item) => String(item.shots) === byId("kernel-budget").value);}
function populateSeeds() {
  const selected = byId("kernel-seed").value;
  const selector = byId("kernel-seed");selector.replaceChildren();
  currentBudget().replicates.forEach((item) => {const option = document.createElement("option");option.value = String(item.shot_seed);option.textContent = String(item.shot_seed);selector.append(option);});
  if ([...selector.options].some((option) => option.value === selected)) selector.value = selected;
  selector.disabled = false; renderKernel();
}
byId("kernel-budget").addEventListener("change", populateSeeds);
byId("kernel-seed").addEventListener("change", renderKernel);
for (const kind of ["raw", "clipped", "higham"]) byId(`kernel-kind-${kind}`).addEventListener("change", renderKernel);
byId("retry-kernel").addEventListener("click", loadKernelData);

function kernelKind() {
  const checked = ["raw", "clipped", "higham"].find((kind) => byId(`kernel-kind-${kind}`).checked);
  return checked || "raw";
}
function repairEntry(replicate) {
  if (!kernelRepairs) return null;
  return kernelRepairs.entries.find((entry) => entry.shots === currentBudget().shots && entry.shot_seed === replicate.shot_seed) || null;
}
const KIND_LABELS = {raw: "Raw sampled kernel", clipped: "Clipped · transductive", higham: "Higham · transductive"};

function renderKernel() {
  if (!kernelData) return;
  const metadata = kernelData.metadata;
  const replicate = currentBudget().replicates.find((item) => String(item.shot_seed) === byId("kernel-seed").value);
  const entry = repairEntry(replicate);
  let kind = kernelKind();
  if (kind === "higham" && !entry) { kind = "raw"; byId("kernel-kind-raw").checked = true; }
  const repaired = kind !== "raw";
  selectedMatrix = {raw: replicate.raw_sampled_kernel_matrix, clipped: replicate.psd_repaired_kernel_matrix, higham: entry && entry.higham_matrix}[kind];
  const diagnostics = {raw: replicate.raw_matrix_diagnostics, clipped: replicate.repaired_matrix_diagnostics, higham: entry && entry.higham_diagnostics}[kind];
  const scope = byId("kernel-scope");scope.classList.toggle("transductive", repaired);
  scope.textContent = repaired
    ? `TRANSDUCTIVE · ${kind === "higham" ? "Higham" : "Clipping"} repair uses the full unlabeled matrix, including test inputs. Test labels are not used. The repair changes the measured data; interpret any metric as a transductive fixed-split result.`
    : "RAW SAMPLED KERNEL · One estimate per unique pair, reflected for symmetry, with exact K(x, x) = 1. The classifier uses raw train/train and test/train blocks; negative eigenvalues are preserved.";
  const psd = diagnostics.positive_semidefinite_within_tolerance;
  byId("psd-badge").textContent = psd ? "PSD WITHIN TOLERANCE" : "INDEFINITE";
  byId("psd-badge").className = `stage-badge ${psd ? "good" : "warning"}`;
  byId("kernel-min-eigenvalue").textContent = scientific(diagnostics.minimum_eigenvalue);
  byId("kernel-tolerance").textContent = scientific(diagnostics.psd_tolerance);
  byId("kernel-symmetry").textContent = scientific(diagnostics.symmetry_max_abs_error);
  byId("kernel-diagonal").textContent = `${number(Math.min(...diagnostics.diagonal_values), 6)} – ${number(Math.max(...diagnostics.diagonal_values), 6)}`;
  byId("kernel-distance").textContent = number(diagnostics.frobenius_distance_from_raw, 6);
  byId("kernel-repair-note").textContent = {
    raw: "An exact fidelity kernel is PSD. Independently sampled pair estimates can be indefinite; accepting this matrix in SVC does not restore the PSD condition.",
    clipped: "Eigenvalue clipping and diagonal renormalization change measured similarities. This PSD, unit-diagonal matrix is not the nearest correlation matrix, and here it lands further from the exact kernel than the raw matrix. This is classical post-processing.",
    higham: `Higham's alternating projections (${entry ? entry.higham_iterations : "—"} iterations) find the nearest PSD, unit-diagonal matrix to the raw one in Frobenius norm. It still changes measured similarities and uses test inputs. Recomputed from the saved raw matrix; not re-sampled.`
  }[kind];
  byId("kernel-size").textContent = `${metadata.sample_size} × ${metadata.sample_size} · FULL SUBSET`;
  byId("kernel-ordering").textContent = `Rows and columns: ${metadata.train_size} training inputs, then ${metadata.test_size} test inputs. The dashed boundary marks the fixed split. Color scale is fixed at −1 to +1.`;
  byId("kernel-split").textContent = `${metadata.sample_size} inputs · ${metadata.train_size} train / ${metadata.test_size} test · split seed ${metadata.seed}. Accuracy and F1 come directly from the saved result.${kind === "higham" ? " No classifier metrics were saved for Higham on this split; docs/repeated-model-comparison.md compares it over 50 splits." : ""}`;
  const rows = [
    ["Raw finite-shot kernel", replicate.classifier_results.raw_finite_shot_kernel, kind === "raw"],
    ["Clipped · transductive", replicate.classifier_results.psd_repaired_transductive_kernel, kind === "clipped"],
    ["Higham · transductive (not recorded)", {accuracy: NaN, f1: NaN}, kind === "higham"],
    ["Exact statevector kernel", kernelData.baselines.exact_statevector_kernel_svc, false],
    ["Fixed RBF baseline", kernelData.baselines.fixed_rbf_svc, false]
  ];
  const body = byId("classifier-body");body.replaceChildren();
  rows.forEach(([label, metrics, selected]) => {const row = document.createElement("tr");row.classList.toggle("selected", selected);for (const text of [label, percent(metrics.accuracy), number(metrics.f1)]) {const td = document.createElement("td");td.textContent = text;row.append(td);}body.append(row);});
  byId("kernel-row").max = String(selectedMatrix.length - 1);byId("kernel-col").max = String(selectedMatrix.length - 1);
  renderKernelHeatmap(metadata.train_size);inspectCell();
  renderDistances(entry, kind);
  renderSpectrum(entry, kind);
}

function renderDistances(entry, kind) {
  const body = byId("distance-body");body.replaceChildren();
  for (const name of ["raw", "clipped", "higham"]) {
    const row = document.createElement("tr");row.classList.toggle("selected", name === kind);
    const distance = entry ? entry.distance_to_exact[name] : NaN;
    const ratio = entry ? distance / entry.distance_to_exact.raw : NaN;
    const label = document.createElement("td");label.textContent = {raw: "Raw", clipped: "Clipped", higham: "Higham"}[name];
    const value = document.createElement("td");
    const bar = document.createElement("span");bar.className = `distance-bar ${name}`;
    if (entry) bar.style.width = `${Math.min(100, 100 * distance / Math.max(...Object.values(entry.distance_to_exact)))}%`;
    const text = document.createElement("span");text.textContent = number(distance, 4);
    value.append(bar, text);
    const relative = document.createElement("td");relative.textContent = Number.isFinite(ratio) ? `${ratio.toFixed(2)}×` : "—";
    row.append(label, value, relative);body.append(row);
  }
  byId("distance-note").textContent = entry
    ? `Exact = statevector fidelity kernel on the same 40 inputs. Here clipping is ${(entry.distance_to_exact.clipped / entry.distance_to_exact.raw).toFixed(2)}× the raw distance and Higham ${(entry.distance_to_exact.higham / entry.distance_to_exact.raw).toFixed(2)}×. Distances are checked against results/higham_vs_clipping.json.`
    : "Distance to exact needs the repair comparison, which is unavailable.";
}

function symlog(value) { const c = 1e-3; return Math.sign(value) * Math.log10(1 + Math.abs(value) / c); }
function renderSpectrum(entry, kind) {
  const canvas = byId("kernel-spectrum");const {ctx, width, height} = context(canvas);
  if (!entry) {ctx.textAlign = "center";ctx.fillText("Spectrum needs the repair comparison, which is unavailable.", width / 2, height / 2);byId("spectrum-caption").textContent = "Spectrum unavailable.";return;}
  const values = entry.eigenvalues[kind], exact = kernelRepairs.exact_eigenvalues;
  const left = 64, right = width - 18, top = 18, bottom = height - 40;
  const all = [...values, ...exact].map(symlog);
  const high = Math.max(...all), low = Math.min(0, ...all);
  const y = (v) => bottom - (symlog(v) - low) / (high - low) * (bottom - top);
  const x = (i) => left + (i + 0.5) * (right - left) / values.length;
  ctx.strokeStyle = themeColor("--border", "#2a3748");ctx.lineWidth = 1;
  ctx.fillStyle = themeColor("--muted", themeColor("--muted", "#a6b5c8"));ctx.textAlign = "right";
  for (const tick of [-1, -0.1, -0.01, 0.01, 0.1, 1, 10]) {
    if (symlog(tick) < low || symlog(tick) > high) continue;
    ctx.beginPath();ctx.moveTo(left, y(tick));ctx.lineTo(right, y(tick));ctx.stroke();
    ctx.fillText(String(tick), left - 8, y(tick) + 4);
  }
  ctx.strokeStyle = themeColor("--text", "#eef3f9");ctx.setLineDash([6, 4]);ctx.lineWidth = 1.3;
  ctx.beginPath();ctx.moveTo(left, y(0));ctx.lineTo(right, y(0));ctx.stroke();ctx.setLineDash([]);
  ctx.fillText("0", left - 8, y(0) + 4);
  ctx.strokeStyle = themeColor("--muted", themeColor("--muted", "#a6b5c8"));ctx.lineWidth = 1;
  exact.forEach((v, i) => {ctx.beginPath();ctx.arc(x(i), y(v), 5.5, 0, 2 * Math.PI);ctx.stroke();});
  let negatives = 0;
  values.forEach((v, i) => {
    if (v < -1e-10) {
      negatives += 1;ctx.fillStyle = themeColor("--danger", "#ff9a9a");
      ctx.beginPath();ctx.moveTo(x(i) - 5, y(v) - 4);ctx.lineTo(x(i) + 5, y(v) - 4);ctx.lineTo(x(i), y(v) + 5);ctx.closePath();ctx.fill();
    } else {
      ctx.fillStyle = themeColor("--accent", "#76d8c6");ctx.beginPath();ctx.arc(x(i), y(v), 3.2, 0, 2 * Math.PI);ctx.fill();
    }
  });
  ctx.fillStyle = themeColor("--muted", themeColor("--muted", "#a6b5c8"));ctx.textAlign = "center";
  ctx.fillText("eigenvalue rank (ascending)", (left + right) / 2, height - 12);
  // Same rank rule as the Python code: eigenvalue > n * machine epsilon * largest eigenvalue.
  const exactRank = exact.filter((v) => v > exact.length * Number.EPSILON * Math.max(...exact)).length;
  const text = `${KIND_LABELS[kind]}: ${negatives} negative eigenvalue${negatives === 1 ? "" : "s"} (most negative ${scientific(values[0])}). The exact kernel has rank ${exactRank} of ${exact.length}; its remaining eigenvalues are zero, which is why sampling noise pushes so many raw eigenvalues below zero.`;
  byId("spectrum-caption").textContent = text;
  canvas.setAttribute("aria-label", text);
}

async function loadKernelRepairs() {
  if (kernelRepairs || repairsLoading) return;
  repairsLoading = true;
  byId("kernel-repairs-status").textContent = "Computing the Higham comparison from the saved raw matrices (read-only, no sampling)…";
  try {
    kernelRepairs = await requestJSON("/api/kernel-repairs");
    byId("kernel-kind-higham").disabled = false;
    byId("kernel-repairs-status").textContent = "Higham comparison ready. Distances agree with results/higham_vs_clipping.json.";
  } catch (error) {
    kernelRepairs = null;
    byId("kernel-repairs-status").textContent = `Higham comparison unavailable (${error.message}). Raw and clipped views still work.`;
  } finally { repairsLoading = false; renderKernel(); }
}

function renderKernelHeatmap(trainSize) {
  const canvas = byId("kernel-canvas");const {ctx} = context(canvas);
  const left = 68, top = 36, size = 480, cell = size / selectedMatrix.length;
  selectedMatrix.forEach((row, i) => row.forEach((value, j) => {ctx.fillStyle = heatColor(value, true);ctx.fillRect(left + j * cell, top + i * cell, cell + .3, cell + .3);}));
  ctx.strokeStyle = themeColor("--boundary", "#e7eff8");ctx.lineWidth = 1.3;ctx.setLineDash([5, 4]);
  const boundary = trainSize * cell;
  ctx.beginPath();ctx.moveTo(left + boundary, top);ctx.lineTo(left + boundary, top + size);ctx.moveTo(left, top + boundary);ctx.lineTo(left + size, top + boundary);ctx.stroke();ctx.setLineDash([]);
  ctx.fillStyle = themeColor("--muted", "#a6b5c8");ctx.textAlign = "center";
  for (const i of [0, trainSize - 1, trainSize, selectedMatrix.length - 1]) {ctx.fillText(String(i), left + (i + .5) * cell, top - 13);ctx.fillText(String(i), left - 22, top + (i + .5) * cell + 4);}
  ctx.fillText("training inputs", left + boundary / 2, top + size + 25);
  ctx.fillText("test inputs", left + boundary + (size - boundary) / 2, top + size + 25);
  drawScale(ctx, left, top + size + 46, size, true);
  canvas.setAttribute("aria-label", `${selectedMatrix.length} by ${selectedMatrix.length} ${KIND_LABELS[kernelKind()]} heatmap. Use row and column controls below to read individual values.`);
}
function inspectCell() {
  if (!selectedMatrix) return;
  const row = Number(byId("kernel-row").value), col = Number(byId("kernel-col").value);
  if (!Number.isInteger(row) || !Number.isInteger(col) || row < 0 || col < 0 || row >= selectedMatrix.length || col >= selectedMatrix.length) {
    byId("kernel-cell-value").textContent = `Use indices 0–${selectedMatrix.length - 1}`;return;
  }
  byId("kernel-cell-value").textContent = `K(${row}, ${col}) = ${number(selectedMatrix[row][col], 6)}`;
}
byId("kernel-row").addEventListener("input", inspectCell);
byId("kernel-col").addEventListener("input", inspectCell);
byId("kernel-canvas").addEventListener("click", (event) => {
  if (!selectedMatrix) return;
  const rect = event.currentTarget.getBoundingClientRect();
  const x = (event.clientX - rect.left) * 680 / rect.width;
  const y = (event.clientY - rect.top) * 610 / rect.height;
  const col = Math.floor((x - 68) / (480 / selectedMatrix.length));
  const row = Math.floor((y - 36) / (480 / selectedMatrix.length));
  if (row >= 0 && col >= 0 && row < selectedMatrix.length && col < selectedMatrix.length) {byId("kernel-row").value = row;byId("kernel-col").value = col;inspectCell();}
});
renderEmptyDensity();

// ---------------------------------------------------------------- theme (dark default, light option)
const THEME_KEY = "praxis-lab-theme";
function systemTheme() {
  try { return typeof matchMedia === "function" && matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark"; } catch (error) { return "dark"; }
}
function activeTheme() { return document.documentElement.getAttribute("data-theme") || systemTheme(); }
function syncThemeToggle() { byId("theme-toggle").setAttribute("aria-pressed", String(activeTheme() === "light")); }
function redrawForTheme() {
  themeCache = {};
  syncThemeToggle();
  const event = typeof CustomEvent === "function" ? new CustomEvent("praxis-theme-change") : {type: "praxis-theme-change"};
  document.dispatchEvent(event);
  if (bellResult) renderDensity(); else renderEmptyDensity();
  if (kernelData) renderKernel();
}
function applyTheme(theme, remember) {
  document.documentElement.setAttribute("data-theme", theme);
  if (remember) { try { localStorage.setItem(THEME_KEY, theme); } catch (error) { /* storage may be unavailable */ } }
  redrawForTheme();
}
byId("theme-toggle").addEventListener("click", () => applyTheme(activeTheme() === "light" ? "dark" : "light", true));
(function initTheme() {
  let saved = null;
  try { saved = localStorage.getItem(THEME_KEY); } catch (error) { saved = null; }
  if (saved === "light" || saved === "dark") applyTheme(saved, false); else syncThemeToggle();
  try {
    if (typeof matchMedia === "function") {
      matchMedia("(prefers-color-scheme: light)").addEventListener("change", () => { if (!document.documentElement.getAttribute("data-theme")) redrawForTheme(); });
    }
  } catch (error) { /* older browsers: the theme still follows CSS */ }
})();
