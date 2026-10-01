"""Compare two scans (fixed / new / unchanged) to track migration progress.

Findings are matched by fingerprint (file, rule, algorithm, key size, detail), not by line
number, so editing unrelated lines does not turn a finding into "fixed + new".
"""

from __future__ import annotations

import json
from pathlib import Path

from .algorithms import RISK_ORDER


def compare(old: dict, new: dict) -> dict:
    old_by = {f["fingerprint"]: f for f in old["findings"]}
    new_by = {f["fingerprint"]: f for f in new["findings"]}
    fixed = [old_by[k] for k in sorted(old_by.keys() - new_by.keys())]
    added = [new_by[k] for k in sorted(new_by.keys() - old_by.keys())]
    unchanged = [new_by[k] for k in sorted(old_by.keys() & new_by.keys())]

    def counts(findings):
        return {risk: sum(f["risk"] == risk for f in findings) for risk in RISK_ORDER}

    return {"old": {"root": old["root"], "generated_at": old["generated_at"], "by_risk": old["summary"]["by_risk"]},
            "new": {"root": new["root"], "generated_at": new["generated_at"], "by_risk": new["summary"]["by_risk"]},
            "fixed": fixed, "new_findings": added, "unchanged": unchanged,
            "counts": {"fixed": counts(fixed), "new": counts(added), "unchanged": counts(unchanged)}}


def write_markdown(result: dict, path: Path) -> None:
    c = result["counts"]
    out = ["# Cryptography inventory: progress", "",
           f"Before: `{result['old']['root']}` ({result['old']['generated_at']})  ", f"After: `{result['new']['root']}` ({result['new']['generated_at']})", "",
           "| Risk | Before | After | Fixed | New | Unchanged |", "|---|---:|---:|---:|---:|---:|"]
    for risk in RISK_ORDER:
        out.append(f"| {risk} | {result['old']['by_risk'][risk]} | {result['new']['by_risk'][risk]} | {c['fixed'][risk]} | "
                   f"{c['new'][risk]} | {c['unchanged'][risk]} |")
    for title, key in (("Fixed (risky findings that disappeared)", "fixed"), ("New (all findings that appeared, including OK)", "new_findings"),
                       ("Still open (risky findings in both scans)", "unchanged")):
        items = [f for f in result[key] if f["risk"] != "OK"] if key != "new_findings" else result[key]
        out += ["", f"## {title}: {len(items)}", ""]
        out += [f"- `{f['file']}`:{f['line'] or '-'} {f['risk']} {f['algorithm']}: {f['detail']}" for f in items] or ["- none"]
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
