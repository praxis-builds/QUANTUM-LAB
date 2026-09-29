"""Run the configurable 5-fold x 10-repeat paired kernel evaluation."""

from __future__ import annotations

import argparse

from praxis_quantum_lab.kernel_experiment import (
    DEFAULT_DATASET_SIZE,
    DEFAULT_EXTENDED_REPEATS,
    DEFAULT_EXTENDED_SPLITS,
    DEFAULT_SEED,
    DEFAULT_TIMING_REPETITIONS,
    run_extended_kernel_evaluation,
    write_extended_kernel_evaluation_artifact,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-size", type=int, default=DEFAULT_DATASET_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--n-splits", type=int, default=DEFAULT_EXTENDED_SPLITS)
    parser.add_argument("--n-repeats", type=int, default=DEFAULT_EXTENDED_REPEATS)
    parser.add_argument("--timing-repetitions", type=int, default=DEFAULT_TIMING_REPETITIONS)
    arguments = parser.parse_args()
    report = run_extended_kernel_evaluation(
        dataset_size=arguments.dataset_size,
        seed=arguments.seed,
        n_splits=arguments.n_splits,
        n_repeats=arguments.n_repeats,
        timing_repetitions=arguments.timing_repetitions,
    )
    path = write_extended_kernel_evaluation_artifact(report)
    aggregate = report["aggregate"]
    classical = aggregate["classical_rbf_svc"]["metrics"]
    quantum = aggregate["quantum_kernel_svc"]["metrics"]
    difference = aggregate["paired_accuracy_difference_quantum_minus_classical"]
    print("Expanded paired local kernel evaluation completed.")
    print(
        "Classical accuracy mean/std/median/IQR: "
        f"{classical['accuracy']['mean']:.3f} / {classical['accuracy']['standard_deviation']:.3f} / "
        f"{classical['accuracy']['median']:.3f} / {classical['accuracy']['interquartile_range']:.3f}"
    )
    print(
        "Quantum accuracy mean/std/median/IQR: "
        f"{quantum['accuracy']['mean']:.3f} / {quantum['accuracy']['standard_deviation']:.3f} / "
        f"{quantum['accuracy']['median']:.3f} / {quantum['accuracy']['interquartile_range']:.3f}"
    )
    print(
        "Paired quantum-minus-classical accuracy mean/std/median/IQR: "
        f"{difference['mean']:.3f} / {difference['standard_deviation']:.3f} / "
        f"{difference['median']:.3f} / {difference['interquartile_range']:.3f}"
    )
    print(f"Saved {path}.")


if __name__ == "__main__":
    main()
