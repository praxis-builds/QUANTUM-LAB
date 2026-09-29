"""Load a lesson script by number so tests can call its main()."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

LESSONS = Path(__file__).resolve().parents[1] / "lessons"


def load_lesson(number: str):
    script = next(LESSONS.glob(f"{number}_*.py"))
    if str(LESSONS) not in sys.path:
        sys.path.insert(0, str(LESSONS))
    spec = importlib.util.spec_from_file_location(f"lesson_{number}", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
