"""Run the local full-subset finite-shot kernel PSD-repair comparison."""

from __future__ import annotations

import argparse

from praxis_quantum_lab.finite_shot_kernel import (
    DEFAULT_SAMPLE_SIZE,
    DEFAULT_SEED,
    DEFAULT_SHOT_BUDGETS,
    DEFAULT_SHOT_SEEDS,
)
from praxis_quantum_lab.finite_shot_psd import run_psd_repair_experiment, write_psd_repair_artifacts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--shot-budgets", type=int, nargs="+", default=list(DEFAULT_SHOT_BUDGETS))
    parser.add_argument("--shot-seeds", type=int, nargs="+", default=list(DEFAULT_SHOT_SEEDS))
    arguments = parser.parse_args()

    report = run_psd_repair_experiment(
        sample_size=arguments.sample_size,
        seed=arguments.seed,
        shot_budgets=tuple(arguments.shot_budgets),
        shot_seeds=tuple(arguments.shot_seeds),
    )
    json_path, plot_path = write_psd_repair_artifacts(report)
    print("Finite-shot kernel PSD-repair study completed on local Aer.")
    exact = report["baselines"]["exact_statevector_kernel_svc"]
    rbf = report["baselines"]["fixed_rbf_svc"]
    print(f"Exact kernel accuracy/F1: {exact['accuracy']:.3f} / {exact['f1']:.3f}")
    print(f"Fixed RBF accuracy/F1: {rbf['accuracy']:.3f} / {rbf['f1']:.3f}")
    for budget in report["shot_budgets"]:
        summary = budget["summary"]
        raw = summary["classifier_results"]["raw_finite_shot_kernel"]
        repaired = summary["classifier_results"]["psd_repaired_transductive_kernel"]
        print(
            f"{budget['shots']} shots: raw acc/F1 {raw['accuracy']['mean']:.3f}/"
            f"{raw['f1']['mean']:.3f}; repaired transductive acc/F1 "
            f"{repaired['accuracy']['mean']:.3f}/{repaired['f1']['mean']:.3f}; "
            f"minimum eigenvalue raw/repaired "
            f"{summary['raw_minimum_eigenvalue']['mean']:.4g}/"
            f"{summary['repaired_minimum_eigenvalue']['mean']:.4g}; "
            f"PSD raw/repaired "
            f"{summary['raw_psd_replicates_within_tolerance']}/"
            f"{summary['repaired_psd_replicates_within_tolerance']}/"
            f"{summary['replicate_count']}"
        )
    print(f"Saved {json_path} and {plot_path}.")


if __name__ == "__main__":
    main()
