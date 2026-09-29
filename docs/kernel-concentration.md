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

---

# Results (added after running; everything above is unchanged)

Artifacts: `results/kernel_concentration.json`, `results/kernel_concentration_variance.png`. Runner: `experiments/run_kernel_concentration.py` (~9 s; rerun byte-identical). Exact statevectors, 40 points, 780 pairs; no sampling.

Selected rows (mean / Var / median of off-diagonal K; requested shots metric; relative-resolution shots):

| L, α | q = 1 | q = 4 | q = 8 | log-Var slope, q = 4…8 |
|---|---|---|---|---|
| 1, 1.0 (existing map) | 0.66 / 0.089 / 0.73; 2.2; 0.37 | 0.28 / 0.085 / 0.17; 1.6; 4.9 | 0.17 / 0.064 / 0.029; 0.4; 34 | −0.07 |
| 2, 1.0 | 0.52 / 0.105 / 0.49; 2.4; 1.0 | 0.11 / 0.037 / 0.037; 1.0; 26 | 0.047 / 0.023 / 0.0018; 0.1; 549 | −0.12 |
| 4, 1.0 | 0.60 / 0.075 / 0.60; 3.2; 0.66 | 0.12 / 0.023 / 0.068; 2.7; 14 | 0.029 / 0.0115 / 0.0040; 0.3; 250 | −0.18 |
| 1, 0.3 | 0.95 / 3.0e-3 / 0.97; 9.1 | 0.82 / 0.017 / 0.85; 7.7 | 0.70 / 0.042 / 0.72; 4.9 | rises |
| 1, 0.1 | 0.995 / 3.9e-5 / 0.997; 71 | 0.98 / 3.0e-4 / 0.98; 51 | 0.96 / 1.1e-3 / 0.97; 26 | rises |
| 4, 0.1 | 0.98 / 5.9e-4; 19 | 0.94 / 4.8e-3; 7.4 | 0.85 / 0.012; 10 | rises |

Haar reference: Var ≈ 4^−q, slope −1.39. The full table is in the JSON.

## Prediction vs observed

| # | Prediction | Observed | Verdict |
|---|---|---|---|
| C-P1 | L = 1 kernel = k₀^⌈q/2⌉ k₁^⌊q/2⌋ to 1e-12; not for L = 2 | max error ≤ 6.7e-15 for all q and α; L = 2 differs by > 1e-3 (tested) | Confirmed |
| C-P2 | L=1, α=1: mean falls; Var 0.05–0.12 → 0.005–0.03; requested shots < 100; relative shots grow ≥ 100× | mean 0.66 → 0.17 ✓; Var 0.089 → **0.064** ✗; shots 0.4–2.7 ✓; relative shots 0.37 → 34 = **91×** ✗ (just short) | **Mostly wrong on variance** |
| C-P3 | L=4, α=1: Var(q=8) < 1e-3; slope −1.0 to −1.6; requested shots ≥ 100 at q=8; L=2 between L=1 and L=4 | Var **0.0115**; slope **−0.18**; shots **0.3**; ordering L1 > L2 > L4 ✓ | **Wrong** except the ordering |
| C-P4 | α=0.1: mean ≥ 0.9 at q=8 for every L; Var does not decrease with q; α=0.3 in between | mean 0.96 / 0.93 / **0.85** (L=4 fails); Var rises 20–72× from q=1 to 8 ✓; α=0.3 in between ✓ | Mostly confirmed |
| C-P5 | no config above 10⁴ shots (requested metric); largest L=4, α=1 at 10²–10³ | max is **100** (L=1, α=0.1, q=2); L=4, α=1 needs 0.3–3.6 | First part ✓, second **wrong** |

## Explanation: no Haar-like concentration here, but the median collapses

1. **More qubits sharpen the same 2-feature kernel.** From C-P1, for even q, K_q = (K₂)^(q/2) exactly (checked: max |K₈ − K₂⁴| = 3.9e-15). The 8-qubit kernel of the existing map is literally the 2-qubit kernel to the fourth power. Raising to a power keeps pairs near K = 1 close to 1 and pushes the rest toward 0, like narrowing an RBF bandwidth. The variance over pairs is then set by the **distribution of pair distances in the 2-D data**: the fraction of close pairs stays high, so Var(K) cannot decay exponentially. My C-P2 estimate treated single-qubit fidelities as roughly independent and uniform, which ignores that a pair close in feature 0 is usually also close in feature 1.
2. **Depth doesn't produce Haar-like states from 2 inputs.** Exponential concentration theory needs the embedded data to look like a 2-design. With two input features, every state lies on a 2-D manifold in a 2^q-dimensional space, and nearby inputs still give nearby states (continuity). So deeper maps shrink the effective bandwidth faster (slope −0.18 vs −0.07), but Var(K) stays three orders of magnitude above 4^−q at q = 8. I predicted Haar-like decay without accounting for the input dimension. This lesson generalises: concentration rate depends on the **data dimension and distribution**, not just on q and depth.
3. **The requested metric falls with q, because the median collapses.** m(1 − m)/Var(K) shrinks as the median goes to 0 (0.73 → 0.029 → 0.0018 across the rows above). That makes the requested metric look easy. The practical problem shows up in the relative metric instead: at L = 2, α = 1, q = 8, resolving the median pair's value to within its own size needs **549 shots**, and most pairs are near 0 in a kernel close to the identity. That is the "bandwidth too narrow" failure, not Haar concentration.
4. **α works as a bandwidth knob in both directions.** α = 0.1 keeps K near 1, with Var rising with q (the kernel slowly widens its range). α = 0.3 lands in a middle range where the median stays near 0.5–0.7 at q = 8. Scaling features is a real mitigation for this map, but only because the problem is bandwidth, not Haar concentration.

## Next

- A proper concentration test needs input dimension to grow with q (for example, synthetic data with d = q features), so the data manifold is not stuck at 2-D.
- The relative metric (1 − m)/m should be checked against actual finite-shot estimates, together with the negativity model from the earlier docs.

Scope: exact simulation, one 40-point subset, one data family. No classifier was run here, and nothing in this study claims or refutes quantum advantage.
