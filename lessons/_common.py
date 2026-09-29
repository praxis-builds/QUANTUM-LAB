"""Small helpers shared by the lesson scripts (output folder, plot backend)."""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

SEED = 20260928


def out_dir() -> Path:
    """Plots go to lessons/out/ (git-ignored); tests override it with PRAXIS_LESSONS_OUT."""
    path = Path(os.environ.get("PRAXIS_LESSONS_OUT", Path(__file__).resolve().parent / "out"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def heading(text: str) -> None:
    print(f"\n=== {text} ===")
