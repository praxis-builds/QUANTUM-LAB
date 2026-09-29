"""Save the clipping-step diagnostic (projection only vs projection + rescale)."""

from __future__ import annotations

from pathlib import Path

from praxis_quantum_lab.repair_comparison import CLIPPING_STEP_RESULT_FILENAME, write_clipping_step_diagnostic


def main() -> None:
    results_dir = Path(__file__).resolve().parents[1] / "results"
    report = write_clipping_step_diagnostic(results_dir)
    print(f"Wrote {results_dir / CLIPPING_STEP_RESULT_FILENAME}")
    for row in report["rows"]:
        print(
            row["shots"], row["replicate"],
            "raw %.3f proj %.3f proj+rescale %.3f diag %.3f offdiag exact/raw/clip %.3f/%.3f/%.3f"
            % (row["raw_to_exact"], row["projection_only_to_exact"], row["projection_plus_rescale_to_exact"],
               row["projection_mean_diagonal"], row["exact_mean_offdiagonal"], row["raw_mean_offdiagonal"], row["clipped_mean_offdiagonal"]),
        )


if __name__ == "__main__":
    main()
