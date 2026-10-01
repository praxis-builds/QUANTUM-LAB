# PRAXIS QUANTUM LAB — CODEX HANDOFF
## Reconstructed project conversation and working context
**Conversation period:** September 28–29, 2026  
**Purpose:** Give Codex enough historical context to understand what Praxis Quantum Lab is, why it exists, what has already been built/tested, what results were observed, and what direction was next.

> **Important provenance note**
> This is a reconstructed handoff from the Quantum Lab conversation context that remains accessible to ChatGPT. It preserves the substantive project decisions, reported implementation state, experiment results, constraints, and next-step instructions. It is not claimed to be a word-for-word export of every utterance in the original voice/chat conversation.

---

# 1. PROJECT INTENT

The user wanted to create a separate **Praxis Quantum Lab** rather than mix quantum-computing work into unrelated projects.

The project began as a local, simulator-first environment for learning quantum computing by actually building experiments rather than consuming theory passively.

The working philosophy became:

**Theory → Prediction → Code → Result → Explain the mismatch**

The goal is not to claim quantum advantage. The goal is to understand quantum-computing mechanics experimentally and compare quantum-inspired/quantum-kernel behavior against classical baselines under controlled, reproducible conditions.

The project should remain useful as a learning laboratory:
- understand state vectors and amplitudes,
- understand gates and tensor products,
- understand measurement,
- build Bell-state experiments,
- understand density matrices,
- introduce noise through channels/Kraus operators,
- compare ideal mathematical models against Qiskit Aer simulation,
- build quantum kernels,
- compare them fairly with classical kernels,
- investigate finite-shot effects,
- inspect numerical/PSD failures rather than hiding them,
- visualize the experiments through a local interactive lab/dashboard.

---

# 2. WORKFLOW / RESPONSIBILITY SPLIT

A deliberate workflow was established:

- **ChatGPT conversation:** brainstorming, reasoning, teaching, experiment design, reviewing results, and writing strong implementation prompts.
- **Codex:** actual code changes and project-file modifications.
- The user later wanted to test another coding agent alongside Codex on the same project.

The project was initially developed from the Codex desktop app rather than entirely inside VS Code.

The user prefers large, coherent implementation prompts instead of many tiny prompts because of model-usage limits.

---

# 3. PROJECT LOCATION

The project was originally reported on Windows as:

`C:/Users/PRAXIS/Projects/praxis-quantum-lab`

Later, while setting up a WSL-oriented working environment, the intended WSL path was discussed as:

`~/projects/praxis-quantum-lab`

The broader development environment is the user's Praxis lab setup.

When reconciling the uploaded source tree, **trust the actual uploaded filesystem structure over this historical path note.**

---

# 4. ORIGINAL PROJECT BRIEF

The initial experiment was framed approximately as:

**Praxis Quantum Lab 01 — Classical vs Quantum-Kernel Classification**

The project was required to be:
- local,
- simulator-only,
- reproducible,
- educational,
- testable,
- explicit about limitations,
- free from unsupported claims of quantum advantage.

Core technologies:
- Python
- NumPy
- Qiskit
- Qiskit Aer
- scikit-learn
- matplotlib
- pytest

The initial build direction included three broad layers.

## Layer A — Quantum mechanics from scratch

Implement and inspect:
- state vectors,
- amplitudes,
- normalization,
- common single-qubit gates,
- tensor products,
- multi-qubit states,
- measurement probabilities.

The point was to understand the mathematics before letting Qiskit abstract it away.

## Layer B — Qiskit/Aer experiments

Build circuits in Qiskit and simulate them locally with Aer.

Bell-state experiments were central:
1. initialize `|00>`
2. apply Hadamard to the first qubit
3. apply CNOT
4. produce the Bell state
5. measure/simulate
6. compare theoretical expectation with simulator output.

For a 1,000-shot ideal Bell experiment, the prediction should be approximately:
- 500 counts `00`
- 500 counts `11`
- little or no `01` / `10`

The exact counts fluctuate because sampling is finite.

## Layer C — Classical vs quantum-kernel classification

Build a controlled classification experiment with:
- a fixed dataset,
- fixed train/test split,
- deterministic random seeds,
- a classical RBF-kernel baseline,
- a quantum feature map/kernel,
- accuracy,
- precision,
- recall,
- F1,
- confusion matrix,
- timing,
- explicit qubit/circuit-depth reporting,
- reproducibility information,
- documented limitations.

The comparison must be fair. A simulator result must not be described as proof of quantum computational advantage.

---

# 5. LEARNING METHOD

The project was intentionally shifted away from "keep adding features" toward **understanding-first experimentation**.

Before running an experiment:

1. State the theory.
2. Predict what should happen.
3. Run the code.
4. Inspect the actual result.
5. Explain any mismatch.

Examples:

### Bell state
Prediction:
`P(00) ≈ 0.5`
`P(11) ≈ 0.5`
`P(01) ≈ 0`
`P(10) ≈ 0`

Then run Aer and compare finite-shot counts.

### Noise
Predict how a specific noise channel should alter:
- populations,
- coherence,
- fidelity,
- measurement counts.

Then compare:
- hand-derived / NumPy/Kraus result,
- Qiskit Aer result.

### Kernel
Predict what finite sampling should do to a similarity matrix, then inspect:
- symmetry,
- diagonal behavior,
- eigenvalues,
- positive-semidefinite status,
- classifier behavior.

The mismatch itself is part of the lesson.

---

# 6. REPORTED ENVIRONMENT STATE

At one project checkpoint the local `.venv` reportedly contained:

- NumPy `2.5.3`
- scikit-learn `1.9.1`
- Qiskit `2.5.2`
- Qiskit Aer `0.17.2`
- matplotlib `3.11.2`
- pytest `9.1.1`
- setuptools `84.0.0`

At that checkpoint the project reportedly had **34 tests**.

Codex should verify the uploaded project's actual current dependency files and test count rather than assuming these historical versions remain authoritative.

---

# 7. REPORTED CORE MODULES / EXPERIMENT AREAS

The project history referenced work corresponding to modules/areas including:

- `state_vectors`
- `qiskit_experiments`
- `kernel_experiment`
- `density_matrices`
- density-matrix noise experiments
- Bell-state noise analytics
- finite-shot kernel experiments
- PSD analysis / repair follow-up
- runners/tests
- saved results

Historical filenames mentioned in project context include:

- `state_vectors.py`
- `qiskit_experiments.py`
- `kernel_experiment.py`
- `density_matrices.py`
- `density_matrix_noise.py`
- `bell_noise_analytics.py`
- `finite_shot_kernel.py`

There were also later noise/analytics/finite-shot/PSD modules.

**Do not create duplicates solely because a historical filename appears here. Inspect the actual uploaded repository first.**

---

# 8. STATE-VECTOR WORK

The early lab work covered state-vector mechanics directly.

Conceptual targets:
- represent `|0>` and `|1>`,
- build superpositions,
- apply gates,
- verify normalization,
- form multi-qubit states with tensor products,
- compute probabilities from amplitude magnitudes,
- compare manual/NumPy behavior against Qiskit.

The educational goal was to connect code to the underlying linear algebra instead of treating Qiskit circuits as opaque objects.

---

# 9. QISKIT / BELL-STATE WORK

Qiskit Aer was used as the local simulation backend.

Bell-state experiments were used as a reference system because they are simple enough to derive manually but rich enough to expose:
- entanglement,
- measurement correlations,
- density matrices,
- decoherence/noise,
- finite-shot sampling.

The ideal Bell state was a recurring baseline for later noise work.

---

# 10. DENSITY MATRICES

The lab expanded from pure state vectors into density matrices.

The purpose was to make mixed states and noisy evolution explicit.

The project explored:
- converting pure states into density matrices,
- inspecting diagonal populations,
- inspecting off-diagonal coherence,
- comparing ideal Bell-state density matrices against noisy states,
- understanding why a state vector alone is insufficient for general noisy/open-system evolution.

This led naturally into Kraus-channel experiments.

---

# 11. KRAUS / NOISE EXPERIMENTS

Noise channels were implemented/analyzed with density matrices and Kraus operators.

A key validation pattern was:

**manual/Kraus model vs Qiskit Aer simulation**

The project used Bell-state noise as an analytics target and checked whether the mathematical channel implementation and Aer produced consistent behavior.

The important learning link was:

state amplitudes → density matrices → Kraus operators → noisy density matrix → measurement statistics/fidelity.

The project was not intended to merely display noisy counts. It was intended to explain *why* the distribution and state changed.

---

# 12. CLASSICAL RBF VS QUANTUM KERNEL

The project included a classification experiment comparing:
- a classical RBF kernel,
- a quantum-kernel approach.

The comparison included or was required to include:
- fixed data,
- fixed split,
- reproducible seeds,
- classification metrics,
- timing,
- confusion matrix,
- quantum circuit characteristics,
- limitations.

A reported experiment included a **5×10 kernel evaluation**.

The lab treats this comparison as an experiment in representation/kernel behavior, **not evidence that the simulated quantum method is computationally superior to the classical baseline.**

---

# 13. FINITE-SHOT QUANTUM KERNEL

The project then moved beyond exact/statevector-style kernel values and investigated what happens when kernel similarities are estimated from finite measurement shots.

Shot budgets used:

- `128`
- `512`
- `2048`

This was important because finite-shot estimation introduces sampling noise into individual pairwise similarities.

The experiment exposed a deeper numerical issue:

> Even when pairwise estimates individually look reasonable, the assembled empirical kernel matrix may cease to be positive semidefinite.

That became the next experiment rather than being treated as an inconvenience to hide.

---

# 14. PSD-VIOLATION FOLLOW-UP

A dedicated follow-up experiment was implemented using the existing feature map.

Reported experimental design:

- **40-point subset**
- fixed **28/12 train/test split**
- shot budgets: **128 / 512 / 2048**
- **five simulator seeds** per shot budget
- total: **15 finite-shot runs**
- all **780 unique pairs** measured for each run
- raw measured matrix saved
- repaired matrix saved beside it

Why 780?

For 40 points, the number of unique unordered pairs is:

`40 × 39 / 2 = 780`

The diagonal does not need a distinct pair measurement in that count.

---

# 15. PSD RESULTS

Across all 15 runs:

- every raw finite-shot kernel matrix was indefinite,
- every repaired matrix was PSD within tolerance `1e-10`.

Reported mean raw minimum eigenvalues:

| Shots | Mean raw minimum eigenvalue |
|---:|---:|
| 128 | `-0.3571` |
| 512 | `-0.1784` |
| 2048 | `-0.0892` |

This showed a clear trend:

**More shots reduced the magnitude of the PSD violation, but did not eliminate it in the tested runs.**

Reported repaired minimum eigenvalues were effectively numerical zero, on the order of `10^-15`, and all repaired matrices passed the `1e-10` PSD tolerance.

One reported table included:

| Shots | Mean raw min eigenvalue | Mean repaired min eigenvalue | Raw PSD | Repaired PSD |
|---:|---:|---:|---:|---:|
| 128 | `-0.3571` | approx. `-2.23e-15` | `0/5` | `5/5` |
| 512 | `-0.1784` | approx. `-2.57e-15` | `0/5` | `5/5` |
| 2048 | `-0.0892` | effectively zero | `0/5` | `5/5` |

A reported mean Frobenius change for the 128-shot repair was approximately:

`1.5838`

The original experiment output should be treated as authoritative for any additional exact values.

---

# 16. PSD REPAIR METHOD

The repair procedure:

1. eigendecompose the noisy measured kernel,
2. clip negative eigenvalues,
3. reconstruct the matrix,
4. renormalize the diagonal.

Important caveat explicitly recorded in the project discussion:

> The repair changes the measured similarities and is **not guaranteed to produce the nearest correlation matrix**.

That limitation matters. Do not silently describe the repaired matrix as the mathematically optimal correction.

The repaired classifier reportedly tied the exact/reference classifier in the discussed follow-up, but Codex should inspect the actual result files before making any stronger statement about metrics.

---

# 17. INTERPRETATION OF THE PSD EXPERIMENT

The important scientific/engineering observation was not merely "repair works."

It was:

- exact quantum kernels have mathematical structure,
- finite-shot estimates perturb individual entries,
- independently noisy entries can collectively violate global PSD structure,
- increasing shots reduces sampling error,
- lower sampling error reduced the observed negative eigenvalue magnitude,
- PSD projection can restore a matrix usable by kernel methods,
- but projection modifies the empirical measurements.

This is exactly the kind of mismatch the lab is designed to expose.

---

# 18. DASHBOARD / VIRTUAL LAB DIRECTION

After the experiment chain, the next major direction was an **interactive virtual Quantum Lab dashboard**.

The user wanted a place where simulations could be run and results inspected visually rather than only through scripts/terminal output.

Because model usage was limited, the dashboard prompt was deliberately narrowed instead of requesting a giant rewrite.

The focused dashboard specification had two primary areas.

## A. Bell Lab

A live local simulator interface for Bell/noise experiments.

Desired controls/output included:
- run a Bell simulation,
- select/adjust noise,
- shot count,
- inspect measurement counts,
- inspect density matrix information,
- inspect fidelity,
- compare ideal vs noisy behavior.

The dashboard should use the existing experiment code rather than reimplementing quantum logic unnecessarily.

## B. Kernel Observatory

A visualization layer over the saved finite-shot/PSD experiment results.

Desired inspection dimensions included:
- shot budget,
- simulator seed,
- raw vs repaired kernel,
- minimum eigenvalue,
- PSD status,
- repair distance/change,
- classifier metrics,
- saved result data.

The goal was to make the finite-shot → PSD violation → repair chain visually understandable.

---

# 19. DASHBOARD TECHNICAL CONSTRAINTS

The narrowed implementation prompt specified approximately:

- local-only dashboard,
- vanilla Python backend where practical,
- HTML/CSS/JavaScript frontend,
- no unnecessary package installation,
- no external network dependency,
- no cloud execution,
- no QPU,
- bind only to `127.0.0.1`,
- bounded/safe API inputs,
- reuse existing simulation modules,
- add tests/smoke checks,
- preserve existing experiments and tests.

This was deliberately scoped to conserve coding-agent usage.

---

# 20. RESOURCE / MODEL-USAGE CONTEXT

At the dashboard stage the user reported approximately **65% Astra Ultra usage remaining** and expected to use Astra Ultra at around `1.5×`.

Because of that, the implementation request was narrowed to one coherent dashboard task instead of spending usage on multiple exploratory prompts.

Later the user observed that the high-capability coding model consumed usage extremely quickly, reinforcing the preference for efficient prompts.

---

# 21. CODING-AGENT / IDE CONTEXT

The user later wanted a separate VS Code working environment for the Quantum Lab and wanted multiple coding agents to be able to inspect/work on the same source tree.

A WSL-oriented VS Code launch command discussed was:

```bash
code --new-window ~/projects/praxis-quantum-lab
```

Historical note: earlier project context reported the project on Windows at:

```text
C:/Users/PRAXIS/Projects/praxis-quantum-lab
```

Codex should determine which path corresponds to the actual uploaded/current repository and avoid assuming both are synchronized copies.

---

# 22. WHAT CODEX SHOULD ASSUME NOW

When this handoff is given to Codex together with the actual project folder:

1. **Inspect the repository first.**
2. Treat existing code/tests/result files as the source of truth for implementation details.
3. Use this document to recover the *intent and history* behind those files.
4. Do not rewrite working experiments merely to match filenames in this document.
5. Preserve reproducibility.
6. Preserve simulator-only operation unless explicitly told otherwise.
7. Do not add cloud/QPU dependencies without explicit instruction.
8. Do not claim quantum advantage from simulator comparisons.
9. Preserve the theory → prediction → code → result → explain-mismatch learning structure.
10. Run the existing test suite before and after substantial changes.

---

# 23. EXPECTED CURRENT PROJECT CAPABILITIES

Based on the last accessible project discussion, the repository should contain some or all of the following working capabilities:

- manual state-vector experiments,
- Qiskit/Aer circuit experiments,
- Bell-state simulation,
- density-matrix experiments,
- Kraus/noise modeling,
- comparison of mathematical noise evolution with Aer,
- Bell noise analytics,
- classical RBF baseline,
- quantum-kernel classification,
- finite-shot kernel estimation,
- finite-shot experiments at 128/512/2048 shots,
- PSD diagnostics,
- PSD repair,
- saved experiment results,
- automated tests.

At one checkpoint, **34 tests** were reported.

Verify rather than assuming this remains the current count.

---

# 24. NEXT LOGICAL STATE OF WORK

The last major intended build was the local interactive dashboard / virtual lab.

Before implementing anything new, Codex should determine whether dashboard work already exists in the uploaded repository.

If it does:
- audit it against the Bell Lab + Kernel Observatory intent,
- run tests,
- identify missing or broken functionality,
- continue from the existing implementation.

If it does not:
- use the dashboard constraints in this handoff as the intended next feature,
- reuse existing experiment modules rather than duplicating their physics/math logic.

---

# 25. PROJECT PRINCIPLES TO PRESERVE

### Understanding over feature count
A new experiment is valuable when it reveals something about the system.

### Predict before running
Write down the expected behavior before seeing simulator output.

### Explain discrepancies
Unexpected output is an investigation target.

### Reproducibility
Seeds, shot counts, splits, feature maps, and relevant configuration should be explicit.

### Classical baselines matter
Quantum-kernel results should be compared against a reasonable classical baseline.

### Simulator honesty
Aer simulation is not physical quantum hardware.

### No unsupported quantum-advantage claims
A simulator experiment cannot establish practical quantum advantage.

### Preserve numerical pathology
Do not hide raw indefinite finite-shot kernels. Their failure is scientifically useful.

### Repair transparently
When PSD projection is used, report that it changes measured similarities and is not necessarily the nearest correlation-matrix correction.

### Local-first
The project was intentionally designed to work locally without cloud/QPU dependencies.

---

# 26. CODEX STARTING INSTRUCTION

**Read this document, then inspect the entire Praxis Quantum Lab repository before changing anything.**

Reconstruct the current architecture from the actual source tree and result files. Run the existing tests. Compare what exists against the historical project state described here.

Then report:

1. current repository structure,
2. implemented experiments,
3. current test status,
4. available saved results,
5. whether the finite-shot PSD follow-up is fully present,
6. whether a dashboard already exists,
7. discrepancies between this handoff and the actual repository,
8. the smallest sensible next step.

Do **not** modify files during that first audit unless explicitly instructed.

---

# 27. COMPACT CONTEXT FOR A NEW AGENT

Praxis Quantum Lab is a local simulator-only Python/Qiskit learning lab. It began with manual state vectors and Qiskit Bell experiments, expanded into density matrices and Kraus/noise validation against Aer, then into classical RBF vs quantum-kernel classification. The lab subsequently studied finite-shot quantum kernels at 128/512/2048 shots. A 40-point, fixed 28/12 experiment measured all 780 unique pairs for each of 15 runs (3 shot budgets × 5 seeds). Every raw measured kernel was indefinite; every eigenvalue-clipped/diagonal-renormalized repaired kernel was PSD within `1e-10`. Mean raw minimum eigenvalues improved from about `-0.3571` at 128 shots to `-0.1784` at 512 and `-0.0892` at 2048. The repair modifies measured similarities and is not guaranteed to be the nearest correlation matrix. The next planned feature was a localhost-only interactive dashboard with a live Bell/noise lab and a finite-shot PSD Kernel Observatory. ChatGPT handled reasoning/prompts; Codex handled code changes. Preserve tests, reproducibility, local-only operation, and the theory → prediction → code → result → explain-mismatch workflow.

---

**End of reconstructed Quantum Lab handoff.**
