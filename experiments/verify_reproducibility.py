"""Fail clearly if repeated same-seed kernel experiments diverge."""

from praxis_quantum_lab.kernel_experiment import verify_reproducibility


if __name__ == "__main__":
    is_reproducible = verify_reproducibility()
    print(f"Same-seed non-timing results identical: {is_reproducible}")
    raise SystemExit(0 if is_reproducible else 1)
