# Completed studies

## Kernel/PSD study (2026-09-28 to 2026-09-29) — completed, frozen

A classical RBF SVC against a quantum fidelity-kernel SVC on one small data set, then what finite shots do to that kernel: indefinite (non-PSD) estimates, why they happen, how to predict them, and what clipping and Higham repairs change. Result in one line: RBF wins on accuracy; repairs move alignment and decision correlation, not accuracy. No quantum advantage was found or claimed.

**Status:** complete and frozen on 2026-09-30, when the lab's main path moved to quantum computing algorithms (see the program in the top-level `README.md`). Everything below is kept where it is, unchanged and still tested. It is not extended. The Kernel Observatory tab of the dashboard reads its saved results.

| Stage | Doc | Module(s) | Runner(s) in `experiments/` |
|---|---|---|---|
| Classical vs quantum kernel, one split | `docs/experiment-guide.md` | `kernel_experiment.py` | `run_classification.py`, `verify_reproducibility.py` |
| Repeated splits | `docs/repeated-kernel-comparison.md` | `kernel_experiment.py` | `run_repeated_classification.py`, `verify_repeated_classification.py` |
| Extended 5×10 evaluation | `docs/extended-kernel-evaluation.md` | `kernel_experiment.py` | `run_extended_kernel_evaluation.py`, `verify_extended_kernel_evaluation.py` |
| Finite-shot kernel | `docs/finite-shot-kernel.md` | `finite_shot_kernel.py` | `run_finite_shot_kernel.py` |
| PSD repair (transductive) | `docs/finite-shot-psd-repair.md` | `finite_shot_psd.py` | `run_finite_shot_psd_repair.py` |
| Kernel rank and PSD violation | `docs/kernel-rank-prediction.md` | `kernel_spectrum.py` | `run_kernel_rank_prediction.py` |
| Per-eigenvalue negativity | `docs/eigenvalue-negativity-prediction.md` | `kernel_negativity.py` | `run_eigenvalue_negativity.py` |
| Higham vs clipping | `docs/higham-vs-clipping.md` | `nearest_correlation.py`, `repair_comparison.py` | `run_higham_vs_clipping.py`, `run_clipping_step_diagnostic.py` |
| Metrics that separate models | `docs/repair-metric-comparison.md` | `repair_metrics.py` | `run_repair_metric_comparison.py` |
| Out-of-sample second-order test | `docs/second-order-negativity-test.md` | `kernel_negativity.py` | `run_second_order_negativity_test.py` |
| Repeated-split model comparison | `docs/repeated-model-comparison.md` | `repeated_model_comparison.py` | `run_repeated_model_comparison.py` |
| Kernel concentration | `docs/kernel-concentration.md` | `kernel_concentration.py` | `run_kernel_concentration.py` |
| Observatory view (read-only) | `docs/dashboard.md` | `observatory.py` | — |

Modules live in `src/praxis_quantum_lab/`, tests in `tests/test_<module>.py` (plus `test_repeated_kernel_experiment.py`), outputs in `results/` (the `classification_*`, `finite_shot_*`, `kernel_*`, `eigenvalue_*`, `higham_*`, `clipping_*`, `repair_*`, `repeated_model_*` and `second_order_*` files). The foundations material (state vectors, Qiskit examples, density matrices, Bell noise) is shared with the main path and is not part of this frozen study.

Rules that still apply if anyone reads or reuses it: raw pathologies (indefinite kernels) are reported unrepaired, and every repair changes the data.
