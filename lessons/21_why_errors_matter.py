"""Lesson 21: why errors matter. Shor (N = 15) and Grover under per-gate depolarizing noise."""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
import numpy as np
from qiskit_aer import AerSimulator

from _common import SEED, heading, out_dir
from _grover_n import grover_circuit, marked_item_oracle, optimal_iterations
from _qec import gate_count, per_gate_noise, to_basis
from _shor import run_gives_order, shor_circuit

RATES = (0.0, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2)
SHOTS = 1000
SHOR_A, SHOR_N, SHOR_T = 7, 15, 8
GROVER_SIZES = (3, 4, 5)
MARKED = 5
WHERE_P = 0.01
N21_GATES_NOTE = (2, 21)  # a, N for the size-only estimate


def build() -> dict[str, dict]:
    circuits = {"Shor N=15": {"circuit": to_basis(shor_circuit(SHOR_A, SHOR_N, gate_level=True, measure=True), SEED),
                              "floor": float(np.mean([run_gives_order(SHOR_A, SHOR_N, m, SHOR_T) for m in range(2**SHOR_T)])),
                              "success": lambda m: run_gives_order(SHOR_A, SHOR_N, m, SHOR_T)}}
    for n in GROVER_SIZES:
        circuit = grover_circuit(n, marked_item_oracle(n, MARKED), optimal_iterations(2**n), measure=True)
        circuits[f"Grover n={n}"] = {"circuit": to_basis(circuit, SEED), "floor": 1 / 2**n, "success": lambda m: m == MARKED}
    return circuits


def success_rate(entry: dict, model) -> float:
    simulator = AerSimulator(method="statevector", noise_model=model)
    memory = simulator.run(entry["circuit"], shots=SHOTS, seed_simulator=SEED, memory=True).result().get_memory()
    return float(np.mean([entry["success"](int(bits, 2)) for bits in memory]))


def where_errors_hurt(entry: dict) -> dict:
    """Shor-15 at p = WHERE_P, with noise only on gates touching the counting register, or only on
    gates acting purely on the work register."""
    circuit = entry["circuit"]
    counting = set(range(SHOR_T))
    pairs = {tuple(circuit.find_bit(q).index for q in inst.qubits) for inst in circuit.data if inst.operation.name == "cx"}
    singles = {circuit.find_bit(inst.qubits[0]).index for inst in circuit.data if inst.operation.name == "u"}
    gates = {"counting": 0, "work": 0}
    for inst in circuit.data:
        if inst.operation.name in ("u", "cx"):
            touched = {circuit.find_bit(q).index for q in inst.qubits}
            gates["counting" if touched & counting else "work"] += 1
    models = {
        "counting": per_gate_noise(WHERE_P, qubits_1q=singles & counting, pairs_2q={p for p in pairs if set(p) & counting}),
        "work": per_gate_noise(WHERE_P, qubits_1q=singles - counting, pairs_2q={p for p in pairs if not set(p) & counting}),
    }
    return {part: {"gates": gates[part], "success": success_rate(entry, model)} for part, model in models.items()}


def plot(results: dict, circuits: dict):
    rates = [p for p in RATES if p > 0]
    figure, (left, right) = plt.subplots(1, 2, figsize=(12, 4.2))
    for name, row in results.items():
        label = f"{name} ({circuits[name]['gates']} gates)"
        left.semilogx(rates, [row["raw"][p] for p in rates], "o-", label=label)
        right.semilogx(rates, [row["normalised"][p] for p in rates], "o-", label=label)
    left.set_title("Success probability")
    right.set_title("Normalised: 1 = noiseless, 0 = random guessing")
    for axis in (left, right):
        axis.set_xlabel("depolarizing error per gate p")
        axis.legend(fontsize=8)
    left.set_ylabel("P(success)")
    figure.tight_layout()
    path = out_dir() / "21_why_errors_matter.png"
    figure.savefig(path, dpi=130)
    plt.close(figure)
    return path


def main() -> dict:
    heading("Step 1: the circuits, compiled to single-qubit gates (u) and CNOTs (cx)")
    circuits = build()
    for name, entry in circuits.items():
        entry["gates"] = gate_count(entry["circuit"])
        print(f"{name:<11}: {entry['circuit'].num_qubits:>2} qubits, {entry['gates']:>3} gates, "
              f"random-guess success {entry['floor']:.3f}")

    heading(f"Step 2: success vs depolarizing error p on every gate ({SHOTS} seeded shots each)")
    results = {}
    for name, entry in circuits.items():
        raw = {p: success_rate(entry, per_gate_noise(p)) for p in RATES}
        ideal, floor = raw[0.0], entry["floor"]
        normalised = {p: (raw[p] - floor) / (ideal - floor) for p in RATES}
        results[name] = {"raw": raw, "normalised": normalised}
        print(f"{name:<11}: " + "  ".join(f"p={p:g}: {raw[p]:.3f}" for p in RATES))
    print("\nNormalised (1 = noiseless, 0 = no better than guessing):")
    for name, row in results.items():
        print(f"{name:<11}: " + "  ".join(f"{row['normalised'][p]:+.2f}" for p in RATES[1:]))

    heading(f"Step 3: where do errors hurt Shor? (p = {WHERE_P} on part of the circuit only)")
    where = where_errors_hurt(circuits["Shor N=15"])
    for part, row in where.items():
        print(f"noise only on gates {'touching the counting register' if part == 'counting' else 'purely on the work register'}: "
              f"{row['gates']} gates, success {row['success']:.3f}")

    heading("Step 4: a bigger Shor, by size only (not simulated)")
    a, n = N21_GATES_NOTE
    big = gate_count(to_basis(shor_circuit(a, n, measure=True), SEED))
    estimates = {p: (1 - p) ** big for p in (1e-4, 1e-3, 1e-2)}
    print(f"Shor N = 21 compiles to {big} gates. A noisy run did not finish in 10 minutes here, so only a")
    print("rough estimate: P(no error anywhere) = (1 - p)^G = " +
          ", ".join(f"{v:.2g} at p = {p:g}" for p, v in estimates.items()))
    print("Shor for RSA-2048 runs for hours to days (Lesson 16's estimates): only error-corrected")
    print("logical qubits get the error per operation low enough for that.")
    path = plot(results, circuits)
    print(f"\nSaved {path}")
    return {"gates": {k: v["gates"] for k, v in circuits.items()}, "floors": {k: v["floor"] for k, v in circuits.items()},
            "results": results, "where": where, "n21_gates": big, "n21_estimates": estimates}


if __name__ == "__main__":
    main()
