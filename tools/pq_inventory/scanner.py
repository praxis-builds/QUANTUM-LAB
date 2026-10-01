"""Run every detector over a tree and collect a ScanResult (read-only)."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from . import __version__, detect_configs, detect_keys, detect_source
from .algorithms import RISK_ORDER
from .model import Finding, ScanResult
from .walker import DEFAULT_MAX_BYTES, DEFAULT_MAX_FILES, walk


def _is_ssh_config(relative: str) -> bool:
    name = relative.rsplit("/", 1)[-1].lower()
    return "ssh" in name or "/.ssh/" in f"/{relative.lower()}"


def scan(root: Path, *, rules=None, max_bytes: int = DEFAULT_MAX_BYTES, max_files: int = DEFAULT_MAX_FILES,
         exclude: list[Path] | None = None) -> ScanResult:
    root = Path(root)
    rules = rules if rules is not None else detect_source.load_rules()
    result = ScanResult(root=str(root))
    excluded = [Path(p).resolve() for p in exclude or []]
    if not detect_keys.HAVE_CRYPTOGRAPHY:
        result.notes.append("the 'cryptography' package is not installed: keys and certificates are classified from "
                            "PEM headers only (install the [pqc] extra for sizes, curves and certificate details)")
    seen: set[tuple] = set()
    for item in walk(root, max_bytes=max_bytes, max_files=max_files, skipped=result.skipped):
        if any(item.path.resolve().is_relative_to(path) for path in excluded):
            continue
        result.files_scanned += 1
        findings: list[Finding] = detect_keys.detect(item.relative, item.data, item.is_text)
        if item.is_text:
            text = item.data.decode("utf-8", errors="replace")
            findings += detect_source.detect(item.relative, text, rules)
            findings += detect_configs.detect_tls(item.relative, text)
            if _is_ssh_config(item.relative):
                findings += detect_configs.detect_ssh(item.relative, text)
        for finding in findings:
            key = (finding.file, finding.line, finding.algorithm, finding.detail)
            if key not in seen:
                seen.add(key)
                result.findings.append(finding)
    result.findings.sort(key=lambda f: (f.file, f.line or 0, f.algorithm))
    repeats: Counter = Counter()
    for finding in result.findings:
        base = (finding.file, finding.rule, finding.algorithm, finding.key_size, finding.detail)
        finding.occurrence = repeats[base]
        repeats[base] += 1
    return result


def summary(result: ScanResult) -> dict:
    by_risk = Counter(f.risk for f in result.findings)
    return {
        "files_scanned": result.files_scanned,
        "files_with_findings": len({f.file for f in result.findings}),
        "findings": len(result.findings),
        "by_risk": {risk: by_risk.get(risk, 0) for risk in RISK_ORDER},
        "by_category": dict(sorted(Counter(f.category for f in result.findings).items())),
        "by_algorithm": dict(sorted(Counter(f.algorithm for f in result.findings).items())),
        "heuristic_findings": sum(f.heuristic for f in result.findings),
        "skipped": len(result.skipped),
    }


def to_document(result: ScanResult, *, generated_at: str | None = None) -> dict:
    return {
        "tool": "pq_inventory", "version": __version__, "schema": 1,
        "generated_at": generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "root": result.root, "summary": summary(result), "notes": result.notes,
        "skipped": result.skipped, "findings": [f.to_dict() for f in result.findings],
    }
