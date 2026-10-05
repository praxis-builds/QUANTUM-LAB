# pq_tls sample results (recorded, not live)

`sample-results.json` is one run of

    python -m pq_tls check google.com cloudflare.com praxis-builds.github.io github.com --json sample-results.json

recorded on **2026-10-05** with pq_tls 0.1.0 (ML-KEM key from `cryptography` 50.0.2). It is a
snapshot from one machine: servers change their configuration, and a CDN can answer differently by
region. Re-run the command for current results.

What it showed on that day: google.com, cloudflare.com and praxis-builds.github.io chose
X25519MLKEM768 (hybrid post-quantum); github.com chose x25519 (classical). All four use TLS 1.3, and
all four certificates use quantum-vulnerable keys (ECDSA P-256 or RSA 2048), like every web
certificate today. The readiness-report demo (`examples/readiness-demo/`) reuses this file instead
of contacting the network.
