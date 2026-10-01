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


def _loadable(path: Path) -> bool:
    try:
        ctypes.CDLL(str(path))
    except OSError:
        return False
    return True


def liboqs_library_path() -> Path | None:
    """The liboqs shared library that liboqs-python 0.16 *will* load, or None.

    liboqs-python tries exactly <OQS_INSTALL_PATH or ~/_oqs>/lib/liboqs.so, .../lib64/liboqs.so and
    ctypes.util.find_library("oqs"); if none loads, `import oqs` clones and builds liboqs from GitHub.
    So this accepts only those candidates, and only if they really load (a versioned liboqs.so.9
    without the liboqs.so link, a dangling link or a foreign file would all send oqs to the network).
    """
    root = Path(os.environ["OQS_INSTALL_PATH"]) if "OQS_INSTALL_PATH" in os.environ else Path.home() / "_oqs"
    for sub in ("lib", "lib64"):
        candidate = root / sub / "liboqs.so"
        if candidate.is_file() and _loadable(candidate):
            return candidate
    found = ctypes.util.find_library("oqs")
    if found and _loadable(Path(found)):
        return Path(found)
    return None


def _import_oqs():
    import oqs  # noqa: PLC0415  (only ever reached through load_oqs, after the guard)

    return oqs


def load_oqs():
    """The oqs module, or None if liboqs or liboqs-python is missing. Never auto-installs: oqs is
    imported only when the library it will load is known to load, and OQS_INSTALL_PATH (the variable
    liboqs-python documents) is set to the directory that was checked, so oqs looks exactly there."""
    path = liboqs_library_path()
    if path is None:
        return None
    if path.parent.name in ("lib", "lib64") and path.name == "liboqs.so":
        os.environ["OQS_INSTALL_PATH"] = str(path.parent.parent)
    try:
        return _import_oqs()
    except ImportError:
        return None


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
