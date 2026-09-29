"""Apply clipping and Higham repair to the saved raw finite-shot kernels."""

from __future__ import annotations

from pathlib import Path

from praxis_quantum_lab.repair_comparison import PLOT_FILENAME, RESULT_FILENAME, write_artifacts


def main() -> None:
    results_dir = Path(__file__).resolve().parents[1] / "results"
    report = write_artifacts(results_dir)
    print(f"Wrote {results_dir / RESULT_FILENAME} and {results_dir / PLOT_FILENAME}")
    for row in report["rows"]:
        print(
            row["shots"], row["replicate"],
            "raw->exact %.4f" % row["raw"]["distance_to_exact"],
            "clip: ->raw %.4f ->exact %.4f lmin %.1e" % (row["clipped"]["distance_to_raw"], row["clipped"]["distance_to_exact"], row["clipped"]["lambda_min"]),
            "higham: ->raw %.4f ->exact %.4f lmin %.1e it %d" % (row["higham"]["distance_to_raw"], row["higham"]["distance_to_exact"], row["higham"]["lambda_min"], row["higham"]["iterations"]),
        )


if __name__ == "__main__":
    main()
