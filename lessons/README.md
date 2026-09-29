# Foundations lessons

Six short lessons, one idea each, using this repo's own code and local Aer only (no cloud, no hardware). Do them in order; each builds on the last. Run every script from the repo root with `.venv/bin/python`.

Each lesson has a `.py` script and a `.md` page: the idea in plain words, three "predict first" questions, how to run, and what you should see. **Answer the questions before you run the script.** The answers sit at the bottom of the `.md` page under "Spoiler". Plots go to `lessons/out/` (git-ignored).

| # | Lesson | One-line idea | Uses |
|---|---|---|---|
| 01 | [One qubit](01_one_qubit.md) | Amplitudes squared are probabilities, and shots only estimate them | `state_vectors.py`, Aer |
| 02 | [Interference](02_interference.md) | H, H returns to 0 because paths cancel; a classical coin cannot do this | `state_vectors.py`, Aer |
| 03 | [Phase](03_phase.md) | A hidden sign changes nothing you can measure, until interference reveals it | `state_vectors.py`, Aer |
| 04 | [Entanglement](04_entanglement.md) | Perfect correlation with 50/50 marginals; why the kernel's last CZ cancels | Aer, `kernel_spectrum.py` |
| 05 | [Grover search](05_grover.md) | One oracle call finds the marked item of four; interference does useful work | Aer |
| 06 | [Noise](06_noise.md) | Depolarizing noise erases the phase relations, and success falls toward 25% | `density_matrices.py`, Aer |

Run one lesson: `.venv/bin/python lessons/02_interference.py`. Run all their checks: `.venv/bin/python -m pytest tests/test_lesson_0*.py`.

## Mapping to Coursera "Complete Quantum Computing Course for Beginners" (Course 1)

**Unverified.** I could not retrieve the module-by-module syllabus of Course 1. The public course page describes the specialization as covering qubits, superposition, quantum gates, entanglement and building circuits in Qiskit. This table matches the lessons to those concepts only. Check the real module list on the [course page](https://www.coursera.org/specializations/packt-the-complete-quantum-computing-course-for-beginners) and adjust.

| Concept named in the course description | Lessons |
|---|---|
| Qubits, superposition, measurement | 01, 02 |
| Quantum gates (H, X, Z, phase, CZ, CNOT) | 02, 03, 05 |
| Interference and phase | 02, 03, 05 |
| Entanglement (Bell state) | 04 |
| Building and running circuits in Qiskit | all (each uses Qiskit circuits on local Aer) |
| A first quantum algorithm (Grover) | 05 |
| Noise (usually a later topic, so this is extra) | 06 |

Not covered here: the quantum Fourier transform and other algorithms, real hardware, and programming-language basics.

## Honest limits

These are simulations on a classical computer, and the Grover lesson compares oracle calls on 4 items. Nothing here claims a quantum speed-up. The repo's rules on this (see `CLAUDE.md`) apply to lessons too.
