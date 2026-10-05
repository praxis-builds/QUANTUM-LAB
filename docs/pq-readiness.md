# pq_readiness: Quantum Readiness Report

One command turns a code scan and a set of website checks into a report a manager can read and a
consultant can hand over: one self-contained HTML page (print it to PDF from any browser) plus the
same data as JSON.

    python -m pq_readiness report --client "Name" [--code <path>] \
        [--sites a.com b.com | --sites-json results.json] [--sites-note "..."] \
        [--systems systems.json] --out <dir> [--date YYYY-MM-DD]

- `--code` scans a directory or file with [`pq_inventory`](pq-inventory.md) (read-only, offline).
- `--sites` checks websites now with [`pq_tls`](pq-tls.md) (at most 20, single hosts, browser-equivalent
  traffic). `--sites-json` reuses a recorded `pq_tls ... --json` file instead, with no network.
- `--systems` groups the findings into systems with Mosca's x and y (format in
  [`pq-inventory.md`](pq-inventory.md)); without it the whole tree is one system with the default assumptions.
- `--date` fixes the report date. It is the only clock the report uses, so the same inputs and date
  always give the same bytes.

Exit codes: `0` written; `2` usage or input error (missing path, empty client name, an unreadable or
malformed results file, more than 20 sites, a range instead of a host).

## Sections

1. **Executive summary** in plain language: websites with and without hybrid key exchange, findings
   by risk, which systems are already late under the Mosca assumption, the first thing to do.
2. **Websites: key exchange**: PQ-HYBRID / CLASSICAL / UNKNOWN, TLS version, certificate key, one
   recommendation each, with the date and source of the check.
3. **Code and configuration findings** by risk class, with the recommended replacement for each.
4. **Migration timeline (Mosca)**: a chart of x + y per system against z, the table, and every
   assumption written out.
5. **Prioritised actions**: now (weak today, or already late), next (quantum exposure with time
   left, websites without hybrid key exchange), later (certificates, Grover-only items).
6. **Methodology and honest limits**, then the date and tool versions.

## Guarantees

- **No key material and no source text.** The report carries only what pq_inventory reports:
  file, line, algorithm, risk, a description and a replacement. The scanner never stores matched
  text (DECISIONS D18), and the report drops even the `[redacted]` marker. A test plants keys and
  passwords and checks both outputs.
- **Everything is escaped.** Client name, host names, file names, certificate subjects and notes go
  through HTML escaping. A test feeds hostile values through every input.
- **Self-contained.** No scripts and no external assets. The print stylesheet sets A4 margins,
  starts the findings and the methodology on a new page, and drops colour backgrounds.
- **Deterministic.** Same inputs and `--date`, same bytes (tested).

## Example

[`examples/readiness-demo/`](../examples/readiness-demo/README.md) is the report for the fictional
Northwind Warehouse: its code before the first migration wave, its systems file, and the recorded
website results from [`examples/pq-tls/`](../examples/pq-tls/README.md). Northwind is fictional, so
those four websites are real public sites used as stand-ins, and the report says so. It is
generated with no network and is published on the project site.

**Not verified:** the printed PDF itself. No browser could run in this environment, so the print
layout has been checked by reading the stylesheet, not by printing.
