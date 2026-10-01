"""Rule-driven detection in source code and other text (rules: rules/default_rules.json + user files).

A rule is a regular expression applied line by line to files whose name matches `files`:
  {"id": "...", "description": "...", "files": [".py", "DEFAULT.PFL", "*"], "pattern": "...", "flags": "i",
   "algorithm": "RSA"  OR  "algorithm_map": {"md5": "MD5", ...} with "map_group": "alg",
   "key_size_group": "bits" (optional), "category": "source", "heuristic": false}
Whole-line comments are skipped for source files (a comment that mentions MD5 is not a use of MD5).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from .model import Finding

SOURCE_SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".java", ".kt", ".go", ".c", ".h", ".cc",
                   ".cpp", ".cxx", ".hpp", ".cs"}
COMMENT_PREFIXES = ("#", "//", "/*", "*", "--")
MAX_LINE = 4000


@dataclass
class Rule:
    id: str
    description: str
    files: list[str]
    pattern: re.Pattern
    algorithm: str | None
    algorithm_map: dict[str, str] | None
    map_group: str | None
    key_size_group: str | None
    category: str
    heuristic: bool

    def applies_to(self, relative: str) -> bool:
        name = relative.rsplit("/", 1)[-1]
        for selector in self.files:
            if selector == "*" or name == selector or (selector.startswith(".") and name.lower().endswith(selector)):
                return True
            if selector.startswith("*") and name.lower().endswith(selector[1:].lower()):
                return True
        return False


def _compile(raw: dict) -> Rule:
    flags = re.I if "i" in raw.get("flags", "") else 0
    if not raw.get("algorithm") and not raw.get("algorithm_map"):
        raise ValueError(f"rule {raw.get('id')}: needs 'algorithm' or 'algorithm_map'")
    return Rule(id=raw["id"], description=raw.get("description", ""), files=list(raw.get("files", ["*"])),
                pattern=re.compile(raw["pattern"], flags), algorithm=raw.get("algorithm"),
                algorithm_map={k.lower(): v for k, v in raw.get("algorithm_map", {}).items()} or None,
                map_group=raw.get("map_group"), key_size_group=raw.get("key_size_group"),
                category=raw.get("category", "source"), heuristic=bool(raw.get("heuristic", False)))


def load_rules(extra: list[Path] | None = None) -> list[Rule]:
    """The packaged default rules, then any user rule files (JSON; YAML only if PyYAML is installed)."""
    texts = [resources.files("pq_inventory").joinpath("rules/default_rules.json").read_text(encoding="utf-8")]
    sources = ["default_rules.json"]
    for path in extra or []:
        texts.append(Path(path).read_text(encoding="utf-8"))
        sources.append(str(path))
    rules = []
    for source, text in zip(sources, texts):
        if source.endswith((".yaml", ".yml")):
            try:
                import yaml  # noqa: PLC0415 - optional
            except ImportError as error:
                raise ValueError(f"{source}: YAML rule files need PyYAML; use JSON instead") from error
            document = yaml.safe_load(text)
        else:
            document = json.loads(text)
        rules += [_compile(raw) for raw in document["rules"]]
    return rules


def detect(relative: str, text: str, rules: list[Rule]) -> list[Finding]:
    applicable = [rule for rule in rules if rule.applies_to(relative)]
    if not applicable:
        return []
    is_source = Path(relative).suffix.lower() in SOURCE_SUFFIXES
    findings: list[Finding] = []
    seen: set[tuple[int, str]] = set()
    for number, line in enumerate(text.splitlines(), start=1):
        if len(line) > MAX_LINE:
            line = line[:MAX_LINE]  # minified or generated: bound the regex work
        if is_source and line.lstrip().startswith(COMMENT_PREFIXES):
            continue
        for rule in applicable:
            for match in rule.pattern.finditer(line):
                algorithm = rule.algorithm
                if rule.algorithm_map:
                    key = (match.group(rule.map_group) or "").lower()
                    algorithm = rule.algorithm_map.get(key)
                    if algorithm is None:
                        continue
                size = None
                if rule.key_size_group and match.groupdict().get(rule.key_size_group):
                    size = int(match.group(rule.key_size_group))
                if (number, algorithm) in seen:
                    continue  # a more specific rule earlier in the list already reported this
                seen.add((number, algorithm))
                findings.append(Finding.make(file=relative, line=number, category=rule.category, algorithm=algorithm,
                                             rule=rule.id, key_size=size, heuristic=rule.heuristic,
                                             detail=rule.description + (f" ({size}-bit)" if size else ""), evidence=line))
    return findings
