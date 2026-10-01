"""Read-only, bounded walk of a directory tree.

Safety: symbolic links are never followed (so no loops and no escaping the root), files above a
size limit and binary files are skipped (with the reason recorded), and nothing is written.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MAX_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_FILES = 50_000
SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv", ".tox", ".mypy_cache", ".pytest_cache"}
# Binary-looking files we still inspect: DER-encoded certificates and keys.
DER_SUFFIXES = {".der", ".cer", ".crt", ".p7b"}


@dataclass
class WalkedFile:
    path: Path
    relative: str
    data: bytes
    is_text: bool


def looks_binary(data: bytes) -> bool:
    return b"\x00" in data[:8192]


def walk(root: Path, *, max_bytes: int = DEFAULT_MAX_BYTES, max_files: int = DEFAULT_MAX_FILES, skipped: list | None = None):
    """Yield WalkedFile for every regular file under root (root itself may be a single file)."""
    skipped = skipped if skipped is not None else []
    root = Path(root)
    if root.is_symlink():
        skipped.append({"file": root.name, "reason": "symlink (not followed)"})
        return
    if root.is_file():
        candidates = [(root, root.name)]
        base = root.parent
    else:
        candidates = None
        base = root
    count = 0

    def visit(path: Path, relative: str):
        nonlocal count
        if count >= max_files:
            skipped.append({"file": relative, "reason": f"file limit {max_files} reached"})
            return None
        if path.is_symlink():
            skipped.append({"file": relative, "reason": "symlink (not followed)"})
            return None
        try:
            stat = path.stat()
        except OSError as error:
            skipped.append({"file": relative, "reason": f"unreadable: {error.__class__.__name__}"})
            return None
        if stat.st_size > max_bytes:
            skipped.append({"file": relative, "reason": f"larger than {max_bytes} bytes"})
            return None
        try:
            data = path.read_bytes()
        except OSError as error:
            skipped.append({"file": relative, "reason": f"unreadable: {error.__class__.__name__}"})
            return None
        binary = looks_binary(data)
        if binary and path.suffix.lower() not in DER_SUFFIXES:
            skipped.append({"file": relative, "reason": "binary file"})
            return None
        count += 1
        return WalkedFile(path, relative, data, not binary)

    if candidates is not None:
        for path, relative in candidates:
            item = visit(path, relative)
            if item:
                yield item
        return
    for directory, dirnames, filenames in os.walk(base, followlinks=False):
        current = Path(directory)
        kept = []
        for name in sorted(dirnames):
            sub = current / name
            rel = sub.relative_to(base).as_posix()
            if name in SKIP_DIRS:
                skipped.append({"file": rel + "/", "reason": "excluded directory"})
            elif sub.is_symlink():
                skipped.append({"file": rel + "/", "reason": "symlink (not followed)"})
            else:
                kept.append(name)
        dirnames[:] = kept
        for name in sorted(filenames):
            path = current / name
            item = visit(path, path.relative_to(base).as_posix())
            if item:
                yield item
