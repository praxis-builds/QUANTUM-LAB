# Lesson 12: phase estimation

## The idea
Some states pass through a gate U unchanged except for a phase: U|ψ⟩ = e^{2πiφ}|ψ⟩. Such a state is an **eigenstate** of U, and φ (a number between 0 and 1, in turns) is its **eigenphase**, the gate's hidden "rotation amount". The T gate, for example, multiplies |1⟩ by e^{2πi/8}, so φ = 1/8.

**Phase estimation (QPE)** measures φ. Put t **counting qubits** in |+⟩. Counting qubit k controls U applied 2^k times. By phase kickback (Lesson 07) the eigenstate stays put and qubit k picks up the phase 2^k·φ. Those t phases are exactly the pattern the QFT makes from the integer m = φ·2ᵗ, so the inverse QFT (Lesson 11) turns them into m, and a measurement reads φ in binary. If φ needs more than t binary digits, you get a spread of nearby estimates.

## Predict first
1. T on |1⟩ with 3 counting qubits: what bit string do you measure, and how often?
2. φ = 1/3 is 0.010101… in binary and never ends. With 3 counting qubits, which estimate is most likely, and roughly how likely?
3. Going from 2 to 3, 4 and 5 counting qubits, does the probability of getting the single nearest estimate go up?

## How to run

    .venv/bin/python lessons/12_phase_estimation.py

It prints five labelled steps and saves `lessons/out/12_phase_estimation.png`. The counting qubits are 0 … t−1 (Qiskit order, qubit 0 on the right), and the eigenstate |1⟩ sits on qubit t.

## What you should see, and why
Answers are below.

## Spoiler
1. "001" in 2,000 of 2,000 shots (exact probability 1.000000), which means m = 1 and φ = 1/8. Before the inverse QFT the three counting qubits hold 0.125, 0.250 and 0.500 turns, which is 1/8 shifted 0, 1 and 2 binary places. S (φ = 1/4) likewise gives "010" every time.
2. 3/8 = 0.375 ("011"), with probability 0.688; Aer gave 1,406 of 2,000. The next is 2/8 ("010") at 0.175. The rest spreads thinly over the other outcomes.
3. **No.** It is natural to expect more qubits to make the nearest estimate more likely (this lab's own plan predicted it), but they don't. The exact probabilities are 0.700, 0.688, 0.685 and 0.684 for t = 2, 3, 4, 5: slightly *down*, toward sin²(π/3)/(π/3)² ≈ 0.684. That limit depends only on how far φ·2ᵗ lies from the nearest integer, which is always 1/3 for φ = 1/3. It never falls below the textbook bound 4/π² ≈ 0.405. More qubits improve **accuracy**, not certainty: the nearest estimate's error halves each time (0.083, 0.042, 0.021, 0.010), and the chance of landing within 0.05 of 1/3 rises from 0 to 0.688, 0.857 and 0.898. The plot shows both curves.

**Classical baseline.** If you can write U down as a matrix, `np.linalg.eigvals` gives the phases directly (0 and 1/3 here). QPE is useful only when U is a circuit too large to write as a matrix. Even then it has a cost: digit k needs U applied 2^k times, 2ᵗ − 1 in all, unless U^(2^k) has a shortcut.

**The bridge to Shor (program step 4).** Shor's algorithm is phase estimation applied to U: |y⟩ → |a·y mod N⟩. Its eigenphases are s/r, where r is the period of aˣ mod N: the hidden-period idea of Simon (Lesson 10), with an integer period instead of an XOR one. Modular multiplication has the shortcut: U^(2^k) is multiplication by a^(2^k) mod N, which is cheap to compute classically. A continued-fraction step turns the estimate into r, and r usually gives a factor of N. That is the threat to RSA.

**What this does NOT show.** The unitaries here are single-qubit phase gates whose phases we chose, so the "hidden" phase was never hidden. Nothing here factors a number or breaks RSA, and there is no speed-up claim: for these sizes the classical eigenvalue routine is exact and immediate.
