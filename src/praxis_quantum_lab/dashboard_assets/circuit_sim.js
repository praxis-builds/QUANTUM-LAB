"use strict";

// The Circuit Playground simulator in plain JavaScript, for the static site (no server, no
// dependencies). A line-by-line port of src/praxis_quantum_lab/circuit_playground.py: the same
// request validation, gate conventions (Qiskit's RX/RY/RZ, CP, CCZ, CCX with [control, control,
// target]), basis order |q2 q1 q0> (index = sum of bit_k << k), Bloch vectors from reduced density
// matrices, and response fields. Exact states agree with Python to 1e-12
// (tests/js/circuit_sim.test.js against tests/fixtures/playground_states.json).
// One difference: shots come from a seeded JavaScript PRNG, not from Qiskit Aer, so the counts
// differ from the dashboard's for the same seed. Responses say so in `sampler`.
const PlaygroundSim = (() => {
  const MAX_QUBITS = 3, MAX_GATES = 30, MAX_SHOTS = 8192, MAX_SEED = 2147483647, MAX_ANGLE = 4 * Math.PI;
  const SAMPLER = "browser sampling, not Aer";
  const SINGLE = new Set(["h", "x", "y", "z", "s", "t"]);
  const ROTATION = new Set(["rx", "ry", "rz", "cp"]);
  const TWO = new Set(["cx", "cz", "swap", "cp"]);
  const THREE = new Set(["ccz", "ccx"]);
  const NAMES = new Set([...SINGLE, ...ROTATION, ...TWO, ...THREE, "measure"]);
  const R = Math.SQRT1_2;
  // 2x2 matrices as [[re, im], ...] in row order: m00, m01, m10, m11
  const FIXED = {
    h: [[R, 0], [R, 0], [R, 0], [-R, 0]],
    x: [[0, 0], [1, 0], [1, 0], [0, 0]],
    y: [[0, 0], [0, -1], [0, 1], [0, 0]],
    z: [[1, 0], [0, 0], [0, 0], [-1, 0]],
    s: [[1, 0], [0, 0], [0, 0], [0, 1]],
    t: [[1, 0], [0, 0], [0, 0], [Math.cos(Math.PI / 4), Math.sin(Math.PI / 4)]]
  };

  class RequestError extends Error {}
  const isInt = (value) => typeof value === "number" && Number.isInteger(value);
  const isPlainObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value);

  function rotationMatrix(name, angle) {
    const c = Math.cos(angle / 2), s = Math.sin(angle / 2);
    if (name === "rx") return [[c, 0], [0, -s], [0, -s], [c, 0]];
    if (name === "ry") return [[c, 0], [-s, 0], [s, 0], [c, 0]];
    if (name === "rz") return [[Math.cos(-angle / 2), Math.sin(-angle / 2)], [0, 0], [0, 0], [Math.cos(angle / 2), Math.sin(angle / 2)]];
    throw new RequestError(`Unknown rotation gate: ${name}`);
  }

  function parseGate(item, qubits) {
    const keys = isPlainObject(item) ? Object.keys(item) : [];
    if (!isPlainObject(item) || !("gate" in item) || !("qubits" in item) || keys.some((k) => !["gate", "qubits", "angle"].includes(k))) {
      throw new RequestError("Each gate needs exactly gate and qubits (plus angle for rx, ry, rz, cp).");
    }
    const name = item.gate;
    if (typeof name !== "string" || !NAMES.has(name)) throw new RequestError("Unsupported gate.");
    const wires = item.qubits;
    const arity = THREE.has(name) ? 3 : TWO.has(name) ? 2 : 1;
    if (!Array.isArray(wires) || wires.length !== arity || !wires.every((w) => isInt(w) && w >= 0 && w < qubits)) {
      throw new RequestError(`Gate ${name} needs ${arity} qubit index(es) inside the circuit.`);
    }
    if (new Set(wires).size !== wires.length) throw new RequestError("A multi-qubit gate needs different qubits.");
    const gate = {gate: name, qubits: [...wires]};
    if (ROTATION.has(name)) {
      const angle = item.angle;
      if (typeof angle !== "number" || !(Math.abs(angle) <= MAX_ANGLE)) throw new RequestError("angle must be a finite number from -4*pi to 4*pi.");
      gate.angle = angle;
    } else if ("angle" in item) {
      throw new RequestError(`Gate ${name} does not take an angle.`);
    }
    return gate;
  }

  // parse_circuit_request: every limit is checked before anything is simulated.
  function parseRequest(payload) {
    const fields = ["gates", "qubits", "seed", "shots"];
    if (!isPlainObject(payload) || Object.keys(payload).sort().join() !== fields.join()) {
      throw new RequestError("Provide exactly qubits, gates, shots, and seed.");
    }
    const qubits = payload.qubits;
    if (!isInt(qubits) || qubits < 1 || qubits > MAX_QUBITS) throw new RequestError(`qubits must be an integer from 1 to ${MAX_QUBITS}.`);
    for (const [field, low, high] of [["shots", 1, MAX_SHOTS], ["seed", 0, MAX_SEED]]) {
      if (!isInt(payload[field]) || payload[field] < low || payload[field] > high) throw new RequestError(`${field} must be an integer from ${low} to ${high}.`);
    }
    if (!Array.isArray(payload.gates) || payload.gates.length > MAX_GATES) throw new RequestError(`gates must be a list of at most ${MAX_GATES} gates.`);
    const gates = payload.gates.map((item) => parseGate(item, qubits));
    const measured = new Set();
    for (const gate of gates) {
      if (gate.gate === "measure") {
        if (measured.has(gate.qubits[0])) throw new RequestError("A qubit can be measured only once.");
        measured.add(gate.qubits[0]);
      } else if (gate.qubits.some((q) => measured.has(q))) {
        throw new RequestError("A measured qubit cannot be used by a later gate.");
      }
    }
    return {qubits, gates, shots: payload.shots, seed: payload.seed};
  }

  // A state is {re: Float64Array, im: Float64Array}; index = sum of bit_k << k.
  function zeroState(n) {
    const size = 2 ** n, re = new Float64Array(size), im = new Float64Array(size);
    re[0] = 1;
    return {re, im};
  }
  function permute(state, source) {  // new[i] = old[source(i)]
    const size = state.re.length, re = new Float64Array(size), im = new Float64Array(size);
    for (let i = 0; i < size; i++) { const j = source(i); re[i] = state.re[j]; im[i] = state.im[j]; }
    return {re, im};
  }
  function phase(state, where, pr, pi) {  // multiply amplitudes where(i) by pr + i·pi
    const size = state.re.length, re = Float64Array.from(state.re), im = Float64Array.from(state.im);
    for (let i = 0; i < size; i++) {
      if (where(i)) { const a = state.re[i], b = state.im[i]; re[i] = a * pr - b * pi; im[i] = a * pi + b * pr; }
    }
    return {re, im};
  }
  function applyMatrix(state, m, wire) {
    const size = state.re.length, re = Float64Array.from(state.re), im = Float64Array.from(state.im), bit = 1 << wire;
    for (let i = 0; i < size; i++) {
      if (i & bit) continue;
      const j = i | bit, ar = state.re[i], ai = state.im[i], br = state.re[j], bi = state.im[j];
      re[i] = m[0][0] * ar - m[0][1] * ai + m[1][0] * br - m[1][1] * bi;
      im[i] = m[0][0] * ai + m[0][1] * ar + m[1][0] * bi + m[1][1] * br;
      re[j] = m[2][0] * ar - m[2][1] * ai + m[3][0] * br - m[3][1] * bi;
      im[j] = m[2][0] * ai + m[2][1] * ar + m[3][0] * bi + m[3][1] * br;
    }
    return {re, im};
  }
  const bitOf = (i, q) => (i >> q) & 1;

  function applyGate(state, gate) {
    const name = gate.gate, w = gate.qubits;
    if (name === "measure") return state;
    if (name === "ccx") return permute(state, (i) => (bitOf(i, w[0]) && bitOf(i, w[1]) ? i ^ (1 << w[2]) : i));
    if (name === "ccz") return phase(state, (i) => bitOf(i, w[0]) && bitOf(i, w[1]) && bitOf(i, w[2]), -1, 0);
    if (name === "cx") return permute(state, (i) => (bitOf(i, w[0]) ? i ^ (1 << w[1]) : i));
    if (name === "cz") return phase(state, (i) => bitOf(i, w[0]) && bitOf(i, w[1]), -1, 0);
    if (name === "cp") return phase(state, (i) => bitOf(i, w[0]) && bitOf(i, w[1]), Math.cos(gate.angle), Math.sin(gate.angle));
    if (name === "swap") return permute(state, (i) => (bitOf(i, w[0]) !== bitOf(i, w[1]) ? i ^ (1 << w[0]) ^ (1 << w[1]) : i));
    const matrix = ROTATION.has(name) ? rotationMatrix(name, gate.angle) : FIXED[name];
    return applyMatrix(state, matrix, w[0]);
  }

  function circuitStates(parameters) {
    const states = [zeroState(parameters.qubits)];
    for (const gate of parameters.gates) states.push(applyGate(states[states.length - 1], gate));
    return states;
  }

  function probabilities(state) {
    const p = Array.from(state.re, (re, i) => re * re + state.im[i] * state.im[i]);
    const total = p.reduce((a, b) => a + b, 0);
    return p.map((value) => value / total);  // the Python code renormalises the same way
  }

  // Reduced density matrix of each qubit: rho = (I + r·sigma)/2.
  function blochVectors(state, n) {
    const vectors = [];
    for (let q = 0; q < n; q++) {
      let r00 = 0, r11 = 0, xr = 0, xi = 0;
      for (let i = 0; i < state.re.length; i++) {
        if (bitOf(i, q)) continue;
        const j = i | (1 << q), ar = state.re[i], ai = state.im[i], br = state.re[j], bi = state.im[j];
        r00 += ar * ar + ai * ai;
        r11 += br * br + bi * bi;
        xr += ar * br + ai * bi;  // rho01 = sum a * conj(b)
        xi += ai * br - ar * bi;
      }
      vectors.push([2 * xr, -2 * xi, r00 - r11]);
    }
    return vectors;
  }

  const clean = (value) => Math.round(value * 1e12) / 1e12 + 0;

  // Python's "%.3g" for the angle in gate labels.
  function formatG3(x) {
    if (x === 0) return Object.is(x, -0) ? "-0" : "0";
    const [mantissa, exponentText] = x.toExponential(2).split("e");
    const exponent = Number(exponentText);
    const strip = (text) => (text.includes(".") ? text.replace(/0+$/, "").replace(/\.$/, "") : text);
    if (exponent < -4 || exponent >= 3) return `${strip(mantissa)}e${exponent < 0 ? "-" : "+"}${String(Math.abs(exponent)).padStart(2, "0")}`;
    return strip(x.toFixed(Math.max(0, 2 - exponent)));
  }
  function gateLabel(gate) {
    const wires = gate.qubits.map((w) => `q${w}`).join(",");
    const angle = "angle" in gate ? ` (${formatG3(gate.angle / Math.PI)}π)` : "";
    return `${gate.gate.toUpperCase()}${angle} on ${wires}`;
  }

  function step(index, label, state, n) {
    const vectors = blochVectors(state, n);
    return {
      index, label,
      amplitudes: Array.from(state.re, (re, i) => [clean(re), clean(state.im[i])]),
      probabilities: probabilities(state).map(clean),
      bloch: vectors.map((v) => v.map(clean)),
      bloch_length: vectors.map((v) => clean(Math.hypot(...v)))
    };
  }

  function marginal(p, measured) {
    const result = new Array(2 ** measured.length).fill(0);
    p.forEach((value, index) => {
      let key = 0;
      measured.forEach((qubit, position) => { key |= bitOf(index, qubit) << position; });
      result[key] += value;
    });
    return result;
  }

  // mulberry32: a small, fast, seedable 32-bit generator. Fine for drawing teaching histograms;
  // it is not Aer's generator and not cryptographic.
  function prng(seed) {
    let a = seed >>> 0;
    return () => {
      a = (a + 0x6D2B79F5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function sampleCounts(p, shots, seed, width) {
    const random = prng(seed), counts = new Array(p.length).fill(0), cumulative = [];
    p.reduce((sum, value, i) => (cumulative[i] = sum + value), 0);
    for (let shot = 0; shot < shots; shot++) {
      const r = random() * cumulative[cumulative.length - 1];
      let k = 0;
      while (k < cumulative.length - 1 && r >= cumulative[k]) k++;
      counts[k] += 1;
    }
    return Object.fromEntries(counts.map((count, key) => [key.toString(2).padStart(width, "0"), count]));
  }

  // simulate_circuit: per-step exact states plus sampled counts, same fields as the server.
  function simulate(payload) {
    const parameters = parseRequest(payload);
    const n = parameters.qubits, gates = parameters.gates, states = circuitStates(parameters);
    const steps = [step(0, `Start |${"0".repeat(n)}⟩`, states[0], n)];
    gates.forEach((gate, i) => steps.push(step(i + 1, gateLabel(gate), states[i + 1], n)));
    const measuredGates = gates.filter((gate) => gate.gate === "measure").map((gate) => gate.qubits[0]).sort((a, b) => a - b);
    const measured = measuredGates.length ? measuredGates : Array.from({length: n}, (_, q) => q);
    const exact = marginal(probabilities(states[states.length - 1]), measured);
    return {
      qubits: n, gates, shots: parameters.shots, seed: parameters.seed,
      basis: Array.from({length: 2 ** n}, (_, i) => i.toString(2).padStart(n, "0")),
      basis_convention: "|q2 q1 q0>; q0 is the rightmost bit",
      steps,
      measured_qubits: measured,
      measured_labels: Array.from({length: 2 ** measured.length}, (_, i) => i.toString(2).padStart(measured.length, "0")),
      measured_probabilities: exact.map(clean),
      counts: sampleCounts(exact, parameters.shots, parameters.seed, measured.length),
      sampler: SAMPLER
    };
  }

  return {MAX_QUBITS, MAX_GATES, MAX_SHOTS, MAX_SEED, SAMPLER, RequestError, parseRequest, applyGate, circuitStates,
          probabilities, blochVectors, gateLabel, formatG3, marginal, prng, sampleCounts, simulate};
})();
if (typeof module !== "undefined" && module.exports) module.exports = PlaygroundSim;
