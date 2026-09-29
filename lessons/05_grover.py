"""Lesson 05: Grover search on 2 qubits. One quantum step finds the marked item."""

from __future__ import annotations

import numpy as np
from qiskit.quantum_info import Statevector

from _common import SEED, heading
from _grover import circuit_from_layers, grover_layers, stage_boundaries
from praxis_quantum_lab.qiskit_experiments import ideal_counts

MARKED = "10"
SHOTS = 2000
ITEMS = ("00", "01", "10", "11")


def amplitudes_after(marked: str, layer_count: int) -> np.ndarray:
    circuit = circuit_from_layers(grover_layers(marked)[:layer_count])
    return Statevector(circuit).data.real


def show(label: str, amplitudes: np.ndarray, marked: str) -> None:
    text = "  ".join(f"|{item}>:{(amplitudes[int(item, 2)] + 0.0):+.2f}" for item in ITEMS)
    print(f"{label:<28} {text}   P(marked {marked}) = {amplitudes[int(marked, 2)] ** 2:.2f}")


def classical_average_guesses(rng: np.random.Generator, trials: int = 200_000) -> tuple[float, float]:
    """Guess items in random order without repeats. After 3 misses the 4th is known,
    so the search never needs more than 3 guesses."""
    positions = rng.integers(1, 5, size=trials)  # uniform position of the marked item
    guesses = np.minimum(positions, 3)
    return (1 + 2 + 3 + 3) / 4, float(guesses.mean())


def main() -> dict:
    heading(f"Step 1: amplitudes after each stage (marked item = |{MARKED}>)")
    bounds = stage_boundaries(MARKED)
    start = np.array([1.0, 0.0, 0.0, 0.0])
    show("start |00>", start, MARKED)
    stages = {}
    for stage, count in bounds.items():
        stages[stage] = amplitudes_after(MARKED, count)
        show(f"after {stage}", stages[stage], MARKED)
    print("The oracle only flips ONE sign, which is invisible to a measurement (Lesson 03).")
    print("The diffusion step then turns that hidden sign into a large amplitude by interference.")

    heading("Step 2: the same circuit measured on local Aer")
    counts = ideal_counts(circuit_from_layers(grover_layers(MARKED), measure=True), shots=SHOTS, seed=SEED)
    print(f"counts over {SHOTS} shots: {counts}")

    heading("Step 3: every possible marked item")
    success = {}
    for item in ITEMS:
        final = amplitudes_after(item, len(grover_layers(item)))
        success[item] = float(final[int(item, 2)] ** 2)
        print(f"marked |{item}>: probability of measuring it after ONE Grover step = {success[item]:.6f}")

    heading("Step 4: classical guessing")
    exact, simulated = classical_average_guesses(np.random.default_rng(SEED))
    print(f"exact average number of guesses = (1 + 2 + 3 + 3) / 4 = {exact:.2f}")
    print(f"simulated over 200000 random orders               = {simulated:.3f}")
    print("Grover used the oracle once. This is a toy comparison of oracle calls for 4 items,")
    print("not a speed claim: any real advantage needs many items and a fair classical baseline.")
    return {
        "stages": {key: value.tolist() for key, value in stages.items()},
        "counts": counts,
        "success": success,
        "classical_exact": exact,
        "classical_simulated": simulated,
    }


if __name__ == "__main__":
    main()
