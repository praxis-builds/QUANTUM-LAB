"""Run independent analytical validation for the local Bell Kraus sweep."""

from praxis_quantum_lab.density_matrix_noise import (
    run_analytical_bell_noise_validation,
    write_analytical_validation_artifacts,
)


if __name__ == "__main__":
    report = run_analytical_bell_noise_validation()
    json_path, plot_path = write_analytical_validation_artifacts(report)
    errors = [
        case["analytical_to_aer_frobenius_error"]
        for channel in report["channels"].values()
        for case in channel["cases"]
    ]
    print("Analytical Bell-noise validation completed locally.")
    print(f"Maximum analytical-versus-Aer Frobenius error: {max(errors):.3e}")
    print(f"Saved {json_path} and {plot_path}.")
