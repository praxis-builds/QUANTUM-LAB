"""pq_inventory: a read-only cryptography inventory scanner for post-quantum migration planning.

It finds quantum-vulnerable and classically weak cryptography in source code, keys, certificates,
SSH and TLS configuration, classifies each finding, recommends a NIST replacement, and writes
JSON, HTML, Markdown and CycloneDX CBOM reports. It never uses the network and never writes
outside the chosen output directory.
"""

__version__ = "0.1.0"
