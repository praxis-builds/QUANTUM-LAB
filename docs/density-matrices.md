# Density matrices and local Kraus noise

## Why use a density matrix?

A pure state `|ψ⟩` can be written as a density matrix:

```text
ρ = |ψ⟩⟨ψ|.
```

Density matrices also describe probabilistic mixtures, which are needed after
noise. A physically valid finite density matrix is Hermitian, has trace one,
and has no negative eigenvalue beyond numerical round-off.

The module applies a quantum channel written with Kraus operators:

```text
ρ′ = Σᵢ KᵢρKᵢ†.
```

The completeness condition

```text
Σᵢ Kᵢ†Kᵢ = I
```

means that the channel preserves total probability (the trace of `ρ`) for
every input state. `density_matrices.py` validates this condition before a
channel is applied.

## Ordering convention

The implementation deliberately follows Qiskit’s little-endian convention. On
two qubits, vector and matrix indices are displayed as `|q1 q0⟩`: qubit 0 is
the rightmost, least-significant bit. Therefore a Pauli-X operation on qubit 0
maps `|00⟩` to `|01⟩`, while X on qubit 1 maps `|00⟩` to `|10⟩`.

The Bell sweep applies every local channel to **qubit 0 only**. The custom
embedding is built by bit position, not by an implicit tensor-product order,
then tested against Aer using that same target qubit.

## Channel parameter conventions

All strengths lie in `[0, 1]`.

- Bit flip: `p` is the probability in `E(ρ) = (1-p)ρ + pXρX`.
- Amplitude damping: `γ` is the probability that `|1⟩` decays to `|0⟩`.
- Depolarizing: `p` means `E(ρ) = (1-p)ρ + pI/2` for the targeted qubit.
  This is explicitly this lab’s replacement-with-maximally-mixed-state
  convention; it is not assumed to be the same named parameter used by every
  simulator API.

The Aer circuit receives a `Kraus` instruction constructed from exactly these
matrices. The comparison is consequently between two local implementations of
the same channel, not a comparison with hardware calibration data.

## Run it

```bash
.venv/bin/python experiments/run_density_matrix_noise_sweep.py
```

The runner refuses to overwrite existing artifacts. It writes
`results/density_matrix_bell_noise_sweep.json` and a matching probability plot.
For each channel and strength the JSON stores the custom and Aer density
matrices as `[real, imag]` pairs, computational-basis probabilities, Kraus
completeness error, and `||ρ_custom - ρ_Aer||_F`.

The stated `1e-10` comparison tolerance is far larger than expected
double-precision round-off but still small enough to expose an ordering or
channel-definition error.

## What this demonstrates—and what it does not

It demonstrates trace-preserving Kraus evolution, the difference between pure
and mixed states, correct local-qubit ordering, and agreement with an exact
local density-matrix simulator. It does not estimate a real device’s noise,
perform error mitigation, or establish a hardware capability.

For the independent derivation of this sweep’s probabilities and Bell fidelity,
see [analytical Bell-noise validation](bell-noise-analytical-validation.md).
