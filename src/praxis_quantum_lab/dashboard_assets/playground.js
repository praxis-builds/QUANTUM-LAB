"use strict";

// Circuit Playground. The server computes every state (NumPy) and every shot (local Aer);
// this file only keeps the gate list and draws what the server returns. The one exception
// is the empty circuit, whose state |0...0> is drawn directly so the first load simulates nothing.
// PlaygroundCore holds pure helpers so they can be unit-tested with Node, without a browser.
const PlaygroundCore = (() => {
  const MAX_QUBITS = 3, MAX_GATES = 30, MAX_SHOTS = 8192, MAX_SEED = 2147483647;
  const GATES = {
    h: {label: "H", arity: 1, name: "Hadamard"},
    x: {label: "X", arity: 1, name: "X (bit flip)"},
    y: {label: "Y", arity: 1, name: "Y"},
    z: {label: "Z", arity: 1, name: "Z (phase flip)"},
    s: {label: "S", arity: 1, name: "S (quarter-turn phase)"},
    t: {label: "T", arity: 1, name: "T (eighth-turn phase)"},
    rx: {label: "RX", arity: 1, angle: true, name: "rotation about x"},
    ry: {label: "RY", arity: 1, angle: true, name: "rotation about y"},
    rz: {label: "RZ", arity: 1, angle: true, name: "rotation about z"},
    cx: {label: "CNOT", arity: 2, name: "controlled NOT"},
    cz: {label: "CZ", arity: 2, name: "controlled Z"},
    cp: {label: "CP", arity: 2, angle: true, name: "controlled phase"},
    ccz: {label: "CCZ", arity: 3, name: "controlled-controlled Z"},
    swap: {label: "SWAP", arity: 2, name: "swap"},
    measure: {label: "M", arity: 1, name: "measure"}
  };
  const PALETTE = ["h", "x", "y", "z", "s", "t", "rx", "ry", "rz", "cx", "cz", "cp", "ccz", "swap", "measure"];

  // Earliest column after every earlier gate that touches (or visually crosses) the same wires.
  function layoutColumns(gates) {
    const next = new Array(MAX_QUBITS).fill(0);
    return gates.map((gate) => {
      const low = Math.min(...gate.qubits), high = Math.max(...gate.qubits);
      let column = 0;
      for (let q = low; q <= high; q++) column = Math.max(column, next[q]);
      for (let q = low; q <= high; q++) next[q] = column + 1;
      return column;
    });
  }

  function measuredQubits(gates) {
    return new Set(gates.filter((gate) => gate.gate === "measure").map((gate) => gate.qubits[0]));
  }

  // Mirrors the server rules so the UI can explain a refusal before sending anything.
  function placementProblem(gates, gate, qubits) {
    const info = GATES[gate.gate];
    if (!info) return "Unknown gate.";
    if (gates.length >= MAX_GATES) return `The circuit is full (${MAX_GATES} gates). Remove a gate or press Undo.`;
    if (gate.qubits.length !== info.arity || gate.qubits.some((q) => !Number.isInteger(q) || q < 0 || q >= qubits)) return "Choose qubits inside the circuit.";
    if (new Set(gate.qubits).size !== gate.qubits.length) return "A multi-qubit gate needs different qubits.";
    const measured = measuredQubits(gates);
    for (const q of gate.qubits) {
      if (measured.has(q)) return `q${q} is already measured. Measurement must be the last operation on its wire.`;
    }
    if (info.angle && !(Number.isFinite(gate.angle) && Math.abs(gate.angle) <= 4 * Math.PI)) return "The angle must be between −4π and 4π.";
    return null;
  }

  function keepWithinQubits(gates, qubits) {
    return gates.filter((gate) => gate.qubits.every((q) => q < qubits));
  }

  function buildRequest(qubits, gates, shots, seed) {
    return {
      qubits,
      gates: gates.map((gate) => (GATES[gate.gate].angle
        ? {gate: gate.gate, qubits: [...gate.qubits], angle: gate.angle}
        : {gate: gate.gate, qubits: [...gate.qubits]})),
      shots,
      seed
    };
  }
  function circuitKey(qubits, gates) { return JSON.stringify(buildRequest(qubits, gates, 0, 0).gates) + `|${qubits}`; }

  function shotsFromSlider(value) { return Math.min(MAX_SHOTS, Math.max(1, Math.round(Math.pow(MAX_SHOTS, value / 100)))); }
  function sliderFromShots(shots) { return Math.round(100 * Math.log(shots) / Math.log(MAX_SHOTS)); }
  function parseBoundedInt(text, low, high) {
    if (!/^\s*\d+\s*$/.test(String(text))) return null;
    const value = Number(text);
    return Number.isSafeInteger(value) && value >= low && value <= high ? value : null;
  }

  function piLabel(radians) {
    const turns = radians / Math.PI;
    if (Math.abs(turns) < 1e-9) return "0";
    for (const denominator of [1, 2, 3, 4, 6, 8, 12, 16]) {
      const numerator = Math.round(turns * denominator);
      if (Math.abs(turns * denominator - numerator) < 1e-6) {
        const sign = numerator < 0 ? "−" : "";
        const top = Math.abs(numerator) === 1 ? "π" : `${Math.abs(numerator)}π`;
        return denominator === 1 ? `${sign}${top}` : `${sign}${top}/${denominator}`;
      }
    }
    return `${turns.toFixed(3).replace("-", "−")}π`;
  }

  // Phase 0 is teal and phase π is rose, so + and − amplitudes are far apart on the wheel.
  function phaseHue(phase) { return (((170 + phase * 180 / Math.PI) % 360) + 360) % 360; }
  function phaseColor(re, im, lightness = 60) {
    if (Math.hypot(re, im) < 1e-9) return "hsl(215 12% 45%)";
    return `hsl(${Math.round(phaseHue(Math.atan2(im, re)))} 72% ${lightness}%)`;
  }
  function formatAmplitude(re, im) {
    const eps = 5e-7;
    const signed = (v) => `${v < 0 ? "−" : "+"}${Math.abs(v).toFixed(3)}`;
    if (Math.hypot(re, im) < eps) return "0";
    if (Math.abs(im) < eps) return signed(re);
    if (Math.abs(re) < eps) return `${signed(im)}i`;
    return `${Math.hypot(re, im).toFixed(3)}∠${piLabel(Math.atan2(im, re))}`;
  }

  // Orthographic view of the Bloch sphere: az turns about z, el tilts toward the viewer.
  // With the default view +z points up, +y to the right and +x toward the viewer (down-left).
  function project(vector, az, el) {
    const [x, y, z] = vector;
    const xr = x * Math.cos(az) - y * Math.sin(az);
    const yr = x * Math.sin(az) + y * Math.cos(az);
    return {h: yr, v: z * Math.cos(el) - xr * Math.sin(el), depth: xr * Math.cos(el) + z * Math.sin(el)};
  }

  function basisLabels(qubits) {
    return Array.from({length: 2 ** qubits}, (_, i) => i.toString(2).padStart(qubits, "0"));
  }
  function initialStep(qubits) {
    const size = 2 ** qubits;
    return {
      index: 0,
      label: `Start |${"0".repeat(qubits)}⟩`,
      amplitudes: Array.from({length: size}, (_, i) => [i === 0 ? 1 : 0, 0]),
      probabilities: Array.from({length: size}, (_, i) => (i === 0 ? 1 : 0)),
      bloch: Array.from({length: qubits}, () => [0, 0, 1]),
      bloch_length: Array.from({length: qubits}, () => 1)
    };
  }
  function blochNote(length) {
    if (length >= 0.999) return "pure state of its own";
    return "entangled: this qubit has no pure state of its own";
  }
  function describeGate(gate) {
    const info = GATES[gate.gate];
    const angle = info.angle ? `(${piLabel(gate.angle)})` : "";
    if (info.arity === 3) return `${info.label} on ${gate.qubits.map((q) => `q${q}`).join(", ")}`;
    if (info.arity === 2) {
      return gate.gate === "swap"
        ? `SWAP q${gate.qubits[0]} ↔ q${gate.qubits[1]}`
        : `${info.label}${angle} control q${gate.qubits[0]} → target q${gate.qubits[1]}`;
    }
    return `${info.label}${angle} on q${gate.qubits[0]}`;
  }
  function largestGap(counts, labels, probabilities, shots) {
    return Math.max(...labels.map((label, i) => Math.abs(counts[label] / shots - probabilities[i])));
  }

  return {
    MAX_QUBITS, MAX_GATES, MAX_SHOTS, MAX_SEED, GATES, PALETTE,
    layoutColumns, measuredQubits, placementProblem, keepWithinQubits, buildRequest, circuitKey,
    shotsFromSlider, sliderFromShots, parseBoundedInt, piLabel, phaseHue, phaseColor, formatAmplitude,
    project, basisLabels, initialStep, blochNote, describeGate, largestGap
  };
})();
if (typeof module !== "undefined" && module.exports) module.exports = PlaygroundCore;

if (typeof document !== "undefined") (() => {
  const C = PlaygroundCore;
  const SVG_NS = "http://www.w3.org/2000/svg";
  const $ = (id) => document.getElementById(id);
  const state = {
    qubits: 2, gates: [], history: [], presetId: null, presets: [],
    armed: null, placing: [], angle: Math.PI / 2,
    shots: 1024, seed: 20260928,
    result: null, resultKey: "", resultCircuitKey: "", lastSteps: null,
    step: 0, view: {az: -0.5, el: 0.35},
    inFlight: false, queued: false, pending: false, retries: 0, timer: null, spheres: []
  };

  // ---------------------------------------------------------------- small DOM helpers
  function svg(tag, attrs = {}, parent = null) {
    const node = document.createElementNS(SVG_NS, tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
    if (parent) parent.append(node);
    return node;
  }
  function svgText(parent, x, y, content, attrs = {}) {
    const node = svg("text", {x, y, ...attrs}, parent);
    node.textContent = content;
    return node;
  }
  function element(tag, className, content) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (content !== undefined) node.textContent = content;
    return node;
  }
  function cssNumber(name, fallback) {
    try {
      const value = parseFloat(getComputedStyle(document.documentElement).getPropertyValue(name));
      return Number.isFinite(value) ? value : fallback;
    } catch (error) { return fallback; }
  }
  function setStatus(message) { $("pg-status").textContent = message; }
  function showError(message) { $("pg-error").textContent = message; $("pg-error").hidden = !message; }

  // ---------------------------------------------------------------- editing
  function snapshot() {
    return {qubits: state.qubits, presetId: state.presetId, gates: state.gates.map((g) => ({...g, qubits: [...g.qubits]}))};
  }
  function commit(change, message) {
    state.history.push(snapshot());
    if (state.history.length > 200) state.history.shift();
    change();
    state.placing = [];
    state.step = state.gates.length;
    showError("");
    renderAll();
    setStatus(message);
    scheduleRequest();
  }
  function arm(name) {
    const arity = C.GATES[name].arity;
    if (arity > state.qubits) { showError(arity === 2 ? "Two-qubit gates need at least 2 qubits." : `${C.GATES[name].label} needs ${arity} qubits.`); return; }
    state.armed = name;
    state.placing = [];
    showError("");
    renderPalette(); renderPlacement();
    setStatus(`${C.GATES[name].label} chosen. ${arity > 1 ? "Now choose the first qubit." : "Now choose a qubit."}`);
  }
  function roleName(name, index) {
    if (name === "swap") return ["first qubit", "second qubit"][index];
    if (C.GATES[name].arity === 3) return ["first qubit", "second qubit", "third qubit"][index];
    return ["control", "target"][index];
  }
  function place(qubit) {
    if (!state.armed) { setStatus("Choose a gate from the palette first."); return; }
    const info = C.GATES[state.armed];
    let gate;
    if (info.arity > 1) {
      if (state.placing.includes(qubit)) { showError("Choose a different qubit for the next end of the gate."); return; }
      if (state.placing.length < info.arity - 1) {
        state.placing.push(qubit);
        renderPlacement();
        setStatus(`${info.label}: ${roleName(state.armed, state.placing.length - 1)} is q${qubit}. Now choose the ${roleName(state.armed, state.placing.length)}.`);
        return;
      }
      gate = {gate: state.armed, qubits: [...state.placing, qubit]};
    } else {
      gate = {gate: state.armed, qubits: [qubit]};
    }
    if (info.angle) gate.angle = state.angle;
    const problem = C.placementProblem(state.gates, gate, state.qubits);
    if (problem) { state.placing = []; renderPlacement(); showError(problem); return; }
    commit(() => { state.gates.push(gate); state.presetId = null; }, `Added ${C.describeGate(gate)}.`);
  }
  function removeGate(index) {
    const gate = state.gates[index];
    if (!gate) return;
    commit(() => { state.gates.splice(index, 1); state.presetId = null; }, `Removed ${C.describeGate(gate)}.`);
  }
  function undo() {
    const previous = state.history.pop();
    if (!previous) { setStatus("Nothing to undo."); return; }
    state.qubits = previous.qubits; state.gates = previous.gates; state.presetId = previous.presetId;
    state.placing = []; state.step = state.gates.length;
    if (state.armed && C.GATES[state.armed].arity > state.qubits) state.armed = null;
    showError(""); renderAll(); setStatus("Undid the last change."); scheduleRequest();
  }
  function reset() {
    if (!state.gates.length) { setStatus("The circuit is already empty."); return; }
    commit(() => { state.gates = []; state.presetId = null; }, "Circuit cleared. Undo brings it back.");
  }
  function setQubits(count) {
    if (count === state.qubits || !Number.isInteger(count) || count < 1 || count > C.MAX_QUBITS) return;
    state.removedByResize = 0;
    commit(() => {
      const kept = C.keepWithinQubits(state.gates, count);
      const removed = state.gates.length - kept.length;
      state.gates = kept; state.qubits = count; state.presetId = null;
      if (state.armed && C.GATES[state.armed].arity > count) state.armed = null;
      state.removedByResize = removed;
    }, `Now ${count} qubit${count > 1 ? "s" : ""}.`);
    if (state.removedByResize) setStatus(`Now ${count} qubit${count > 1 ? "s" : ""}. Removed ${state.removedByResize} gate(s) on qubits that no longer exist; Undo restores them.`);
  }
  function loadPreset(preset) {
    commit(() => {
      state.qubits = preset.qubits;
      state.gates = preset.gates.map((g) => ({...g, qubits: [...g.qubits]}));
      state.presetId = preset.id;
      if (state.armed && C.GATES[state.armed].arity > state.qubits) state.armed = null;
    }, `Loaded preset: ${preset.title}.`);
  }

  // ---------------------------------------------------------------- server requests
  function scheduleRequest(delay = 120) {
    clearTimeout(state.timer);
    state.pending = true;
    setBusy(state.inFlight);
    state.timer = setTimeout(() => { state.pending = false; sendRequest(); }, delay);
  }
  function wait(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
  async function sendRequest() {
    if (state.inFlight) { state.queued = true; return; }
    const body = JSON.stringify(C.buildRequest(state.qubits, state.gates, state.shots, state.seed));
    const circuitKey = C.circuitKey(state.qubits, state.gates);
    state.inFlight = true; setBusy(true);
    try {
      const response = await fetch("/api/circuit", {method: "POST", headers: {"Content-Type": "application/json"}, body, cache: "no-store"});
      let data = null;
      try { data = await response.json(); } catch (error) { data = null; }
      if (response.status === 429 && state.retries < 8) {
        state.retries += 1; state.queued = true; await wait(250);
      } else if (!response.ok || !data || !Array.isArray(data.steps)) {
        throw new Error(data && typeof data.error === "string" ? data.error : `Request failed (${response.status}).`);
      } else {
        state.retries = 0;
        state.result = data; state.resultKey = body; state.resultCircuitKey = circuitKey;
        showError("");
      }
    } catch (error) {
      showError(`Simulation failed: ${error.message}`);
    } finally {
      state.inFlight = false; setBusy(false);
    }
    if (state.queued) { state.queued = false; sendRequest(); return; }
    renderCircuit(); renderStepper(); renderViews(); renderMeasure();
  }
  function setBusy(busy) {
    const badge = $("pg-busy");
    const fresh = Boolean(state.result && state.resultCircuitKey === C.circuitKey(state.qubits, state.gates));
    let text = "IDLE · NOTHING SIMULATED YET", kind = "";
    if (busy) { text = "SIMULATING…"; kind = "warning"; }
    else if (state.pending || state.queued) { text = "QUEUED…"; kind = "warning"; }
    else if (fresh) { text = "UP TO DATE"; kind = "good"; }
    else if (state.gates.length) { text = "WAITING"; kind = "warning"; }
    badge.textContent = text;
    badge.className = `stage-badge ${kind}`;
  }
  function currentSteps() {
    if (state.result && state.resultCircuitKey === C.circuitKey(state.qubits, state.gates)) return state.result.steps;
    if (state.gates.length === 0) return [C.initialStep(state.qubits)];
    return null;
  }

  // ---------------------------------------------------------------- controls
  function renderPresets() {
    const row = $("pg-preset-buttons");
    row.replaceChildren();
    for (const preset of state.presets) {
      const button = element("button", "pg-chip", preset.title);
      button.type = "button";
      button.setAttribute("aria-pressed", String(state.presetId === preset.id));
      button.addEventListener("click", () => loadPreset(preset));
      row.append(button);
    }
    const active = state.presets.find((p) => p.id === state.presetId);
    $("pg-preset-caption").textContent = active ? active.caption : "Pick a preset, or build your own circuit below.";
  }
  function renderPalette() {
    const row = $("pg-palette-buttons");
    row.replaceChildren();
    for (const name of C.PALETTE) {
      const info = C.GATES[name];
      const button = element("button", `pg-chip pg-gate-chip pg-kind-${info.arity === 2 ? "two" : (name === "measure" ? "measure" : "one")}`, info.label);
      button.type = "button";
      button.draggable = true;
      button.setAttribute("aria-pressed", String(state.armed === name));
      button.setAttribute("aria-label", `${info.label}: ${info.name}`);
      button.title = info.name;
      button.disabled = info.arity > state.qubits;
      button.addEventListener("click", () => arm(name));
      button.addEventListener("dragstart", (event) => {
        if (event.dataTransfer) { event.dataTransfer.setData("text/plain", name); event.dataTransfer.effectAllowed = "copy"; }
        arm(name);
      });
      row.append(button);
    }
    const rotation = Boolean(state.armed && C.GATES[state.armed].angle);
    $("pg-angle-row").hidden = !rotation;
    $("pg-angle-output").textContent = C.piLabel(state.angle);
  }
  function renderPlacement() {
    const row = $("pg-place-buttons");
    row.replaceChildren();
    for (let q = 0; q < state.qubits; q++) {
      const button = element("button", "pg-chip", `q${q}`);
      button.type = "button";
      button.disabled = !state.armed;
      button.setAttribute("aria-pressed", String(state.placing.includes(q)));
      button.setAttribute("aria-label", state.armed ? `Place ${C.GATES[state.armed].label} on qubit ${q}` : `Qubit ${q} (choose a gate first)`);
      button.addEventListener("click", () => place(q));
      row.append(button);
    }
    let prompt = "Choose a gate first.";
    if (state.armed) {
      const info = C.GATES[state.armed];
      if (info.arity === 1) prompt = `${info.label}${info.angle ? `(${C.piLabel(state.angle)})` : ""}: choose a qubit, or click its wire.`;
      else if (state.placing.length === 0) prompt = `${info.label}: choose the ${roleName(state.armed, 0)}.`;
      else prompt = `${info.label}: ${state.placing.map((q, i) => `${roleName(state.armed, i)} q${q}`).join(", ")}; choose the ${roleName(state.armed, state.placing.length)}.`;
    }
    $("pg-place-prompt").textContent = prompt;
  }
  function renderToolbar() {
    $("pg-qubits").value = String(state.qubits);
    $("pg-gate-count").textContent = `${state.gates.length} / ${C.MAX_GATES} GATES`;
    $("pg-undo").disabled = state.history.length === 0;
    $("pg-reset").disabled = state.gates.length === 0;
  }

  // ---------------------------------------------------------------- circuit diagram
  const LAYOUT = {left: 70, column: 54, top: 30, row: 58};
  function wireY(q) { return LAYOUT.top + q * LAYOUT.row; }
  function renderCircuit() {
    const root = $("pg-circuit");
    root.replaceChildren();
    const columns = C.layoutColumns(state.gates);
    const used = columns.length ? Math.max(...columns) + 1 : 0;
    const width = LAYOUT.left + Math.max(used + 1, 7) * LAYOUT.column + 16;
    const height = wireY(state.qubits - 1) + 34;
    root.setAttribute("viewBox", `0 0 ${width} ${height}`);
    const valid = Boolean(currentSteps());
    for (let q = 0; q < state.qubits; q++) {
      const y = wireY(q);
      svgText(root, 8, y + 5, `q${q} |0⟩`, {class: "pg-wire-label"});
      svg("line", {x1: LAYOUT.left - 10, y1: y, x2: width - 8, y2: y, class: "pg-wire"}, root);
      const target = svg("rect", {x: LAYOUT.left - 10, y: y - LAYOUT.row / 2 + 2, width: width - LAYOUT.left + 2, height: LAYOUT.row - 4, class: "pg-wire-target"}, root);
      target.addEventListener("click", () => place(q));
      target.addEventListener("dragover", (event) => { event.preventDefault(); target.classList.add("drop"); });
      target.addEventListener("dragleave", () => target.classList.remove("drop"));
      target.addEventListener("drop", (event) => {
        event.preventDefault();
        target.classList.remove("drop");
        const name = event.dataTransfer ? event.dataTransfer.getData("text/plain") : "";
        if (C.GATES[name] && name !== state.armed) arm(name);
        place(q);
      });
    }
    state.gates.forEach((gate, index) => drawGate(root, gate, index, columns[index], valid));
  }
  function drawGate(root, gate, index, column, valid) {
    const x = LAYOUT.left + column * LAYOUT.column + LAYOUT.column / 2;
    let stage = "future";
    if (valid) stage = index < state.step - 1 ? "applied" : (index === state.step - 1 ? "current" : "future");
    const group = svg("g", {class: `pg-gate pg-${stage}`, tabindex: 0, role: "button", "aria-label": `${C.describeGate(gate)}, gate ${index + 1} of ${state.gates.length}. Press Enter or Delete to remove it.`}, root);
    const info = C.GATES[gate.gate];
    if (info.arity === 3) {
      const ys = gate.qubits.map(wireY), top = Math.min(...ys), bottom = Math.max(...ys);
      svg("rect", {x: x - 18, y: top - 18, width: 36, height: bottom - top + 36, class: "pg-hit"}, group);
      svg("line", {x1: x, y1: top, x2: x, y2: bottom, class: "pg-link"}, group);
      for (const y of ys) svg("circle", {cx: x, cy: y, r: 6, class: "pg-dot"}, group);
    } else if (info.arity === 2) {
      const [a, b] = gate.qubits;
      const ya = wireY(a), yb = wireY(b);
      svg("rect", {x: x - 18, y: Math.min(ya, yb) - 18, width: 36, height: Math.abs(yb - ya) + 36, class: "pg-hit"}, group);
      svg("line", {x1: x, y1: ya, x2: x, y2: yb, class: "pg-link"}, group);
      if (gate.gate === "cx") {
        svg("circle", {cx: x, cy: ya, r: 6, class: "pg-dot"}, group);
        svg("circle", {cx: x, cy: yb, r: 14, class: "pg-target"}, group);
        svg("line", {x1: x - 14, y1: yb, x2: x + 14, y2: yb, class: "pg-link"}, group);
        svg("line", {x1: x, y1: yb - 14, x2: x, y2: yb + 14, class: "pg-link"}, group);
      } else if (gate.gate === "cz" || gate.gate === "cp") {
        svg("circle", {cx: x, cy: ya, r: 6, class: "pg-dot"}, group);
        svg("circle", {cx: x, cy: yb, r: 6, class: "pg-dot"}, group);
        if (gate.gate === "cp") svgText(group, x + 4, (ya + yb) / 2 + 3, C.piLabel(gate.angle), {class: "pg-gate-angle", "text-anchor": "start"});
      } else {
        for (const y of [ya, yb]) {
          svg("line", {x1: x - 8, y1: y - 8, x2: x + 8, y2: y + 8, class: "pg-link"}, group);
          svg("line", {x1: x - 8, y1: y + 8, x2: x + 8, y2: y - 8, class: "pg-link"}, group);
        }
      }
    } else {
      const y = wireY(gate.qubits[0]);
      svg("rect", {x: x - 19, y: y - 19, width: 38, height: 38, rx: 5, class: `pg-box${gate.gate === "measure" ? " pg-measure" : ""}`}, group);
      if (gate.gate === "measure") {
        svg("path", {d: `M ${x - 11} ${y + 6} A 12 12 0 0 1 ${x + 11} ${y + 6}`, class: "pg-meter"}, group);
        svg("line", {x1: x, y1: y + 6, x2: x + 8, y2: y - 8, class: "pg-meter"}, group);
      } else {
        svgText(group, x, y + (info.angle ? 1 : 6), info.label, {class: info.angle ? "pg-gate-label small" : "pg-gate-label", "text-anchor": "middle"});
        if (info.angle) svgText(group, x, y + 13, C.piLabel(gate.angle), {class: "pg-gate-angle", "text-anchor": "middle"});
      }
    }
    group.addEventListener("click", () => removeGate(index));
    group.addEventListener("keydown", (event) => {
      if (["Enter", " ", "Delete", "Backspace"].includes(event.key)) { event.preventDefault(); removeGate(index); }
    });
  }

  // ---------------------------------------------------------------- stepper
  function renderStepper() {
    const steps = currentSteps();
    const slider = $("pg-step");
    slider.max = String(state.gates.length);
    state.step = Math.min(Math.max(state.step, 0), state.gates.length);
    slider.value = String(state.step);
    const disabled = !steps;
    for (const id of ["pg-step", "pg-step-first", "pg-step-prev", "pg-step-next", "pg-step-last"]) $(id).disabled = disabled;
    if (!disabled) {
      $("pg-step-first").disabled = $("pg-step-prev").disabled = state.step === 0;
      $("pg-step-next").disabled = $("pg-step-last").disabled = state.step === state.gates.length;
    }
    const label = steps ? steps[state.step].label : "waiting for the local simulator…";
    $("pg-step-label").textContent = `Step ${state.step} / ${state.gates.length} · ${label}`;
    setBusy(state.inFlight);
  }
  function goToStep(step) {
    state.step = Math.min(Math.max(step, 0), state.gates.length);
    renderCircuit(); renderStepper(); renderViews();
  }

  // ---------------------------------------------------------------- state views
  function renderViews() {
    const steps = currentSteps();
    if (steps) state.lastSteps = {steps, qubits: state.qubits};
    $("pg-views").classList.toggle("stale", !steps);
    const shown = steps ? {step: steps[state.step], qubits: state.qubits} : (state.lastSteps ? {step: state.lastSteps.steps[state.lastSteps.steps.length - 1], qubits: state.lastSteps.qubits} : {step: C.initialStep(state.qubits), qubits: state.qubits});
    renderAmplitudes(shown.step, shown.qubits);
    renderBloch(shown.step, shown.qubits);
    renderProbabilities(shown.step, shown.qubits);
  }
  function barChartFrame(root, labelTop) {
    root.replaceChildren();
    const frame = {left: 46, right: 548, base: 176, top: 26};
    for (const level of [0, 0.5, 1]) {
      const y = frame.base - level * (frame.base - frame.top);
      svg("line", {x1: frame.left, y1: y, x2: frame.right, y2: y, class: level === 0 ? "pg-axis" : "pg-grid"}, root);
      svgText(root, frame.left - 8, y + 4, level === 0 ? "0" : level.toFixed(1), {class: "pg-tick", "text-anchor": "end"});
    }
    svgText(root, frame.left, 14, labelTop, {class: "pg-tick"});
    return frame;
  }
  function renderAmplitudes(step, qubits) {
    const root = $("pg-amplitudes");
    const frame = barChartFrame(root, "|amplitude|");
    const labels = C.basisLabels(qubits);
    const slot = (frame.right - frame.left) / labels.length;
    const barWidth = Math.min(46, slot * 0.6);
    const lightness = cssNumber("--phase-lightness", 60);
    const summary = [];
    labels.forEach((label, i) => {
      const [re, im] = step.amplitudes[i];
      const magnitude = Math.hypot(re, im);
      const x = frame.left + slot * (i + 0.5);
      const height = magnitude * (frame.base - frame.top);
      svg("rect", {x: x - barWidth / 2, y: frame.base - height, width: barWidth, height: Math.max(height, 0), rx: 2, fill: C.phaseColor(re, im, lightness), class: "pg-amp-bar"}, root);
      svgText(root, x, frame.base + 20, `|${label}⟩`, {class: "pg-basis", "text-anchor": "middle"});
      const text = C.formatAmplitude(re, im);
      svgText(root, x, frame.base + 40, text, {class: `pg-value${text.startsWith("−") ? " negative" : ""}`, "text-anchor": "middle"});
      if (magnitude > 5e-7) summary.push(`|${label}⟩ ${text}`);
    });
    root.setAttribute("aria-label", `Amplitudes: ${summary.join(", ") || "none"}; all other basis states 0.`);
    const table = $("pg-amp-table");
    table.replaceChildren();
    labels.forEach((label, i) => {
      const [re, im] = step.amplitudes[i];
      const row = element("tr");
      const head = element("th", "", `|${label}⟩`); head.scope = "row"; row.append(head);
      const phase = Math.hypot(re, im) < 5e-7 ? "—" : C.piLabel(Math.atan2(im, re));
      for (const value of [re.toFixed(6), im.toFixed(6), step.probabilities[i].toFixed(6), phase]) row.append(element("td", "", value));
      table.append(row);
    });
  }
  function renderProbabilities(step, qubits) {
    const root = $("pg-probabilities");
    const frame = barChartFrame(root, "probability");
    const labels = C.basisLabels(qubits);
    const slot = (frame.right - frame.left) / labels.length;
    const barWidth = Math.min(46, slot * 0.6);
    const parts = [];
    labels.forEach((label, i) => {
      const p = step.probabilities[i];
      const x = frame.left + slot * (i + 0.5);
      const height = p * (frame.base - frame.top);
      svg("rect", {x: x - barWidth / 2, y: frame.base - height, width: barWidth, height: Math.max(height, 0), rx: 2, class: "pg-prob-bar"}, root);
      svgText(root, x, frame.base - height - 6, p.toFixed(3), {class: "pg-value", "text-anchor": "middle"});
      svgText(root, x, frame.base + 20, `|${label}⟩`, {class: "pg-basis", "text-anchor": "middle"});
      if (p > 5e-7) parts.push(`|${label}⟩ ${p.toFixed(3)}`);
    });
    root.setAttribute("aria-label", `Probabilities: ${parts.join(", ")}.`);
  }
  function drawPhaseWheel() {
    const root = $("pg-phase-wheel");
    root.replaceChildren();
    const lightness = cssNumber("--phase-lightness", 60);
    const cx = 60, cy = 60, r = 38, wedges = 36;
    for (let k = 0; k < wedges; k++) {
      const a0 = (k / wedges) * 2 * Math.PI, a1 = ((k + 1) / wedges) * 2 * Math.PI, mid = (a0 + a1) / 2;
      const phase = mid > Math.PI ? mid - 2 * Math.PI : mid;
      svg("path", {d: `M ${cx} ${cy} L ${cx + r * Math.cos(a0)} ${cy - r * Math.sin(a0)} A ${r} ${r} 0 0 0 ${cx + r * Math.cos(a1)} ${cy - r * Math.sin(a1)} Z`, fill: C.phaseColor(Math.cos(phase), Math.sin(phase), lightness)}, root);
    }
    svg("circle", {cx, cy, r: 12, class: "pg-wheel-hole"}, root);
    for (const [label, x, y, anchor] of [["0", 104, 64, "start"], ["π/2", 60, 16, "middle"], ["π", 16, 64, "end"], ["−π/2", 60, 114, "middle"]]) {
      svgText(root, x, y, label, {class: "pg-tick", "text-anchor": anchor});
    }
  }

  // ---------------------------------------------------------------- Bloch spheres
  function renderBloch(step, qubits) {
    const container = $("pg-bloch");
    if (state.spheres.length !== qubits) {
      container.replaceChildren();
      state.spheres = [];
      for (let q = 0; q < qubits; q++) {
        const figure = element("figure", "pg-sphere");
        const root = svg("svg", {viewBox: "0 0 220 226", role: "img", tabindex: 0, class: "pg-sphere-svg"});
        const caption = element("figcaption");
        figure.append(root, caption);
        container.append(figure);
        attachRotation(root);
        state.spheres.push({root, caption, vector: [0, 0, 1], length: 1, qubit: q});
      }
    }
    state.spheres.forEach((sphere, q) => {
      sphere.vector = step.bloch[q];
      sphere.length = step.bloch_length[q];
      drawSphere(sphere);
    });
  }
  function drawSphere(sphere) {
    const {root, vector, length, qubit, caption} = sphere;
    root.replaceChildren();
    const cx = 110, cy = 110, R = 78, {az, el} = state.view;
    const point = (v) => { const p = C.project(v, az, el); return {x: cx + R * p.h, y: cy - R * p.v, depth: p.depth}; };
    svg("circle", {cx, cy, r: R, class: "pg-sphere-outline"}, root);
    const circles = [
      (t) => [Math.cos(t), Math.sin(t), 0],
      (t) => [Math.cos(t), 0, Math.sin(t)],
      (t) => [0, Math.cos(t), Math.sin(t)]
    ];
    circles.forEach((curve, index) => {
      let front = "", back = "";
      for (let k = 0; k < 72; k++) {
        const a = point(curve((k / 72) * 2 * Math.PI)), b = point(curve(((k + 1) / 72) * 2 * Math.PI));
        const segment = `M ${a.x.toFixed(1)} ${a.y.toFixed(1)} L ${b.x.toFixed(1)} ${b.y.toFixed(1)} `;
        if (a.depth + b.depth >= 0) front += segment; else back += segment;
      }
      svg("path", {d: back, class: `pg-ring back${index === 0 ? " equator" : ""}`}, root);
      svg("path", {d: front, class: `pg-ring${index === 0 ? " equator" : ""}`}, root);
    });
    for (const [v, label] of [[[0, 0, 1], "|0⟩"], [[0, 0, -1], "|1⟩"], [[1, 0, 0], "|+⟩"], [[0, 1, 0], "|+i⟩"]]) {
      const end = point(v), tip = point(v.map((c) => c * 1.2));
      svg("line", {x1: cx, y1: cy, x2: end.x, y2: end.y, class: "pg-axis-line"}, root);
      svgText(root, tip.x, tip.y + 4, label, {class: "pg-sphere-label", "text-anchor": "middle"});
    }
    const entangled = length < 0.999;
    if (length > 1e-6) {
      const tip = point(vector);
      svg("line", {x1: cx, y1: cy, x2: tip.x, y2: tip.y, class: `pg-arrow${entangled ? " entangled" : ""}`}, root);
      svg("circle", {cx: tip.x, cy: tip.y, r: 5, class: `pg-arrow-tip${entangled ? " entangled" : ""}`}, root);
    }
    svg("circle", {cx, cy, r: 3, class: "pg-center"}, root);
    svgText(root, 8, 18, `q${qubit}`, {class: "pg-sphere-title"});
    const [x, y, z] = vector.map((c) => (Math.abs(c) < 5e-7 ? 0 : c));
    caption.replaceChildren();
    caption.append(element("span", "pg-vector", `r = (${x.toFixed(2)}, ${y.toFixed(2)}, ${z.toFixed(2)}) · |r| = ${length.toFixed(3)}`));
    caption.append(element("span", entangled ? "pg-entangled" : "pg-pure", C.blochNote(length)));
    root.setAttribute("aria-label", `Qubit ${qubit} Bloch vector (${x.toFixed(2)}, ${y.toFixed(2)}, ${z.toFixed(2)}), length ${length.toFixed(3)}: ${C.blochNote(length)}. Use arrow keys to rotate the view.`);
  }
  function redrawSpheres() { state.spheres.forEach(drawSphere); }
  function rotate(dAz, dEl) {
    state.view.az += dAz;
    state.view.el = Math.min(1.45, Math.max(-1.45, state.view.el + dEl));
    redrawSpheres();
  }
  function attachRotation(root) {
    let drag = null;
    root.addEventListener("pointerdown", (event) => {
      drag = {x: event.clientX, y: event.clientY};
      if (root.setPointerCapture && event.pointerId !== undefined) root.setPointerCapture(event.pointerId);
    });
    root.addEventListener("pointermove", (event) => {
      if (!drag) return;
      rotate((event.clientX - drag.x) * 0.012, (event.clientY - drag.y) * 0.012);
      drag = {x: event.clientX, y: event.clientY};
    });
    const stop = () => { drag = null; };
    root.addEventListener("pointerup", stop);
    root.addEventListener("pointercancel", stop);
    root.addEventListener("keydown", (event) => {
      const moves = {ArrowLeft: [-0.12, 0], ArrowRight: [0.12, 0], ArrowUp: [0, -0.12], ArrowDown: [0, 0.12]};
      if (moves[event.key]) { event.preventDefault(); rotate(...moves[event.key]); }
    });
  }

  // ---------------------------------------------------------------- measurement panel
  function renderMeasure(fromRange = false) {
    $("pg-shots-output").textContent = state.shots.toLocaleString("en-US");
    // While the user drags the log slider, never write a rounded value back under the pointer.
    if (!fromRange) $("pg-shots-range").value = String(C.sliderFromShots(state.shots));
    $("pg-shots").value = String(state.shots);
    $("pg-seed").value = String(state.seed);
    const root = $("pg-histogram");
    root.replaceChildren();
    const current = JSON.stringify(C.buildRequest(state.qubits, state.gates, state.shots, state.seed));
    const result = state.result && state.resultKey === current ? state.result : null;
    if (!result) {
      svgText(root, 280, 116, state.inFlight || state.pending ? "Sampling…" : "No shots for this circuit yet", {class: "pg-empty", "text-anchor": "middle"});
      $("pg-histogram-caption").textContent = "No shots yet. Edit the circuit or press Sample shots.";
      root.setAttribute("aria-label", "No sampled histogram yet.");
      return;
    }
    const frame = barChartFrame(root, "fraction of shots");
    const labels = result.measured_labels;
    const slot = (frame.right - frame.left) / labels.length;
    const width = Math.min(24, slot * 0.32);
    const parts = [];
    labels.forEach((label, i) => {
      const exact = result.measured_probabilities[i];
      const sampled = result.counts[label] / result.shots;
      const x = frame.left + slot * (i + 0.5);
      const scale = frame.base - frame.top;
      svg("rect", {x: x - width - 2, y: frame.base - exact * scale, width, height: exact * scale, class: "pg-exact-bar"}, root);
      svg("rect", {x: x + 2, y: frame.base - sampled * scale, width, height: sampled * scale, class: "pg-sample-bar"}, root);
      svgText(root, x, frame.base + 20, label, {class: "pg-basis", "text-anchor": "middle"});
      svgText(root, x, frame.base + 38, `${result.counts[label]}`, {class: "pg-value", "text-anchor": "middle"});
      parts.push(`${label}: ${result.counts[label]} of ${result.shots} (exact ${exact.toFixed(3)})`);
    });
    svg("rect", {x: frame.right - 176, y: 6, width: 10, height: 10, class: "pg-exact-bar"}, root);
    svgText(root, frame.right - 162, 15, "exact", {class: "pg-tick"});
    svg("rect", {x: frame.right - 110, y: 6, width: 10, height: 10, class: "pg-sample-bar"}, root);
    svgText(root, frame.right - 96, 15, "sampled", {class: "pg-tick"});
    root.setAttribute("aria-label", `Sampled histogram. ${parts.join("; ")}.`);
    const measured = result.measured_qubits.map((q) => `q${q}`).join(", ");
    const gap = C.largestGap(result.counts, labels, result.measured_probabilities, result.shots);
    $("pg-histogram-caption").textContent = `${result.shots.toLocaleString("en-US")} shots · seed ${result.seed} · measured ${measured} (labels list the highest qubit first; without M gates every qubit is measured) · largest gap |sampled − exact| = ${gap.toFixed(3)}. More shots shrink the gap roughly like 1/√shots.`;
  }
  function setShots(value, fromRange = false) {
    if (value === null) { showError("Shots must be a whole number from 1 to 8,192."); renderMeasure(); return; }
    showError("");
    if (value === state.shots) return;
    state.shots = value; renderMeasure(fromRange); scheduleRequest(200);
  }
  function setSeed(value) {
    if (value === null) { showError("Seed must be a whole number from 0 to 2,147,483,647."); renderMeasure(); return; }
    showError("");
    if (value === state.seed) return;
    state.seed = value; renderMeasure(); scheduleRequest(200);
  }

  // ---------------------------------------------------------------- wiring
  function renderAll() {
    renderToolbar(); renderPresets(); renderPalette(); renderPlacement();
    renderCircuit(); renderStepper(); renderViews(); renderMeasure();
  }
  $("pg-qubits").addEventListener("change", (event) => setQubits(Number(event.target.value)));
  $("pg-undo").addEventListener("click", undo);
  $("pg-reset").addEventListener("click", reset);
  $("pg-angle").addEventListener("input", (event) => {
    const turns = Number(event.target.value);
    if (Number.isFinite(turns) && Math.abs(turns) <= 2) state.angle = turns * Math.PI;
    $("pg-angle-output").textContent = C.piLabel(state.angle);
    renderPlacement();
  });
  $("pg-step").addEventListener("input", (event) => goToStep(Number(event.target.value)));
  $("pg-step-first").addEventListener("click", () => goToStep(0));
  $("pg-step-prev").addEventListener("click", () => goToStep(state.step - 1));
  $("pg-step-next").addEventListener("click", () => goToStep(state.step + 1));
  $("pg-step-last").addEventListener("click", () => goToStep(state.gates.length));
  $("pg-shots-range").addEventListener("input", (event) => setShots(C.shotsFromSlider(Number(event.target.value)), true));
  $("pg-shots").addEventListener("change", (event) => setShots(C.parseBoundedInt(event.target.value, 1, C.MAX_SHOTS)));
  $("pg-seed").addEventListener("change", (event) => setSeed(C.parseBoundedInt(event.target.value, 0, C.MAX_SEED)));
  $("pg-sample").addEventListener("click", () => { setStatus("Sampling shots on local Aer…"); scheduleRequest(0); });
  document.addEventListener("praxis-theme-change", () => { drawPhaseWheel(); renderViews(); });

  async function loadPresets() {
    try {
      const response = await fetch("/api/circuit-presets", {cache: "no-store"});
      const data = await response.json();
      if (!response.ok || !Array.isArray(data.presets)) throw new Error("bad response");
      state.presets = data.presets;
      renderPresets();
    } catch (error) {
      $("pg-preset-caption").textContent = "Presets could not be loaded; you can still build circuits by hand.";
    }
  }

  $("pg-angle").value = String(state.angle / Math.PI);
  drawPhaseWheel();
  renderAll();
  setStatus("Ready. Nothing has been simulated yet: pick a preset or add a gate.");
  loadPresets();
})();
