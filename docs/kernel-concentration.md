# Kernel concentration vs qubit count

Status: **pre-registered**. Committed before `kernel_concentration.py` existed and before any concentration statistic was computed. Results are appended later in separate commits; this part is never amended. This is the start of a thread, not a complete study.

## Theory

For expressive feature maps, off-diagonal fidelity-kernel values concentrate as q grows. For Haar-random states, E[K] = 1/2^q and Var(K) ≈ 1/4^q. Once the values between different samples are exponentially close together, telling them apart with a finite-shot estimate needs exponentially many shots. This is the known "exponential concentration" problem for quantum kernels. A standard mitigation is to scale the features down (bandwidth α), which keeps states close together.

### A correction to my plan: the final CZ chain cancels

For the existing map (one layer: H, RZ(x), RY(x²) on each qubit, then a CZ chain), the CZ chain is the **last** operation and does not depend on the data. It is the same unitary C for every sample, so

    ⟨φ(z)|φ(x)⟩ = ⟨ψ(z)| C† C |ψ(x)⟩ = ⟨ψ(z)|ψ(x)⟩,

where |ψ⟩ is the product state before the entangler. So **for L = 1 the kernel is exactly a product of single-qubit fidelities**:

    K(x, z) = k₀(x, z)^⌈q/2⌉ · k₁(x, z)^⌊q/2⌋,   k_f = |⟨ψ₁(z_f)|ψ₁(x_f)⟩|²,

with feature f on qubits f, f + 2, …. The entangling gate never affects the kernel, including the 2-qubit kernel used in every earlier study. My approved plan said the chain "doesn't cancel in the overlap"; that was wrong, and this doc supersedes it. For L ≥ 2 the CZ chains sit between data-dependent layers and do not cancel.

This also explains an unexplained number from [kernel-rank-prediction.md](kernel-rank-prediction.md). At q = 3, K = k₀² · k₁. A single-qubit fidelity is Tr(ρρ′) with ρ = (I + n·σ)/2 and |n| = 1. k₀² is an inner product of ρ ⊗ ρ, which lives in a space of dimension 10 (symmetric 4 × 4 in the vector (1, n)). The pure-state constraint |n|² = 1 removes one dimension, leaving 9. k₁ has rank ≤ 4. So rank ≤ 9 × 4 = **36**, which is exactly the rank observed at q = 3, n = 40.

## Design

- Data: `make_subset_features(40, 0)` (40 points, 780 off-diagonal pairs); exact statevectors, no sampling.
- Maps: `layered_feature_map(values, q, layers=L, alpha=α)`. Each layer applies H, RZ(αx), RY((αx)²) on every qubit (features assigned cyclically, qubit i ← feature i mod 2), then a CZ chain. L = 1, α = 1 must equal the existing `feature_map_q` (tested).
- Grid: q = 1…8; L ∈ {1, 2, 4}; α ∈ {0.1, 0.3, 1}.
- Measured over the off-diagonal K: mean, variance and median m.
- **Shots to resolve** (the requested metric): the sampling SD at the median, √(m(1 − m)/shots), falls below the spread SD(K) when shots > m(1 − m)/Var(K).
- **Secondary, relative resolution:** shots > (1 − m)/m, i.e. the SD at the median is below m itself. I add this because for skewed K distributions the median can collapse toward 0, which makes the first metric small even while typical values become unresolvable.
- Plot: log Var(K) vs q, one line per (L, α).

## Predictions

- **C-P1 (exact identity).** For L = 1 and every α, the kernel equals k₀^⌈q/2⌉ k₁^⌊q/2⌋ to 1e-12 for all q. For L = 2 it does not.
- **C-P2 (existing map, L = 1, α = 1): it concentrates anyway, with only two features.** Two features limit the *rank*, not the concentration. Each extra qubit multiplies K by another factor k_f ≤ 1. Mean K falls monotonically in q. Var(K) falls from 0.05–0.12 at q = 1 to 0.005–0.03 at q = 8. It does not collapse all the way, because close pairs keep K near 1. The median falls much faster than the mean (a product of factors becomes very skewed), so the requested shots-to-resolve metric stays **below 100** for all q, while the relative-resolution shots **grow by ≥ 100×** from q = 1 to q = 8.
- **C-P3 (deeper, L = 2 and 4, α = 1).** Interleaved CZ chains make states more scrambled, so concentration is faster and closer to Haar. For L = 4: Var(K) at q = 8 < 1e-3, and a log Var slope over q = 4…8 between −1.0 and −1.6 per qubit (Haar gives −ln 4 ≈ −1.39). Shots-to-resolve at q = 8 is ≥ 100 (Haar-like scaling gives 2^q = 256). L = 2 lies between L = 1 and L = 4 on Var(K) at q = 8.
- **C-P4 (bandwidth α).** At α = 0.1 every state stays near a fixed state, so mean K ≥ 0.9 at q = 8 for every L, and Var(K) does **not** decrease with q (Var at q = 8 ≥ Var at q = 1). This mitigation works in the sense of no exponential decay. α = 0.3 lies between α = 0.1 and α = 1 in mean K at q = 8 for every L.
- **C-P5 (threshold).** No configuration needs more than 10⁴ shots (requested metric) at q ≤ 8. The largest should be L = 4, α = 1, at about 10²–10³.
