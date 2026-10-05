"""The scanner's CBOM against the official CycloneDX 1.6 JSON schema (tests/fixtures/cyclonedx/).

`jsonschema` is pinned in the `dev` extra (approved 2026-10-05), so this runs in every standard
environment, CI included. The import guard only keeps a bare install from failing on import.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema", reason="jsonschema is not installed: pip install -e '.[dev]'")
referencing = pytest.importorskip("referencing", reason="referencing is not installed (comes with jsonschema 4.18+)")

from pq_inventory import reports  # noqa: E402
from pq_inventory.scanner import scan, to_document  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "tests" / "fixtures" / "cyclonedx"
NAMES = ("bom-1.6.schema.json", "spdx.schema.json", "jsf-0.82.schema.json")


@pytest.fixture(scope="module")
def validator():
    from referencing.jsonschema import DRAFT7

    documents = {name: json.loads((SCHEMAS / name).read_text(encoding="utf-8")) for name in NAMES}
    registry = referencing.Registry().with_resources(
        [(f"http://cyclonedx.org/schema/{name}", referencing.Resource.from_contents(document, default_specification=DRAFT7))
         for name, document in documents.items()])
    jsonschema.Draft7Validator.check_schema(documents[NAMES[0]])
    return jsonschema.Draft7Validator(documents[NAMES[0]], registry=registry, format_checker=jsonschema.FormatChecker())


def _errors(validator, bom: dict) -> list[str]:
    return ["/".join(map(str, error.absolute_path)) + ": " + error.message[:200] for error in validator.iter_errors(bom)]


@pytest.mark.parametrize("state", ["before", "after"])
def test_committed_demo_cboms_are_valid_cyclonedx_1_6(validator, state):
    bom = json.loads((ROOT / "examples" / "warehouse-demo" / "reports" / state / "cbom.cdx.json").read_text())
    assert _errors(validator, bom) == []


def test_corpus_cbom_is_valid_cyclonedx_1_6(validator):
    corpus = ROOT / "tests" / "fixtures" / "pq_inventory"
    bom = reports.cbom(to_document(scan(corpus), generated_at="2026-10-01T00:00:00+00:00"))
    assert len(bom["components"]) > 20 and _errors(validator, bom) == []


def test_the_validator_rejects_what_review_finding_13_fixed(validator):
    """A control: a null size, an unknown asset type and an unknown field are all schema errors."""
    bom = json.loads((ROOT / "examples" / "warehouse-demo" / "reports" / "after" / "cbom.cdx.json").read_text())
    key = next(c for c in bom["components"] if "relatedCryptoMaterialProperties" in c["cryptoProperties"])
    key["cryptoProperties"]["relatedCryptoMaterialProperties"]["size"] = None
    bom["components"][0]["cryptoProperties"]["assetType"] = "nonsense"
    bom["components"][1]["bogusField"] = 1
    errors = _errors(validator, bom)
    assert len(errors) == 3 and any("integer" in e for e in errors) and any("bogusField" in e for e in errors)
