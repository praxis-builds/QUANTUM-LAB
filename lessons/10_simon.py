"""Lesson 10: Simon. Find a hidden XOR period s with a few quantum runs plus GF(2) algebra."""

from __future__ import annotations

import numpy as np
from qiskit import transpile
from qiskit_aer import AerSimulator

from _common import SEED, heading
from _oracles import dot, gf2_nullspace, gf2_rank, simon_circuit, simon_function
from praxis_quantum_lab.qiskit_experiments import ideal_counts

SECRETS = ("11", "110", "1010")
CHECK_SHOTS = 2000
REPEATS = 200  # independent end-to-end runs of the algorithm per s
CLASSICAL_TRIALS = 20_000


def measured_runs(s: str, shots: int, seed: int) -> list[int]:
    """One Aer shot = one run of the circuit (one oracle call). Returns the y of each run, in order."""
    simulator = AerSimulator(method="statevector")
    compiled = transpile(simon_circuit(s), simulator, seed_transpiler=seed)
    memory = simulator.run(compiled, shots=shots, seed_simulator=seed, memory=True).result().get_memory()
    return [int(bits, 2) for bits in memory]


def simon_solve(ys: list[int], n: int) -> tuple[int | None, int]:
    """Take runs one at a time until the y's span n - 1 dimensions; then the null space is {0, s}.

    Returns (s, runs used), or (None, runs) if the supply ran out.
    """
    for used in range(1, len(ys) + 1):
        if gf2_rank(ys[:used]) == n - 1:
            (s,) = gf2_nullspace(ys[:used], n)
            return s, used
    return None, len(ys)


def classical_collision_queries(s: str, rng: np.random.Generator) -> int:
    """Query distinct random x until two give the same f(x); then s = x XOR x'."""
    f = simon_function(s)
    seen: dict[int, int] = {}
    for queries, x in enumerate(rng.permutation(len(f)), start=1):
        if f[x] in seen:
            assert seen[f[x]] ^ int(x) == int(s, 2)
            return queries
        seen[f[x]] = int(x)
    raise AssertionError("a 2-to-1 function always collides")


def main() -> dict:
    heading("Step 1: the oracle hides a period s: f(x) = f(x XOR s), and no other collisions")
    for s in SECRETS:
        f = simon_function(s)
        n = len(s)
        pairs = sorted({tuple(sorted((x, x ^ int(s, 2)))) for x in range(2**n)})
        shown = ", ".join(f"f({a:0{n}b}) = f({b:0{n}b})" for a, b in pairs[:3])
        print(f"s = {s}: {shown}{', ...' if len(pairs) > 3 else ''}   ({len(set(f))} distinct outputs for {2**n} inputs)")

    heading(f"Step 2: every measured y satisfies y . s = 0 (mod 2)   ({CHECK_SHOTS} shots each)")
    checks = {}
    for s in SECRETS:
        counts = ideal_counts(simon_circuit(s), shots=CHECK_SHOTS, seed=SEED)
        dots = {y: dot(int(y, 2), int(s, 2)) for y in counts}
        checks[s] = {"counts": counts, "dots": dots}
        print(f"s = {s}: outcomes {sorted(counts)}  ->  y.s mod 2 = {sorted(set(dots.values()))}")
    print("Each run returns a random y ORTHOGONAL to s (half of all strings), never anything else.")

    heading("Step 3: solve for s over GF(2) (XOR arithmetic, Gaussian elimination)")
    solved = {}
    for index, s in enumerate(SECRETS):
        n = len(s)
        ys = measured_runs(s, shots=REPEATS * 4 * n, seed=SEED + index)
        first_s, first_runs = simon_solve(ys, n)
        print(f"s = {s}: first y's = {[format(y, f'0{n}b') for y in ys[:first_runs]]} -> s = {first_s:0{n}b} "
              f"after {first_runs} run(s)")
        runs_used, correct, cursor = [], 0, 0
        for _ in range(REPEATS):
            found, used = simon_solve(ys[cursor:], n)
            cursor += used
            runs_used.append(used)
            correct += found == int(s, 2)
        solved[s] = {"first": format(first_s, f"0{n}b"), "first_runs": first_runs,
                     "mean_runs": float(np.mean(runs_used)), "max_runs": max(runs_used), "correct": correct}
        print(f"          over {REPEATS} independent repeats: s found {correct}/{REPEATS} times, "
              f"mean {solved[s]['mean_runs']:.2f} runs, max {solved[s]['max_runs']}")

    heading("Step 4: the classical baseline (random queries until two outputs collide)")
    rng = np.random.default_rng(SEED)
    classical = {}
    for s in SECRETS:
        n = len(s)
        queries = [classical_collision_queries(s, rng) for _ in range(CLASSICAL_TRIALS)]
        classical[s] = {"mean": float(np.mean(queries)), "max": max(queries), "worst_case": 2 ** (n - 1) + 1}
        print(f"s = {s}: classical mean {classical[s]['mean']:.2f} queries, max seen {classical[s]['max']}, "
              f"worst case 2^(n-1)+1 = {classical[s]['worst_case']};  quantum mean {solved[s]['mean_runs']:.2f}, "
              f"max seen {solved[s]['max_runs']}")
    print("At n <= 4 there is no useful gap: the means are close, and the quantum method's unlucky")
    print("repeats need MORE calls than the classical worst case. The difference is only in how the")
    print("costs GROW: classical about 2^(n/2) queries (birthday collisions), quantum about n runs.")

    heading("Step 5: why this matters for RSA")
    print("Shor's algorithm uses exactly this hidden-period idea. It finds the period r of")
    print("f(x) = a^x mod N (f(x) = f(x + r)); from r, ordinary arithmetic gives the factors of N,")
    print("and factoring N breaks RSA. This toy breaks nothing: see the lesson page.")
    return {"checks": checks, "solved": solved, "classical": classical}


if __name__ == "__main__":
    main()
