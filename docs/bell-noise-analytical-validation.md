# Analytical validation of Bell-state noise

This note derives the reference used by the separate analytical validation
runner. It uses the project’s actual conventions, not a simulator-specific
redefinition: the initial state is

```text
|Phi+> = (|00> + |11>)/sqrt(2)
```

and every channel acts on Qiskit qubit 0, the rightmost bit in `|q1 q0>`.
The pure-reference fidelity is therefore

```text
F(Phi+, rho) = <Phi+|rho|Phi+>.
```

## Bit flip

The implemented operators are `sqrt(1-p) I` and `sqrt(p) X`, so

```text
rho' = (1-p)|Phi+><Phi+| + p|Psi+><Psi+|,
|Psi+> = (|01> + |10>)/sqrt(2).
```

Thus `P(00)=P(11)=(1-p)/2`, `P(01)=P(10)=p/2`, and `F=1-p`. At `p=1`,
the state is the orthogonal Bell state `|Psi+>`.

## Amplitude damping

The actual operators are

```text
K0 = |0><0| + sqrt(1-gamma)|1><1|
K1 = sqrt(gamma)|0><1|.
```

For target qubit 0,

```text
K0|Phi+> = (|00> + sqrt(1-gamma)|11>)/sqrt(2)
K1|Phi+> = sqrt(gamma)|10>/sqrt(2).
```

Therefore `P(00)=1/2`, `P(01)=0`, `P(10)=gamma/2`, and
`P(11)=(1-gamma)/2`. The fidelity is
`F=(1+sqrt(1-gamma))²/4`. At full damping, the result is an equal mixture of
`|00>` and `|10>`, with Bell fidelity `1/4`. The `|10>` outcome follows from
the project’s little-endian qubit-0 convention.

## Depolarizing

This project defines `p` by `E(rho)=(1-p)rho+pI/2` on the targeted qubit. Its
Kraus weights are `I: 1-3p/4` and `X`, `Y`, `Z`: `p/4` each. The four Pauli
branches map `|Phi+>` to the four Bell-state density matrices, giving

```text
P(00)=P(11)=1/2-p/4
P(01)=P(10)=p/4
F=1-3p/4.
```

At `p=1`, all four measurement outcomes have probability `1/4`, while the
original Bell-state fidelity is `1/4`.

## What is validated

Run the separate local check:

```bash
.venv/bin/python experiments/run_analytical_bell_noise_validation.py
```

It compares the analytical density matrices, probabilities, and fidelities to
both the NumPy Kraus calculation and local Aer density-matrix simulation over
the existing six strengths. It writes new guarded artifacts:

- `results/density_matrix_bell_noise_analytical_validation.json`
- `results/density_matrix_bell_noise_analytical_fidelity.png`

Agreement validates the stated channel algebra, target-qubit ordering, and use
of the same Kraus matrices by the two implementations. It cannot validate a
physical device-noise model, calibration, gate duration, readout error, or
hardware error mitigation.
