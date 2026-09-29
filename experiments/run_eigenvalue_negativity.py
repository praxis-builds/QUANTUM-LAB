"""Run the per-eigenvalue negativity prediction sweep and write results/ artifacts."""

from __future__ import annotations

from pathlib import Path

from praxis_quantum_lab.kernel_negativity import PLOT_FILENAME, RESULT_FILENAME, write_artifacts


def main() -> None:
    results_dir = Path(__file__).resolve().parents[1] / "results"
    report = write_artifacts(results_dir)
    print(f"Wrote {results_dir / RESULT_FILENAME} and {results_dir / PLOT_FILENAME}")
    for row in report["by_bottom_spacing"]:
        print(row)


if __name__ == "__main__":
    main()
