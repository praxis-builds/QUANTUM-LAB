"""Run the kernel-rank versus PSD-violation sweep and write results/ artifacts."""

from __future__ import annotations

from pathlib import Path

from praxis_quantum_lab.kernel_spectrum import PLOT_FILENAME, RESULT_FILENAME, write_artifacts


def main() -> None:
    results_dir = Path(__file__).resolve().parents[1] / "results"
    report = write_artifacts(results_dir)
    check = report["aer_versus_binomial_q2_n40"]
    print(f"Wrote {results_dir / RESULT_FILENAME} and {results_dir / PLOT_FILENAME}")
    print(f"Aer vs binomial (q=2, n=40): {check}")


if __name__ == "__main__":
    main()
