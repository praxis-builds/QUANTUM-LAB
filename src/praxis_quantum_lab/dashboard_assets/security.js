"use strict";

// Security Lab: BB84, a toy RSA break with Shor, Grover key search (all simulated by the server on
// local Aer, reusing the lessons' code) and a Mosca calculator (pure arithmetic, computed here).
// SecurityCore holds pure helpers so they can be unit-tested with Node, without a browser.
const SecurityCore = (() => {
  const MAX_SEED = 2147483647;

  function clampInt(value, low, high) {
    const number = Math.round(Number(value));
    return Number.isFinite(number) ? Math.min(high, Math.max(low, number)) : low;
  }
  function bb84Request(values) {
    return {qubits: clampInt(values.qubits, 200, 20000), noise: Math.min(0.2, Math.max(0, Number(values.noise) || 0)),
            sample: clampInt(values.sample, 10, 2000), eve: Boolean(values.eve), seed: clampInt(values.seed, 0, MAX_SEED)};
  }
  function rsaRequest(values) {
    return {n: Number(values.n) === 15 ? 15 : 21, seed: clampInt(values.seed, 0, MAX_SEED)};
  }
  function groverRequest(values) {
    return {key: clampInt(values.key, 0, 15), iterations: clampInt(values.iterations, 0, 8),
            pairs: Number(values.pairs) === 1 ? 1 : 2, seed: clampInt(values.seed, 0, MAX_SEED)};
  }
  // Mosca's inequality: data is at risk if x + y > z.
  function moscaVerdict(x, y, z) {
    const values = [x, y, z].map(Number);
    if (values.some((v) => !Number.isFinite(v) || v < 0)) return {valid: false, text: "Enter three numbers of years (0 or more)."};
    const [dx, dy, dz] = values;
    const slack = dz - (dx + dy);
    if (slack < 0) {
      return {valid: true, atRisk: true, slack,
              text: `AT RISK: x + y = ${dx + dy} years > z = ${dz}. Data protected today could still need to be secret when it can be broken. Start migrating now (${-slack} year${-slack === 1 ? "" : "s"} overdue).`};
    }
    return {valid: true, atRisk: false, slack,
            text: `Not yet at risk: x + y = ${dx + dy} years <= z = ${dz}. You have ${slack} year${slack === 1 ? "" : "s"} of slack, so start migrating no later than then. If z is optimistic, the slack disappears.`};
  }
  function percent(value, digits = 1) {
    return `${(100 * value).toFixed(digits)}%`;
  }
  // Polyline points for a probability curve in a w x h box with a margin.
  function chartPoints(values, width, height, margin) {
    const n = values.length;
    return values.map((v, i) => {
      const x = margin + (n === 1 ? 0 : (i * (width - 2 * margin)) / (n - 1));
      const y = height - margin - v * (height - 2 * margin);
      return [Number(x.toFixed(2)), Number(y.toFixed(2))];
    });
  }
  return {MAX_SEED, bb84Request, rsaRequest, groverRequest, moscaVerdict, percent, chartPoints};
})();
if (typeof module !== "undefined" && module.exports) module.exports = SecurityCore;

if (typeof document !== "undefined") (() => {
  const C = SecurityCore;
  const SVG_NS = "http://www.w3.org/2000/svg";
  const $ = (id) => document.getElementById(id);
  const busy = {bb84: false, rsa: false, grover: false};

  function element(tag, className, content) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (content !== undefined) node.textContent = content;
    return node;
  }
  function svg(tag, attrs, parent) {
    const node = document.createElementNS(SVG_NS, tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
    if (parent) parent.append(node);
    return node;
  }
  async function post(url, body) {
    for (let attempt = 0; attempt < 6; attempt++) {
      const response = await fetch(url, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body), cache: "no-store"});
      const data = await response.json();
      if (response.status === 429) { await new Promise((resolve) => setTimeout(resolve, 400)); continue; }
      if (!response.ok) throw new Error(typeof data.error === "string" ? data.error : `Request failed (${response.status}).`);
      return data;
    }
    throw new Error("The local simulator stayed busy; try again.");
  }
  async function run(kind, button, status, work) {
    if (busy[kind]) return;
    busy[kind] = true;
    $(button).disabled = true;
    $(status).textContent = "Simulating on local Aer…";
    try { await work(); } catch (error) { $(status).textContent = `Error: ${error.message}`; }
    finally { busy[kind] = false; $(button).disabled = false; }
  }

  // ------------------------------------------------------------------- BB84
  function bb84Values() {
    return {qubits: $("bb84-qubits").value, noise: $("bb84-noise").value, sample: $("bb84-sample").value,
            eve: $("bb84-eve").checked, seed: 20260928};
  }
  function bb84Outputs() {
    $("bb84-qubits-output").textContent = String(C.bb84Request(bb84Values()).qubits);
    $("bb84-noise-output").textContent = C.bb84Request(bb84Values()).noise.toFixed(2);
    $("bb84-sample-output").textContent = String(C.bb84Request(bb84Values()).sample);
  }
  for (const id of ["bb84-qubits", "bb84-noise", "bb84-sample"]) $(id).addEventListener("input", bb84Outputs);
  $("bb84-form").addEventListener("submit", (event) => {
    event.preventDefault();
    run("bb84", "bb84-run", "bb84-status", async () => {
      const r = await post("/api/security/bb84", C.bb84Request(bb84Values()));
      $("bb84-results").hidden = false;
      $("bb84-sifted").textContent = `${r.sifted} of ${r.qubits} qubits`;
      $("bb84-qber").textContent = `${C.percent(r.qber_estimate)} in the sample (true ${C.percent(r.qber_true)})`;
      $("bb84-detect").textContent = `${C.percent(r.p_detect, 4)}${r.errors_seen ? " · errors seen" : " · no errors seen"}`;
      $("bb84-key").textContent = r.key_bits > 0 ? `${r.key_bits} bits (keys equal: ${r.keys_equal})` : "none: aborted";
      $("bb84-status").textContent = `${r.status === "key" ? "Secret key distilled." : r.status}${r.sample_clipped ? " Sample reduced to half the sifted key." : ""}`;
      $("bb84-explain").textContent = r.eve
        ? `Eve measured every qubit and knows ${C.percent(r.eve_knows_fraction)} of the sifted key for certain, but she caused about 25% errors. Comparing ${r.sample} bits misses her with probability (3/4)^${r.sample}. Above 11% errors no secret key can be distilled.`
        : `Without Eve the errors come from channel noise, which Alice and Bob cannot tell apart from eavesdropping, so every error costs key length. Above 11% (Shor–Preskill) the protocol aborts.`;
    });
  });

  // -------------------------------------------------------------------- RSA
  $("rsa-form").addEventListener("submit", (event) => {
    event.preventDefault();
    run("rsa", "rsa-run", "rsa-status", async () => {
      const r = await post("/api/security/rsa", C.rsaRequest({n: $("rsa-n").value, seed: $("rsa-seed").value}));
      const list = $("rsa-steps");
      list.replaceChildren();
      const step = (text) => list.append(element("li", null, text));
      step(`Public key (N, e) = (${r.n}, ${r.e}). The attacker sees nothing else.`);
      for (const a of r.attempts) {
        step(`a = ${a.a}: Shor's circuit (${r.qubits} qubits) measured m = ${a.fraction}; continued fraction gives r = ${a.candidate}; ${a.check ? "check passes" : "check fails"} → ${a.outcome}.`);
      }
      if (r.status !== "key recovered") { $("rsa-status").textContent = r.status; return; }
      step(`Period r = ${r.period}, so N = ${r.factors[0]} × ${r.factors[1]} (from gcd(a^(r/2) ± 1, N)).`);
      step(`φ = (${r.factors[0]} − 1)(${r.factors[1]} − 1) = ${r.phi}; private key d = e⁻¹ mod φ = ${r.d}.`);
      step(`Ciphertext ${r.ciphertext.join(", ")} decrypts to "${r.decrypted}".`);
      $("rsa-status").textContent = `Key recovered from the public key alone (toy size: trial division would find ${r.factors[0]} instantly).`;
    });
  });

  // ----------------------------------------------------------------- Grover
  for (let k = 0; k < 16; k++) {
    const option = element("option", null, k.toString(2).padStart(4, "0"));
    option.value = String(k);
    $("grover-key").append(option);
  }
  $("grover-key").value = "11";
  $("grover-iterations").addEventListener("input", () => { $("grover-iterations-output").textContent = $("grover-iterations").value; });
  function drawGrover(r) {
    const chart = $("grover-chart");
    chart.replaceChildren();
    const W = 320, H = 150, M = 22;
    svg("line", {x1: M, y1: H - M, x2: W - M, y2: H - M, class: "sec-axis"}, chart);
    svg("line", {x1: M, y1: M, x2: M, y2: H - M, class: "sec-axis"}, chart);
    const points = C.chartPoints(r.curve.map((c) => c.p_secret), W, H, M);
    svg("polyline", {points: points.map((p) => p.join(",")).join(" "), class: "sec-curve"}, chart);
    const x = points[r.iterations][0];
    const y = H - M - r.measured_secret * (H - 2 * M);
    svg("circle", {cx: x, cy: y, r: 5, class: "sec-point"}, chart);
    const label = document.createElementNS(SVG_NS, "text");
    label.setAttribute("x", String(x + 6)); label.setAttribute("y", String(Math.max(M + 10, y - 6)));
    label.setAttribute("class", "sec-label");
    label.textContent = `measured ${C.percent(r.measured_secret, 0)}`;
    chart.append(label);
    chart.setAttribute("aria-label", `Theory curve of P(secret key) for 0 to 8 iterations; measured ${C.percent(r.measured_secret)} at ${r.iterations} iterations.`);
  }
  $("grover-form").addEventListener("submit", (event) => {
    event.preventDefault();
    run("grover", "grover-run", "grover-status", async () => {
      const r = await post("/api/security/grover", C.groverRequest({key: $("grover-key").value, iterations: $("grover-iterations").value,
                                                                  pairs: $("grover-pairs").value, seed: 20260928}));
      drawGrover(r);
      const over = r.iterations > r.optimal_iterations;
      $("grover-status").textContent = `${r.iterations} iterations on ${r.qubits} qubits: the secret key came out in ${C.percent(r.measured_secret)} of ${r.shots} shots (theory ${C.percent(r.curve[r.iterations].p_secret)}).`;
      $("grover-explain").textContent = `${r.matching_keys.length} key(s) fit the known pair(s): ${r.matching_keys.join(", ")}. Best: ${r.optimal_iterations} iterations${over ? "; you are past it, so success falls again (over-rotation)" : ""}. Classical brute force: ${r.classical_expected_trials} trials on average. Each quantum iteration runs the whole cipher reversibly, twice per pair.`;
    });
  });

  // ------------------------------------------------------------------ Mosca
  function mosca() {
    const verdict = C.moscaVerdict($("mosca-x").value, $("mosca-y").value, $("mosca-z").value);
    const node = $("mosca-verdict");
    node.textContent = verdict.text;
    node.className = `sec-verdict ${verdict.valid ? (verdict.atRisk ? "at-risk" : "ok") : ""}`;
    $("mosca-explain").textContent = "Mosca (2018): if x + y > z, data encrypted today with RSA or elliptic curves could be recorded now and decrypted later. Nobody knows z; try a pessimistic and an optimistic value.";
  }
  for (const id of ["mosca-x", "mosca-y", "mosca-z"]) $(id).addEventListener("input", mosca);
  $("mosca-form").addEventListener("submit", (event) => { event.preventDefault(); mosca(); });

  // Without a repository checkout the server cannot load the lessons' code: say so and keep only
  // the Mosca calculator (pure arithmetic in the browser) usable.
  fetch("/api/security/status", {cache: "no-store"}).then((response) => response.json()).then((status) => {
    if (status.available) return;
    const note = $("security-unavailable");
    note.textContent = `${status.reason} The Mosca calculator below still works.`;
    note.hidden = false;
    for (const id of ["bb84-run", "rsa-run", "grover-run"]) $(id).disabled = true;
  }).catch(() => {});

  bb84Outputs();
  mosca();
})();
