"""Post-quantum crypto helpers for lessons 30-33 (optional extra: pip install -e '.[pqc]').

liboqs-python needs the liboqs C library. If it cannot find it, `import oqs` tries to download
and build liboqs from GitHub. A lesson must never do that by surprise, so we look for the shared
library first and only import oqs when it is there.
"""

from __future__ import annotations

import ctypes.util
import os
import statistics
import time
from pathlib import Path

LIBOQS_HINT = ("liboqs not found. Build liboqs 0.16.0 as a shared library into ~/_oqs (or set OQS_INSTALL_PATH) "
               "and pip install -e '.[pqc]'; see docs/DECISIONS.md (D1).")
CRYPTOGRAPHY_HINT = "the 'cryptography' package is missing: pip install -e '.[pqc]'"


def liboqs_library_path() -> Path | None:
    """Where liboqs-python would load liboqs from, without triggering its auto-installer."""
    roots = [Path(os.environ["OQS_INSTALL_PATH"])] if "OQS_INSTALL_PATH" in os.environ else [Path.home() / "_oqs"]
    for root in roots:
        for sub in ("lib", "lib64"):
            for candidate in sorted((root / sub).glob("liboqs.so*")) if (root / sub).is_dir() else []:
                return candidate
    found = ctypes.util.find_library("oqs")
    return Path(found) if found else None


def load_oqs():
    """The oqs module, or None if liboqs or liboqs-python is missing (never auto-installs)."""
    if liboqs_library_path() is None:
        return None
    try:
        import oqs  # noqa: PLC0415  (imported only once the library is known to exist)
    except ImportError:
        return None
    return oqs


def missing_reason() -> str | None:
    """Why the PQC lessons cannot run here, or None if they can."""
    try:
        import cryptography  # noqa: F401, PLC0415
    except ImportError:
        return CRYPTOGRAPHY_HINT
    if load_oqs() is None:
        return LIBOQS_HINT
    return None


def median_time(function, repeats: int = 200) -> float:
    """Median wall-clock seconds of one call (timings are machine-dependent and only indicative)."""
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        function()
        samples.append(time.perf_counter() - start)
    return statistics.median(samples)
