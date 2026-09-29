"""Compare exact, raw, clipped, Higham and RBF kernels with metrics beyond accuracy."""

from __future__ import annotations

from pathlib import Path

from praxis_quantum_lab.repair_metrics import PLOT_FILENAME, RESULT_FILENAME, write_artifacts


def main() -> None:
    results_dir = Path(__file__).resolve().parents[1] / "results"
    report = write_artifacts(results_dir)
    print(f"Wrote {results_dir / RESULT_FILENAME} and {results_dir / PLOT_FILENAME}")
    rbf = report["references"]["rbf"]
    print("RBF: alignment %.4f r %.3f sign %d/12 acc %.3f" % (rbf["alignment_to_exact_train"], rbf["pearson_r"], rbf["sign_agreement"], rbf["accuracy"]))
    for entry in report["summary"]:
        print(entry)


if __name__ == "__main__":
    main()
