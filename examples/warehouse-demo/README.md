# Warehouse demo (fictional, TEST ONLY)

A small, fictional warehouse/inventory application with typical legacy cryptography planted on purpose, used for the case study in [`docs/case-study.md`](../../docs/case-study.md). Nothing here runs or connects anywhere. All keys and certificates were generated for this demo by `generate_demo_keys.py`; **no private key is stored**.

- `before/`: the application as found (the "before" state).
- `after/`: the same application after the first migration wave.
- `systems.json`: the roadmap configuration (data lifetimes and migration times per system: assumptions for the case study).
- `reports/`: committed scanner output (HTML, Markdown, JSON, CBOM) and the before/after diff.

Regenerate the reports from the repository root:

    python -m pq_inventory scan examples/warehouse-demo/before --out examples/warehouse-demo/reports/before --systems examples/warehouse-demo/systems.json --timestamp 2026-10-01T09:00:00+00:00
    python -m pq_inventory scan examples/warehouse-demo/after  --out examples/warehouse-demo/reports/after  --systems examples/warehouse-demo/systems.json --timestamp 2026-10-01T09:00:00+00:00
    python -m pq_inventory diff examples/warehouse-demo/reports/before/scan.json examples/warehouse-demo/reports/after/scan.json --out examples/warehouse-demo/reports/diff
