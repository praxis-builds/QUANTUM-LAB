"""Findings and scan results."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field

from .algorithms import SEVERITY, classify

_SECRETISH = re.compile(r"[A-Za-z0-9+/=_-]{40,}")
MAX_EVIDENCE = 160


def redact(line: str) -> str:
    """Evidence for a report: trimmed, with long base64/hex-like runs (possible key material) removed."""
    text = _SECRETISH.sub("[redacted]", line.strip())
    return text if len(text) <= MAX_EVIDENCE else text[: MAX_EVIDENCE - 3] + "..."


@dataclass
class Finding:
    file: str  # path relative to the scan root, with forward slashes
    line: int | None
    category: str  # source | certificate | public-key | private-key | ssh-key | ssh-config | tls-config | config
    algorithm: str
    risk: str
    why: str
    replacement: str
    rule: str
    detail: str = ""
    key_size: int | None = None
    heuristic: bool = False
    evidence: str = ""
    occurrence: int = 0  # 0, 1, 2 ... for identical findings in the same file (set by the scanner)

    @classmethod
    def make(cls, *, file: str, line: int | None, category: str, algorithm: str, rule: str, detail: str = "",
             key_size: int | None = None, heuristic: bool = False, evidence: str = "", risk: str | None = None) -> "Finding":
        auto_risk, why, replacement = classify(algorithm, key_size)
        return cls(file=file, line=line, category=category, algorithm=algorithm, risk=risk or auto_risk, why=why,
                   replacement=replacement, rule=rule, detail=detail, key_size=key_size, heuristic=heuristic,
                   evidence=redact(evidence) if evidence else "")

    def fingerprint(self) -> str:
        """Stable identity across scans. Ignores line numbers (they shift when other lines are edited);
        uses the redacted line text, plus an occurrence counter for identical repeats."""
        basis = "|".join([self.file, self.rule, self.algorithm, str(self.key_size), self.detail, self.evidence,
                          str(self.occurrence)])
        return hashlib.sha256(basis.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {**asdict(self), "fingerprint": self.fingerprint(), "severity": SEVERITY[self.risk]}


@dataclass
class ScanResult:
    root: str
    findings: list[Finding] = field(default_factory=list)
    files_scanned: int = 0
    skipped: list[dict] = field(default_factory=list)  # {"file": ..., "reason": ...}
    notes: list[str] = field(default_factory=list)
