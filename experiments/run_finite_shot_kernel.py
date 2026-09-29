"""Run the fixed-split finite-shot compute-uncompute kernel study."""

from __future__ import annotations

import argparse

from praxis_quantum_lab.finite_shot_kernel import (
    DEFAULT_SAMPLE_SIZE,
    DEFAULT_SEED,
    DEFAULT_SHOT_BUDGETS,
    DEFAULT_SHOT_SEEDS,
    run_finite_shot_kernel_experiment,
    write_finite_shot_result,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--shot-budgets", type=int, nargs="+", default=list(DEFAULT_SHOT_BUDGETS))
    parser.add_argument("--shot-seeds", type=int, nargs="+", default=list(DEFAULT_SHOT_SEEDS))
    arguments = parser.parse_args()

    report = run_finite_shot_kernel_experiment(
        sample_size=arguments.sample_size,
        seed=arguments.seed,
        shot_budgets=tuple(arguments.shot_budgets),
        shot_seeds=tuple(arguments.shot_seeds),
    )
    path = write_finite_shot_result(report)
    print("Finite-shot local Aer kernel study completed.")
    print(
        "Exact-kernel accuracy/F1: "
        f"{report['baselines']['exact_quantum_kernel_svc']['accuracy']:.3f} / "
        f"{report['baselines']['exact_quantum_kernel_svc']['f1']:.3f}"
    )
    print(
        "Classical RBF accuracy/F1: "
        f"{report['baselines']['classical_rbf_svc']['accuracy']:.3f} / "
        f"{report['baselines']['classical_rbf_svc']['f1']:.3f}"
    )
    for budget in report["shot_budgets"]:
        summary = budget["summary"]
        training = summary["kernel_error_mean_by_scope"]["training_unique_off_diagonal"]
        metrics = summary["classifier"]
        minimum_eigenvalue = summary["minimum_training_eigenvalue"]["mean"]
        psd_count = summary["positive_semidefinite_replicates_within_tolerance"]
        replicate_count = summary["replicate_count"]
        runtime = summary["timing_seconds_median"]["kernel_circuit_execution_seconds"]
        print(
            f"{budget['shots']} shots ({replicate_count} seeds): "
            f"training kernel MAE/RMSE {training['mae']:.4f}/{training['rmse']:.4f}; "
            f"accuracy/F1 {metrics['accuracy']['mean']:.3f}/{metrics['f1']['mean']:.3f}; "
            f"mean min eigenvalue {minimum_eigenvalue:.4g}; PSD {psd_count}/{replicate_count}; "
            f"median kernel execution {runtime:.3f}s"
        )
    print(f"Saved {path}.")


if __name__ == "__main__":
    main()
