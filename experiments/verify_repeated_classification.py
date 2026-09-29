"""Verify deterministic non-timing outcomes for repeated paired splits."""

from praxis_quantum_lab.kernel_experiment import verify_repeated_reproducibility


if __name__ == "__main__":
    reproducible = verify_repeated_reproducibility()
    print(f"Repeated same-seed non-timing results identical: {reproducible}")
    raise SystemExit(0 if reproducible else 1)
