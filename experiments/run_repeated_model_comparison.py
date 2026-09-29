"""Run the 50-split paired comparison of exact, finite-shot, repaired and RBF kernels."""

from __future__ import annotations

import json
from pathlib import Path

from praxis_quantum_lab.repeated_model_comparison import PLOT_FILENAME, RESULT_FILENAME, write_artifacts


def main() -> None:
    results_dir = Path(__file__).resolve().parents[1] / "results"
    report = write_artifacts(results_dir)
    print(f"Wrote {results_dir / RESULT_FILENAME} and {results_dir / PLOT_FILENAME}")
    print(json.dumps(report["summary"], indent=1))


if __name__ == "__main__":
    main()
