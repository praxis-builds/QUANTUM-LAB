"""Run the exact kernel-concentration sweep (q = 1..8, layers, bandwidth)."""

from __future__ import annotations

from pathlib import Path

from praxis_quantum_lab.kernel_concentration import PLOT_FILENAME, RESULT_FILENAME, write_artifacts


def main() -> None:
    results_dir = Path(__file__).resolve().parents[1] / "results"
    report = write_artifacts(results_dir)
    print(f"Wrote {results_dir / RESULT_FILENAME} and {results_dir / PLOT_FILENAME}")
    for row in report["rows"]:
        print(
            "L=%d a=%.1f q=%d mean %.4f var %.2e median %.4f shots_spread %.1f shots_rel %.3g%s"
            % (row["layers"], row["alpha"], row["qubits"], row["mean"], row["variance"], row["median"],
               row["shots_to_resolve_spread"], row["shots_relative_resolution_at_median"],
               f" prod_err {row['product_formula_max_abs_error']:.1e}" if "product_formula_max_abs_error" in row else ""),
        )


if __name__ == "__main__":
    main()
