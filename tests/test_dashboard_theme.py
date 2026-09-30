"""Dashboard theme tokens: complete, non-circular, and readable (WCAG AA) in both themes."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

CSS = (Path(__file__).resolve().parents[1] / "src" / "praxis_quantum_lab" / "dashboard_assets" / "style.css").read_text(encoding="utf-8")


def token_block(selector_start: str) -> dict[str, str]:
    start = CSS.index(selector_start)
    body = CSS[CSS.index("{", start) + 1: CSS.index("}", start)]
    return dict(re.findall(r"--([a-z-]+):\s*([^;]+);", body))


DARK = token_block(':root[data-theme="dark"]')
LIGHT = token_block(':root[data-theme="light"]')
LIGHT_MEDIA = token_block(':root:not([data-theme="dark"])')


def test_themes_define_the_same_tokens_and_media_matches_toggle():
    assert set(DARK) == set(LIGHT) == set(LIGHT_MEDIA)
    assert LIGHT == LIGHT_MEDIA  # OS preference and the header toggle give the same light theme
    assert len(DARK) >= 50


def test_every_used_variable_is_defined_and_none_is_circular():
    used = set(re.findall(r"var\(--([a-z-]+)\)", CSS))
    assert used <= set(DARK) | {"mono"}, used - set(DARK)
    for name, value in re.findall(r"--([a-z-]+):\s*([^;]+);", CSS):
        assert f"var(--{name})" not in value, f"--{name} refers to itself"
    assert re.search(r'--mono:\s*ui-monospace', CSS)
    # outside the token blocks, colours come only from tokens
    rules = CSS[CSS.index(":root {"):]
    assert not re.findall(r"#[0-9a-fA-F]{3,6}\b|rgba?\(", rules)


def test_reduced_motion_is_respected():
    block = CSS[CSS.index("@media (prefers-reduced-motion: reduce)"):]
    assert "transition: none !important" in block and "animation: none !important" in block


def luminance(color: str) -> float:
    color = color.strip()
    if color.startswith("#"):
        channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    else:
        channels = [int(c) / 255 for c in color.split(",")]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


# (foreground token, background token): text that users must read.
TEXT_PAIRS = [
    (fg, bg) for fg in ("text", "muted", "label", "empty", "footer", "caption-text", "accent", "blue", "warning", "danger", "negative-text")
    for bg in ("bg", "panel", "surface")
] + [
    ("text", "raised"), ("text", "raised-hover"), ("text", "chip-bg"), ("muted", "badge-bg"),
    ("on-accent", "accent"), ("on-accent", "accent-hover"),
    ("accent", "tab-active-bg"), ("accent", "good-bg"), ("accent", "pressed-bg"), ("warning", "warning-bg"),
    ("info-text", "info-bg"), ("caution-text", "caution-bg"), ("danger", "danger-bg"),
    ("gate-text", "gate-fill"), ("gate-text-dim", "gate-fill"), ("gate-caption", "panel"), ("text", "selected-row"),
    ("heat-text-weak", "heat-zero"),
]


@pytest.mark.parametrize("theme_name,theme", [("dark", DARK), ("light", LIGHT)])
@pytest.mark.parametrize("fg,bg", TEXT_PAIRS)
def test_text_contrast_meets_wcag_aa(theme_name, theme, fg, bg):
    ratio = contrast(theme[fg], theme[bg])
    assert ratio >= 4.5, f"{theme_name}: --{fg} on --{bg} is {ratio:.2f}:1"


@pytest.mark.parametrize("theme", [DARK, LIGHT])
def test_non_text_graphics_meet_3_to_1(theme):
    # WCAG 1.4.11: meaningful graphics against the panel they sit on.
    for token in ("accent", "warning", "danger", "blue", "control-border", "gate-stroke", "wire", "sphere-stroke"):
        assert contrast(theme[token], theme["panel"]) >= 3.0, token
    assert contrast(theme["heat-text-strong"], theme["heat-positive"]) >= 3.0
