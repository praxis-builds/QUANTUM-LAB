# Local quantum research dashboard

Start from this project's root with the existing WSL virtual environment:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/Users/PRAXIS/Projects/praxis-quantum-lab && .venv/bin/python -m praxis_quantum_lab.dashboard_server --port 8765"
```

Open **http://127.0.0.1:8765** in a local browser. Keep the terminal running;
Ctrl+C stops the server. No package installation, external assets, CDN, account,
or quantum service is needed. An alternative port can be passed with `--port`;
the bind address is always `127.0.0.1` and is not configurable. Windows-to-WSL
access relies on the machine's existing localhost forwarding.

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
not one collapsed measurement. The first run may be slower while Python loads
Qiskit and Aer.

All matrices use basis `00, 01, 10, 11`, displayed as **|q1 q0>**. Noise acts
on q0, the rightmost bit. Fidelity is always `<Phi+|rho|Phi+>` relative to
`Phi+ = (|00> + |11>)/sqrt(2)`, even at intermediate steps. Select the custom
or Aer matrix and its real or imaginary component. The expandable table also
provides complex entries without relying on color.

## Kernel Observatory

This area reads only `results/finite_shot_kernel_psd_repair.json` through
`GET /api/kernel-results`. It never re-runs the research experiment. Select
shot budget, simulator seed, and raw or repaired matrix. Matrix diagnostics
and classifier metrics are the recorded values; the browser does no kernel
simulation. Rows/columns retain the saved 28-training/12-test order. The cell
inspector exposes exact numerical values using keyboard-accessible inputs.

Repaired results are **transductive**: spectral repair used all 40 unlabeled
inputs, including test inputs, but no test labels. They are not a standard
inductive evaluation. The full matrix's minimum eigenvalue differs from the
training-only matrix diagnostic in the preceding finite-shot study. Also,
measuring a full upper triangle changes the circuit ordering and therefore
the assignment of seeded draws relative to that earlier run. All results are
small classical simulations and do not demonstrate quantum advantage. The
visualizations show mathematical representations, not literal particle motion.

## Local server boundaries

The only GET routes are `/`, `/app.js`, `/style.css`, and `/api/kernel-results`.
Only `POST /api/bell` accepts requests, with exactly these fields:

```json
{"channel":"amplitude_damping","strength":0.2,"shots":2048,"seed":20260928,"step":3}
```

Channel must be `bit_flip`, `amplitude_damping`, or `depolarizing`; strength
is finite and in [0,1]; shots is an integer in [1,8192]; seed is an integer
in [0,2147483647]; step is an integer in [0,3]. The server rejects extra keys,
duplicate keys, non-finite JSON values, traversal/query routes, nonlocal Host
and cross-origin requests. Request bodies are capped at 1 KiB; aggregate
headers/target length are bounded; reads time out after five seconds. There
is at most one Bell simulation and eight accepted connections at once. The
saved result file is bounded to 8 MiB and schema-checked. No arbitrary paths,
directories, subprocesses, or long experiment endpoints are exposed.

This standard-library server is intended for one local user, not deployment
or multi-user hosting. Runs are ephemeral and never write experiment results.

## Verification

```bash
.venv/bin/python -m pytest
```

The dashboard tests exercise request limits, route/host/origin restrictions,
saved-result failures, all circuit stages, channel limits, density-matrix
agreement, and fixed-seed counts. Browser smoke tests cover step/run/reset,
saved-matrix selection, and visible scientific labels.
