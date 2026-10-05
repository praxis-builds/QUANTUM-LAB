# Quantum Readiness Report: demo (fictional client)

`readiness-report.html` (open it, or print it to PDF from a browser) and `readiness-report.json`
are the report `pq_readiness` writes for the fictional Northwind Warehouse, generated offline from
committed inputs:

- code and configuration: `examples/warehouse-demo/before/` (the state before the first
  migration wave in [`docs/case-study.md`](../../docs/case-study.md));
- systems and Mosca assumptions: `examples/warehouse-demo/systems.json`;
- websites: `examples/pq-tls/sample-results.json`, a pq_tls run recorded on 2026-10-05. Northwind is
  fictional, so these are four real public websites used as stand-ins, and the report says so.

Regenerate from the repository root (no network is used):

    python -m pq_readiness report --client "Northwind Warehouse (fictional)" \
        --code examples/warehouse-demo/before --systems examples/warehouse-demo/systems.json \
        --sites-json examples/pq-tls/sample-results.json \
        --sites-note "Northwind is fictional, so these are four real public websites checked on 2026-10-05 as stand-ins, not Northwind's own." \
        --out examples/readiness-demo --date 2026-10-05

`tests/test_pq_readiness.py` fails if the committed files differ from what this command writes.
