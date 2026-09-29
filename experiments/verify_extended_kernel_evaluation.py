"""Verify deterministic non-timing results for the expanded paired configuration."""

from praxis_quantum_lab.kernel_experiment import verify_extended_kernel_reproducibility


if __name__ == "__main__":
    reproducible = verify_extended_kernel_reproducibility()
    print(f"Expanded same-seed non-timing results identical: {reproducible}")
    raise SystemExit(0 if reproducible else 1)
