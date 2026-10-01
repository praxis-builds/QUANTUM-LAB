"""The static Pages showcase: every lesson rendered, links resolved, no scripts, no repo leaks."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

pytest.importorskip("markdown")

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("build_site", ROOT / "tools" / "build_site.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_site"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site") / "_site"
    _load().build(out)
    return out


def test_every_lesson_and_page_is_rendered(site) -> None:
    lessons = sorted(p.stem for p in (ROOT / "lessons").glob("[0-9][0-9]_*.md"))
    assert len(lessons) == 33
    for stem in lessons:
        assert (site / "lessons" / f"{stem}.html").is_file(), stem
    for rel in ("index.html", "style.css", "lessons/index.html", "case-study.html",
                "pq-inventory.html", "reports/before.html", "reports/after.html", ".nojekyll"):
        assert (site / rel).is_file(), rel


def test_internal_links_resolve_and_no_raw_markdown_links_remain(site) -> None:
    for page in site.rglob("*.html"):
        if page.parent.name == "reports":
            continue  # copied scanner reports are self-contained
        text = page.read_text(encoding="utf-8")
        for target in re.findall(r'href="([^"]+)"', text):
            if re.match(r"^[a-z]+:", target) or target.startswith("#"):
                continue
            assert not target.split("#")[0].endswith(".md"), (page, target)
            assert (page.parent / target.split("#")[0]).resolve().is_file(), (page, target)


def test_pages_carry_no_scripts(site) -> None:
    for page in site.rglob("*.html"):
        assert "<script" not in page.read_text(encoding="utf-8").lower(), page


def test_reports_are_the_committed_ones_and_hold_no_key_material(site) -> None:
    for name in ("before", "after"):
        committed = (ROOT / f"examples/warehouse-demo/reports/{name}/report.html").read_text(encoding="utf-8")
        assert (site / f"reports/{name}.html").read_text(encoding="utf-8") == committed
    for page in site.rglob("*"):
        if page.is_file():
            assert "PRIVATE KEY-----" not in page.read_text(encoding="utf-8", errors="ignore"), page


def test_devcontainer_starts_the_dashboard_in_codespaces_mode() -> None:
    raw = (ROOT / ".devcontainer/devcontainer.json").read_text(encoding="utf-8")
    config = json.loads(re.sub(r"^\s*//.*$", "", raw, flags=re.M))
    assert 8765 in config["forwardPorts"]
    assert "--codespaces" in config["postAttachCommand"]
    assert "--port 8765" in config["postAttachCommand"]
