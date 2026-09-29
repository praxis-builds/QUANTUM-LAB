"""Run the pre-registered out-of-sample test of the second-order negativity model."""

from __future__ import annotations

import json
from pathlib import Path

from praxis_quantum_lab.kernel_negativity import (
    OOS_PLOT_FILENAME,
    OOS_RESULT_FILENAME,
    write_out_of_sample_artifacts,
)


def main() -> None:
    results_dir = Path(__file__).resolve().parents[1] / "results"
    report = write_out_of_sample_artifacts(results_dir)
    print(f"Wrote {results_dir / OOS_RESULT_FILENAME} and {results_dir / OOS_PLOT_FILENAME}")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
