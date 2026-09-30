# Local quantum research dashboard

Start from this project's root with the existing WSL virtual environment:

```bash
.venv/bin/python -m praxis_quantum_lab.dashboard_server --port 8765
```

Open **http://127.0.0.1:8765** in a local browser. Keep the terminal running;
Ctrl+C stops the server. No package installation, external assets, CDN, account,
or quantum service is needed. An alternative port can be passed with `--port`;
the bind address is always `127.0.0.1` and is not configurable. Windows-to-WSL
access relies on the machine's existing localhost forwarding.

The server loads Qiskit and Aer once at start-up (a few seconds, before it
prints the URL). After that the page opens instantly, and **nothing simulates
until you act**: opening the page fetches only static files and the preset list.

The dashboard has three tabs: **Circuit Playground** (default), **Bell Lab** and
**Kernel Observatory**.

## Circuit Playground

Build circuits on 1–3 qubits and watch the state change.

- **Gates:** H, X, Y, Z, S, T, RX/RY/RZ (angle slider, −2π to 2π in steps of
  π/16), CNOT, CZ, CP (controlled phase: e^{iθ} on |11⟩, same angle slider), CCZ
  (sign flip on |111⟩ of its three qubits: three clicks), SWAP and M (measure). Choose a gate in the palette, then a
  qubit (the "Place on" buttons, or click its wire), or drag a gate onto a wire.
  Two-qubit gates take the control (or first qubit) and then the target. New
  gates go at the end of their wires. Click a placed gate, or focus it and press
  Delete or Enter, to remove it. Undo and Reset are always available. At most
  30 gates.
- **Amplitudes:** one bar per basis state. Height is |amplitude|, colour is the
  phase (the wheel beside the chart: 0 is teal, π is rose), and the value is
  written under each bar (for example −0.707 or 0.500∠π/2), so colour is never
  the only cue. The exact complex values are in an expandable table.
- **Bloch spheres:** one per qubit, drawn from that qubit's reduced density
  matrix. Drag, or focus and use the arrow keys, to rotate. The arrow has length
  |r|; when it is shorter than 1 the caption says "entangled: this qubit has no
  pure state of its own".
- **Probabilities:** the Born-rule |a|² for every basis state.
- **Step mode:** the slider and buttons replay the circuit gate by gate. Every
  step's state arrives with one request, so stepping never re-simulates.
- **Measure:** shots 1–8,192 (logarithmic slider or exact number) and a seed.
  The histogram shows sampled fractions next to the exact probabilities, plus the
  largest gap between them, which shrinks roughly like 1/√shots. M gates choose
  which qubits are sampled (all qubits if there are none). M is a deferred
  measurement: it never changes the exact state shown, and no gate may follow it
  on the same qubit.
- **Presets**, each with a one-line caption: Superposition (H); Interference
  (H·H returns to |0⟩); Phase is invisible until H (H·Z·H); Bell; GHZ (3 qubits);
  Grover search on 2 qubits (marked |11⟩, found with probability 1; the final −1
  is a global sign); Phase kickback; Deutsch–Jozsa constant and balanced
  (inputs read 00 only when f is constant); Bernstein–Vazirani (s = 101, the
  oracle written as its kicked-back phase, Z on q0 and q2); Simon (s = 11, with
  a one-qubit output: only 00 and 11 appear). The oracle presets fit in 3 qubits,
  so the qubit limit stays at 3; lessons 07–10 cover the full forms. QFT of a
  period-2 input (peaks at |000⟩ and |100⟩); Phase estimation of S (2 counting
  qubits read 01 = 1/4 every shot). Both use CP; lessons 11–12 go further. Grover
  search on 3 qubits (CCZ oracle marks |111⟩, found with probability 0.945 after 2
  steps; the diffusion writes H-then-X as RY(π/2) to fit the 30-gate cap).

Exact states come from the project's NumPy state-vector code (Hadamard, Pauli
matrices and Born rule from `state_vectors.py`); they are cross-checked against
Qiskit `Statevector` in the tests. Shots come from local Aer. Basis labels are
**|q2 q1 q0⟩**; q0 is the rightmost bit, as everywhere in the lab.

## Bell Lab

Nothing runs when the page opens. **Step next gate** computes H(q0), then
CX(q0,q1), then the selected channel on q0. **Run full circuit** computes all
three stages; **Reset** computes the initial state |00>. Each action recomputes
the chosen circuit prefix from |00> with the submitted settings; there is no
shared experiment session on the server. A successful response controls gate
highlights and readings. Edited settings leave earlier results labeled stale
until the next successful run.

The adapter reuses the project's Bell circuit, Hadamard, channel factories,
density-matrix functions, and Bell fidelity. Local Aer uses the same Kraus
operators and saves its density matrix before measurement. Counts are sampled
by Aer; displayed density matrices and probabilities describe the ensemble,
not one collapsed measurement.

All matrices use basis `00, 01, 10, 11`, displayed as **|q1 q0>**. Noise acts
on q0, the rightmost bit. Fidelity is always `<Phi+|rho|Phi+>` relative to
`Phi+ = (|00> + |11>)/sqrt(2)`, even at intermediate steps. Select the custom
or Aer matrix and its real or imaginary component. The expandable table also
provides complex entries without relying on color.

## Kernel Observatory

This area reads saved results only; it never re-runs the research experiment.
Select shot budget, simulator seed, and the matrix: **Raw**, **Clipped** or
**Higham**. Rows/columns retain the saved 28-training/12-test order. The cell
inspector exposes exact numerical values using keyboard-accessible inputs.

- **Raw** and **Clipped** come from `results/finite_shot_kernel_psd_repair.json`
  through `GET /api/kernel-results`. Their diagnostics and classifier metrics
  are the recorded values.
- **Higham** matrices were never saved, so `GET /api/kernel-repairs` recomputes
  them from the saved raw matrices with the same function used in
  [higham-vs-clipping.md](higham-vs-clipping.md). This is deterministic
  post-processing: nothing is sampled and nothing is written. The distances to
  the exact kernel are cross-checked against `results/higham_vs_clipping.json`,
  and the route fails closed (503) if they disagree by more than 1e-8. If it
  fails, the Raw and Clipped views keep working. No classifier metrics exist
  for Higham on this split; [repeated-model-comparison.md](repeated-model-comparison.md)
  compares it over 50 splits.
- **Eigenvalue spectrum:** the selected matrix's sorted eigenvalues on a
  symmetric-log scale, with a zero line. Negative eigenvalues are drawn as
  downward triangles below it, and the exact kernel's spectrum as hollow rings.
  The caption gives the negative count and the exact kernel's rank (16 of 40).
- **Distance to exact:** ‖K − K_exact‖_F for all three matrices, with the ratio
  to raw. The exact kernel is the statevector fidelity kernel on the same 40
  inputs.

**Both repairs change the measured data, and both are transductive**: they use
all 40 unlabeled inputs, including test inputs, but no test labels. They are
not a standard inductive evaluation. **Clipping lands further from the exact
kernel than the raw matrix** in all 15 saved matrices, because its unit-diagonal
rescale shrinks every off-diagonal entry. Higham's nearest-correlation repair
lands closer. The caption in the Observatory links the explanation, which the
server serves as plain text at `/docs/higham-vs-clipping.md`.

The full matrix's minimum eigenvalue differs from the training-only matrix
diagnostic in the preceding finite-shot study. Also, measuring a full upper
triangle changes the circuit ordering and therefore the assignment of seeded
draws relative to that earlier run. All results are small classical
simulations and do not demonstrate quantum advantage. The visualizations show
mathematical representations, not literal particle motion.

## Theme and accessibility

Dark is the default. The page follows the operating system's light-mode
preference, and the **Light theme** button in the header can force either
theme (remembered in this browser if storage is available). Colours are theme
tokens; tests check that body text meets WCAG AA contrast (4.5:1) and that
meaningful graphics meet 3:1 in both themes. Transitions are disabled under
`prefers-reduced-motion`. Every control is a native button, input, select or
radio, or a focusable SVG element with a label: gates in the circuit, Bloch
spheres (arrow keys rotate) and the placement buttons, so the Playground works
without a pointer.

## Local server boundaries

The only GET routes are `/`, `/app.js`, `/playground.js`, `/style.css`,
`/api/kernel-results`, `/api/kernel-repairs`, `/api/circuit-presets` and
`/docs/higham-vs-clipping.md`. The only POST routes are `/api/bell` and
`/api/circuit`.

`POST /api/bell` takes exactly these fields:

```json
{"channel":"amplitude_damping","strength":0.2,"shots":2048,"seed":20260928,"step":3}
```

Channel must be `bit_flip`, `amplitude_damping`, or `depolarizing`; strength
is finite and in [0,1]; shots is an integer in [1,8192]; seed is an integer
in [0,2147483647]; step is an integer in [0,3]. Body at most 1 KiB.

`POST /api/circuit` takes exactly these fields:

```json
{"qubits":2,"gates":[{"gate":"h","qubits":[0]},{"gate":"cx","qubits":[0,1]},{"gate":"ry","qubits":[1],"angle":0.5}],"shots":1024,"seed":20260928}
```

`qubits` is an integer in [1,3]; `gates` is a list of at most 30 gates; shots
is an integer in [1,8192]; seed is an integer in [0,2147483647]. Each gate has
exactly `gate` and `qubits`, plus `angle` only for `rx`, `ry`, `rz`, where it
is required, finite and in [−4π, 4π]. Allowed gates: `h x y z s t rx ry rz`
(one qubit), `cx cz swap` (two different qubits) and `measure` (one qubit, at
most once per qubit, and no later gate on that qubit). Qubit indices must be
integers inside the circuit; booleans are never accepted as numbers. Body at
most 4 KiB.

For both routes the server rejects extra keys, duplicate keys, non-finite JSON
values (including numbers too large for a float), traversal/query routes,
nonlocal Host and cross-origin requests. Aggregate headers/target length are
bounded, and reads time out after five seconds. There is at most one
simulation (Bell or circuit) and eight accepted connections at once; a second
simulation gets 429, and the Playground retries. The saved result files are
each bounded to 8 MiB and schema-checked. No arbitrary paths, directories,
subprocesses, or long experiment endpoints are exposed. All responses carry
the same Content-Security-Policy (`script-src 'self'`, `style-src 'self'`, no
inline scripts or styles), `nosniff` and `DENY` framing headers.

This standard-library server is intended for one local user, not deployment
or multi-user hosting. Runs are ephemeral and never write experiment results.

**Fixed crash (found during this upgrade):** the original server imported Qiskit
lazily inside a request thread, and the *next* simulation request crashed the
process with a segmentation fault inside Qiskit's native circuit code (Qiskit
2.5.2 / Aer 0.17.2). Any second Bell run triggered it. Pytest never saw it,
because pytest imports Qiskit on the main thread. The server now loads Qiskit
and Aer at start-up, and `tests/test_dashboard_process.py` starts the real
entry point in a fresh interpreter and sends repeated requests.

## Verification

```bash
.venv/bin/python -m pytest
```

What the tests cover:

- Server: request limits, route/host/origin restrictions, saved-result
  failures, Bell stages and channel limits, and every circuit validation rule.
  NumPy states match Qiskit for random 1–3 qubit circuits. Presets reach their
  expected states (H·H = |0⟩, Bell ½/½, GHZ, Grover success = 1, kickback,
  DJ 00 only for constant, BV → 101, Simon outcomes orthogonal to s, QFT peaks,
  QPE → 01, 3-qubit Grover 0.945; CP and CCZ match Qiskit in the random circuits). Bloch
  vectors have length 1 for product states and 0 for Bell/GHZ. The repair view
  agrees with the saved files and fails closed.
- Real process: the documented entry point in a fresh interpreter, with
  repeated Bell and circuit requests (the crash regression).
- Front end, without a browser: static checks that every element id used by the
  scripts exists once in `index.html` and that the page has no inline scripts,
  styles or external assets. Theme tokens are checked for completeness and
  contrast. With Node installed, pure logic is unit-tested (`tests/js/`), and the
  real `playground.js` and `app.js` run on a small DOM stand-in against a real
  dashboard process. That run clicks presets, builds and edits circuits
  (including drag-and-drop), steps, samples shots, rotates spheres, switches
  Observatory matrices and themes, and runs Bell step/run/reset. The Node tests
  are skipped when Node is absent.

**Not verified:** nothing here renders the page in a real browser, so layout,
colours as drawn, drag-and-drop in a real browser, and screen-reader output have
not been checked by a test. The earlier note that "browser smoke tests" existed
was not backed by any test in the repository.
