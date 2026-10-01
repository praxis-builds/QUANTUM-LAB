"""Migration roadmap from Mosca's inequality: data is at risk if x + y > z.

x = how many years the data (or a key's trust) must stay secure, y = years needed to migrate the
system, z = years until a cryptographically relevant quantum computer (CRQC). Nobody knows z,
so it is an explicit, labelled assumption. Reference: M. Mosca, "Cybersecurity in an era with
quantum computers: will we be ready?", IEEE Security & Privacy 16(5), 2018.
"""

from __future__ import annotations

import fnmatch
import json
from datetime import date
from pathlib import Path

from .algorithms import CLASSICALLY_BROKEN, QUANTUM_BROKEN, QUANTUM_WEAKENED

DEFAULT_DEADLINE_YEAR = 2035
DEFAULT_ASSUMPTIONS = {
    "z_years": None,  # computed from the deadline year below unless set
    "z_deadline_year": DEFAULT_DEADLINE_YEAR,
    "z_source": ("ASSUMPTION: z = years until 2035, the year NIST IR 8547 (initial public draft, 12 Nov 2024) proposes "
                 "for disallowing quantum-vulnerable public-key algorithms. A regulatory planning horizon, NOT a forecast "
                 "of when a quantum computer will exist. Replace it with your own risk appetite."),
    "x_default_years": 10,
    "x_source": "ASSUMPTION: 10 years of required confidentiality when a system does not say; replace per system.",
    "y_default_years": 5,
    "y_source": "ASSUMPTION: 5 years to migrate when a system does not say; large estates often need longer.",
}
TIERS = {
    1: "Fix now: already weak without any quantum computer",
    2: "Migrate now: at risk under Mosca (x + y > z)",
    3: "Plan migration: quantum-vulnerable, deadline from Mosca",
    4: "Upgrade in routine maintenance: weakened by Grover only",
    5: "No action found",
}


def load_config(path: Path | None) -> dict:
    config = json.loads(Path(path).read_text(encoding="utf-8")) if path else {}
    assumptions = {**DEFAULT_ASSUMPTIONS, **config.get("assumptions", {})}
    reference_year = int(assumptions.get("reference_year") or date.today().year)
    if assumptions.get("z_years") is None:
        assumptions["z_years"] = max(0, int(assumptions["z_deadline_year"]) - reference_year)
    assumptions["reference_year"] = reference_year
    systems = config.get("systems") or [{"name": "Entire scanned tree", "paths": ["*"]}]
    return {"assumptions": assumptions, "systems": systems, "from_file": bool(path)}


def build(findings: list[dict], config: dict) -> dict:
    a = config["assumptions"]
    z = float(a["z_years"])
    items = []
    claimed: set[str] = set()
    for system in config["systems"]:
        patterns = system.get("paths", ["*"])
        mine = [f for f in findings if any(fnmatch.fnmatch(f["file"], p) for p in patterns)]
        claimed.update(f["fingerprint"] for f in mine)
        x = float(system.get("data_lifetime_years", a["x_default_years"]))
        y = float(system.get("migration_years", a["y_default_years"]))
        counts = {risk: sum(f["risk"] == risk for f in mine) for risk in (CLASSICALLY_BROKEN, QUANTUM_BROKEN, QUANTUM_WEAKENED)}
        slack = z - (x + y)
        mosca_at_risk = x + y > z
        if counts[CLASSICALLY_BROKEN]:
            tier = 1
        elif counts[QUANTUM_BROKEN] and mosca_at_risk:
            tier = 2
        elif counts[QUANTUM_BROKEN]:
            tier = 3
        elif counts[QUANTUM_WEAKENED]:
            tier = 4
        else:
            tier = 5
        actions = {}
        for f in sorted(mine, key=lambda f: -f["severity"]):
            if f["risk"] != "OK":
                actions.setdefault(f["algorithm"], {"replacement": f["replacement"], "risk": f["risk"], "count": 0})
                actions[f["algorithm"]]["count"] += 1
        start_by = int(a["reference_year"] + max(0.0, slack)) if counts[QUANTUM_BROKEN] else None
        items.append({
            "system": system.get("name", "unnamed"), "paths": patterns, "notes": system.get("notes", ""),
            "x": x, "y": y, "z": z, "x_from": "config" if "data_lifetime_years" in system else "default assumption",
            "y_from": "config" if "migration_years" in system else "default assumption",
            "slack_years": slack, "mosca_at_risk": mosca_at_risk, "tier": tier, "tier_label": TIERS[tier],
            "counts": counts, "findings": len(mine), "start_migration_by": start_by,
            "actions": [{"algorithm": alg, **info} for alg, info in actions.items()],
        })
    items.sort(key=lambda i: (i["tier"], i["slack_years"], -i["counts"][QUANTUM_BROKEN]))
    unassigned = sum(f["fingerprint"] not in claimed and f["risk"] != "OK" for f in findings)
    return {"assumptions": a, "items": items, "unassigned_findings": unassigned, "config_from_file": config["from_file"]}
