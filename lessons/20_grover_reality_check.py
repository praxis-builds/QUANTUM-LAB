"""Lesson 20: reality check. What Grover's square root means for AES and SHA-256 (arithmetic only)."""

from __future__ import annotations

import math

from _common import heading

TARGETS = {  # name: bits of search space (key length, or hash output for a preimage)
    "AES-128 key": 128,
    "AES-192 key": 192,
    "AES-256 key": 256,
    "SHA-256 preimage": 256,
}
# NIST PQC evaluation criteria (security page of the 2016 call, csrc.nist.gov): quantum gates for an
# optimal key search on AES when circuit depth is capped at MAXDEPTH, and classical gates.
NIST_AES_QUANTUM_GATES_TIMES_MAXDEPTH = {"AES-128 key": 170, "AES-192 key": 233, "AES-256 key": 298}  # log2
NIST_AES_CLASSICAL_GATES = {"AES-128 key": 143, "AES-192 key": 207, "AES-256 key": 272}  # log2
NIST_MAXDEPTH = {"2^40 (about a year of serial gates, envisioned hardware)": 40,
                 "2^64 (about a decade of serial classical gates)": 64,
                 "2^96 (a millennium at the physical limit)": 96}
PARALLEL = (0, 10, 20, 30, 40, 48)  # log2 of the number of machines


def log2_grover_calls(bits: int) -> float:
    """(pi/4) * sqrt(2^bits) sequential oracle calls for one target."""
    return math.log2(math.pi / 4) + bits / 2


def parallel_grover(bits: int, log2_machines: int) -> tuple[float, float]:
    """Split the space into p parts, one Grover search each: every machine needs (pi/4) sqrt(N/p)
    sequential calls, and the total work is p times that = (pi/4) sqrt(N p). Returns log2 of both."""
    depth = math.log2(math.pi / 4) + (bits - log2_machines) / 2
    return depth, depth + log2_machines


def machines_for_depth(bits: int, log2_depth: float) -> float:
    """Smallest p (log2) with (pi/4) sqrt(N/p) <= 2^depth."""
    return bits - 2 * (log2_depth - math.log2(math.pi / 4))


def main() -> dict:
    heading("Step 1: sequential Grover calls, (pi/4) sqrt(N), against classical brute force (N/2)")
    calls = {}
    for name, bits in TARGETS.items():
        calls[name] = log2_grover_calls(bits)
        print(f"{name:<17}: Grover about 2^{calls[name]:.2f} calls, one after another;  classical about 2^{bits - 1}")
    print("Each call is a full reversible AES or SHA-256 circuit (compute and uncompute), not one step.")

    heading("Step 2: Grover parallelises badly (AES-128)")
    parallel = {}
    for log2_p in PARALLEL:
        depth, total = parallel_grover(128, log2_p)
        parallel[log2_p] = (depth, total)
        print(f"2^{log2_p:<2} machines: each runs 2^{depth:.2f} sequential calls; total work 2^{total:.2f}")
    need = machines_for_depth(128, 40)
    print(f"To finish within 2^40 sequential calls you need 2^{need:.1f} machines, and the total work")
    print(f"grows to 2^{40 + need:.1f} (= 2^40 x 2^{need:.1f}): p machines buy only a sqrt(p) speed-up.")
    print("(Counting oracle calls, not gates: each call is itself a deep circuit, which makes this worse.)")

    heading("Step 3: NIST's own yardstick (PQC call for proposals, 2016)")
    nist = {}
    for name in NIST_AES_QUANTUM_GATES_TIMES_MAXDEPTH:
        nist[name] = {label: NIST_AES_QUANTUM_GATES_TIMES_MAXDEPTH[name] - d for label, d in NIST_MAXDEPTH.items()}
        row = ", ".join(f"2^{value}" for value in nist[name].values())
        print(f"{name:<12}: quantum gates at MAXDEPTH 2^40 / 2^64 / 2^96: {row};  classical 2^{NIST_AES_CLASSICAL_GATES[name]}")
    print("Even with a decade-scale depth budget (2^64 serial gates), Grover on AES-128 needs about")
    print("2^106 quantum gates in total, each far more expensive than a classical gate.")

    heading("Step 4: the verdict")
    print("AES-256 and SHA-256 preimages: about 2^128 sequential calls even for Grover. Safe.")
    print("AES-128: about 2^64 sequential calls of a full AES circuit. The debated case; NIST says it")
    print("'will remain secure for decades to come' (PQC FAQ). Grover weakens symmetric crypto;")
    print("Shor (Lesson 16) breaks RSA outright. That is why the migration is about public-key crypto.")
    return {"calls": calls, "parallel": parallel, "machines_for_2_40": need, "nist": nist}


if __name__ == "__main__":
    main()
