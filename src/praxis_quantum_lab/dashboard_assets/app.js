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
function context(canvas) {
  const width = Number(canvas.getAttribute("width"));
  const height = Number(canvas.getAttribute("height"));
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, width, height);
  ctx.font = "12px ui-monospace, Consolas, monospace";
  ctx.fillStyle = "#a6b5c8";
  return {ctx, width, height};
}

function mixColor(start, end, fraction) {
  return `rgb(${start.map((value, index) => Math.round(value + (end[index] - value) * fraction)).join(",")})`;
}
function heatColor(value, signed) {
  const t = Math.min(1, Math.max(0, Math.abs(value)));
  return mixColor([23, 36, 52], signed && value < 0 ? [186, 117, 172] : [92, 205, 193], t);
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
    ctx.fillStyle = "#a6b5c8"; ctx.fillText(basis[i], left - 26, top + i * cellSize + cellSize / 2 + 4);
    ctx.fillText(basis[i], left + i * cellSize + cellSize / 2, top - 16);
    row.forEach((value, j) => {
      const x = left + j * cellSize, y = top + i * cellSize;
      ctx.fillStyle = heatColor(value, true); ctx.fillRect(x, y, cellSize - 2, cellSize - 2);
      ctx.fillStyle = Math.abs(value) > .65 ? "#102726" : "#edf6fa";
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
  ctx.fillStyle = "#a6b5c8";ctx.textAlign = "left";ctx.fillText(signed ? "−1" : "0", left, top + 26);
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
byId("kernel-kind").addEventListener("change", renderKernel);
byId("retry-kernel").addEventListener("click", loadKernelData);

function renderKernel() {
  if (!kernelData) return;
  const metadata = kernelData.metadata;
  const replicate = currentBudget().replicates.find((item) => String(item.shot_seed) === byId("kernel-seed").value);
  const repaired = byId("kernel-kind").value === "repaired";
  selectedMatrix = repaired ? replicate.psd_repaired_kernel_matrix : replicate.raw_sampled_kernel_matrix;
  const diagnostics = repaired ? replicate.repaired_matrix_diagnostics : replicate.raw_matrix_diagnostics;
  const scope = byId("kernel-scope");scope.classList.toggle("transductive", repaired);
  scope.textContent = repaired
    ? "TRANSDUCTIVE EVALUATION · Repair uses the full unlabeled matrix, including test inputs. Test labels are not used. Interpret these metrics as a transductive fixed-split result."
    : "RAW SAMPLED KERNEL · One estimate per unique pair, reflected for symmetry, with exact K(x, x) = 1. The classifier uses raw train/train and test/train blocks; negative eigenvalues are preserved.";
  const psd = diagnostics.positive_semidefinite_within_tolerance;
  byId("psd-badge").textContent = psd ? "PSD WITHIN TOLERANCE" : "INDEFINITE";
  byId("psd-badge").className = `stage-badge ${psd ? "good" : "warning"}`;
  byId("kernel-min-eigenvalue").textContent = scientific(diagnostics.minimum_eigenvalue);
  byId("kernel-tolerance").textContent = scientific(diagnostics.psd_tolerance);
  byId("kernel-symmetry").textContent = scientific(diagnostics.symmetry_max_abs_error);
  byId("kernel-diagonal").textContent = `${number(Math.min(...diagnostics.diagonal_values), 6)} – ${number(Math.max(...diagnostics.diagonal_values), 6)}`;
  byId("kernel-distance").textContent = number(diagnostics.frobenius_distance_from_raw, 6);
  byId("kernel-repair-note").textContent = repaired
    ? "Eigenvalue clipping and diagonal renormalization change measured similarities. This PSD, unit-diagonal matrix is not necessarily the nearest correlation matrix. This is classical post-processing."
    : "An exact fidelity kernel is PSD. Independently sampled pair estimates can be indefinite; accepting this matrix in SVC does not restore the PSD condition.";
  byId("kernel-size").textContent = `${metadata.sample_size} × ${metadata.sample_size} · FULL SUBSET`;
  byId("kernel-ordering").textContent = `Rows and columns: ${metadata.train_size} training inputs, then ${metadata.test_size} test inputs. The dashed boundary marks the fixed split. Color scale is fixed at −1 to +1.`;
  byId("kernel-split").textContent = `${metadata.sample_size} inputs · ${metadata.train_size} train / ${metadata.test_size} test · split seed ${metadata.seed}. Accuracy and F1 come directly from the saved result.`;
  const rows = [
    ["Raw finite-shot kernel", replicate.classifier_results.raw_finite_shot_kernel, !repaired],
    ["Repaired · transductive", replicate.classifier_results.psd_repaired_transductive_kernel, repaired],
    ["Exact statevector kernel", kernelData.baselines.exact_statevector_kernel_svc, false],
    ["Fixed RBF baseline", kernelData.baselines.fixed_rbf_svc, false]
  ];
  const body = byId("classifier-body");body.replaceChildren();
  rows.forEach(([label, metrics, selected]) => {const row = document.createElement("tr");row.classList.toggle("selected", selected);for (const text of [label, percent(metrics.accuracy), number(metrics.f1)]) {const td = document.createElement("td");td.textContent = text;row.append(td);}body.append(row);});
  byId("kernel-row").max = String(selectedMatrix.length - 1);byId("kernel-col").max = String(selectedMatrix.length - 1);
  renderKernelHeatmap(metadata.train_size);inspectCell();
}

function renderKernelHeatmap(trainSize) {
  const canvas = byId("kernel-canvas");const {ctx} = context(canvas);
  const left = 68, top = 36, size = 480, cell = size / selectedMatrix.length;
  selectedMatrix.forEach((row, i) => row.forEach((value, j) => {ctx.fillStyle = heatColor(value, true);ctx.fillRect(left + j * cell, top + i * cell, cell + .3, cell + .3);}));
  ctx.strokeStyle = "#e7eff8";ctx.lineWidth = 1.3;ctx.setLineDash([5, 4]);
  const boundary = trainSize * cell;
  ctx.beginPath();ctx.moveTo(left + boundary, top);ctx.lineTo(left + boundary, top + size);ctx.moveTo(left, top + boundary);ctx.lineTo(left + size, top + boundary);ctx.stroke();ctx.setLineDash([]);
  ctx.fillStyle = "#a6b5c8";ctx.textAlign = "center";
  for (const i of [0, trainSize - 1, trainSize, selectedMatrix.length - 1]) {ctx.fillText(String(i), left + (i + .5) * cell, top - 13);ctx.fillText(String(i), left - 22, top + (i + .5) * cell + 4);}
  ctx.fillText("training inputs", left + boundary / 2, top + size + 25);
  ctx.fillText("test inputs", left + boundary + (size - boundary) / 2, top + size + 25);
  drawScale(ctx, left, top + size + 46, size, true);
  canvas.setAttribute("aria-label", `${selectedMatrix.length} by ${selectedMatrix.length} ${byId("kernel-kind").value} kernel heatmap. Use row and column controls below to read individual values.`);
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
