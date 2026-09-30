# Lesson 11: the quantum Fourier transform

## The idea
A classical **DFT** (discrete Fourier transform; the FFT is a fast way to compute it) takes a signal and finds its frequencies: a list that repeats every r steps becomes a few sharp peaks. The **quantum Fourier transform (QFT)** does the same to the 2ⁿ amplitudes of n qubits. Put equal amplitude on every 2nd basis state of 8, apply the QFT, and all the probability lands on 2 states (0 and 4).

The circuit has only H gates, **controlled-phase** gates (CP(θ): multiply the |11⟩ part by e^{iθ}; CP(π) is CZ) and swaps: about n²/2 gates for n qubits. Its inverse undoes it exactly. The QFT is the step that turns a hidden period into something measurable. Phase estimation (Lesson 12) and Shor's algorithm (program step 4) are built on it.

## Predict first
1. numpy's `np.fft.fft` computes a DFT. Is the 3-qubit QFT matrix equal to `np.fft.fft(np.eye(8), axis=0, norm="ortho")`? If not, what differs?
2. After the QFT, where are the peaks for a period-2 input (states 0, 2, 4, 6)? For a period-4 input (0, 4)? What changes if the period-2 pattern is shifted to 1, 3, 5, 7?
3. What happens to the state if you apply the QFT and then its inverse?

## How to run

    .venv/bin/python lessons/11_qft.py

It prints six labelled steps (including the circuit drawing) and saves `lessons/out/11_qft_peaks.png`. Basis states are Qiskit integers: |100⟩ is 4 (qubit 0 is the rightmost bit).

## What you should see, and why
Answers are below.

## Spoiler
1. **No, and this is the classic trap.** Three conventions have to line up:
   - **Sign.** The QFT is |j⟩ → (1/√N) Σₖ e^{**+**2πi jk/N} |k⟩. numpy's `fft` uses e^{**−**2πi jk/N}, so the QFT matrix is `np.fft.ifft(..., norm="ortho")`, which is √N · `ifft`, not `fft`. The script finds a gap of 0.707 against `fft(norm="ortho")` and 1.2 × 10⁻¹⁶ against its complex conjugate.
   - **Normalisation.** numpy's `fft` has no 1/√N; the QFT must have it to be unitary.
   - **Qubit order.** Without the final SWAP the output bits come out reversed: the circuit then differs from the DFT by 0.707 but matches the bit-reversed DFT to 10⁻¹⁶. Textbooks often write |q₀q₁q₂⟩ with q₀ on the left, while Qiskit puts q₀ on the right. With the index taken as Qiskit's integer, our circuit matches both the DFT and Qiskit's own `QFTGate` (gap 1.4 × 10⁻¹⁵).
   (For n = 1 the matrix is real, so `fft` and the QFT happen to agree; the trap only appears from 2 qubits.)
2. Period 2 → peaks at |000⟩ and |100⟩ (0 and 4), amplitude 0.707 each. Period 4 → peaks at 0, 2, 4 and 6, amplitude 0.5 each. The rule: period r over N = 8 gives peaks at multiples of N/r. The shifted input has the **same** peaks; only the sign of |100⟩ changes (+0.707 to −0.707), which a measurement cannot see. On Aer the period-2 case gave 991 × "000" and 1009 × "100" out of 2,000.
3. You get the input back: the largest error is 3 × 10⁻¹⁶, and QFT⁻¹·QFT differs from the identity by 7 × 10⁻¹⁶ (floating-point rounding).

**Classical baseline.** `np.fft.fft` of the same 8 numbers gives the same peaks (power 0.5 at 0 and 4) in O(N log N) arithmetic steps. The QFT needs O(n²) gates for N = 2ⁿ, but that compares two different tasks (see below).

**What this does NOT show.** The QFT is **not** a faster FFT for your data. To use it on a real signal you would first have to load 2ⁿ numbers into amplitudes, which in general takes about 2ⁿ operations. Afterwards each shot returns one peak index, not the spectrum, and estimating the amplitudes takes many shots. Those two steps remove the gain. The QFT is useful only inside algorithms where the periodic state is produced by the computation itself, as in Shor. Nothing here is a speed-up claim.
