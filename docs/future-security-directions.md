# Future security directions — not implemented in Lab 01

This classification lab is not a cryptography project. Its immediate value is learning linear algebra, circuits, simulation, noise, and honest experimental comparison. Those foundations can later inform security research without forcing a security story into the first experiment.

## Post-quantum cryptography

Future study can compare the threat model behind Shor’s algorithm with the assumptions used by classical public-key systems, then learn why standardized post-quantum schemes use different hard problems. A later lab could model protocol choices and migration constraints, but should use established test vectors and specifications rather than inventing cryptography.

## Threats to current public-key systems

Large fault-tolerant quantum computers could threaten widely deployed RSA and elliptic-curve systems. The relevant practical question is not whether this small simulator can break encryption—it cannot—but which long-lived data may need protection before capable machines exist (“harvest now, decrypt later”).

## Hybrid quantum-classical security research

Potential research topics include evaluating quantum-inspired optimization claims, studying the reliability of quantum-generated features for security telemetry, and designing experiments that compare them against strong classical baselines. Any future security classifier must address data leakage, adversarial robustness, calibration, and operational false-positive costs.

## Quantum-safe migration planning

Useful future work is inventory and governance work: locate cryptographic dependencies, record algorithms and key lifetimes, identify upgrade paths, test interoperability, and plan staged adoption of approved post-quantum or hybrid mechanisms. This repository intentionally implements none of those cryptographic operations yet.
