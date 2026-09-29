"""Run the paired repeated-split local kernel comparison without overwriting results."""

from __future__ import annotations

import argparse

from praxis_quantum_lab.kernel_experiment import (
    DEFAULT_DATASET_SIZE,
    DEFAULT_REPEATED_SPLITS,
    DEFAULT_REPEATS,
    DEFAULT_SEED,
    DEFAULT_TIMING_REPETITIONS,
    run_repeated_classification_experiment,
    write_repeated_experiment_artifact,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-size", type=int, default=DEFAULT_DATASET_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--n-splits", type=int, default=DEFAULT_REPEATED_SPLITS)
    parser.add_argument("--n-repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument(
        "--timing-repetitions", type=int, default=DEFAULT_TIMING_REPETITIONS
    )
    arguments = parser.parse_args()
    report = run_repeated_classification_experiment(
        dataset_size=arguments.dataset_size,
        seed=arguments.seed,
        n_splits=arguments.n_splits,
        n_repeats=arguments.n_repeats,
        timing_repetitions=arguments.timing_repetitions,
    )
    path = write_repeated_experiment_artifact(report)
    aggregate = report["aggregate"]
    classical = aggregate["classical_rbf_svc"]["metrics"]["accuracy"]
    quantum = aggregate["quantum_kernel_svc"]["metrics"]["accuracy"]
    difference = aggregate["paired_accuracy_difference_quantum_minus_classical"]
    print("Repeated local classical-versus-quantum-kernel comparison completed.")
    print(
        "Classical accuracy mean/std: "
        f"{classical['mean']:.3f} / {classical['standard_deviation']:.3f}"
    )
    print(
        "Quantum-kernel accuracy mean/std: "
        f"{quantum['mean']:.3f} / {quantum['standard_deviation']:.3f}"
    )
    print(
        "Paired quantum-minus-classical accuracy mean/std: "
        f"{difference['mean']:.3f} / {difference['standard_deviation']:.3f}"
    )
    print(f"Saved {path}.")


if __name__ == "__main__":
    main()
