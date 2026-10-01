"""Read-only, bounded walk of a directory tree.

Safety: symbolic links are never followed (so no loops and no escaping the root), anything that is
not a regular file (FIFOs, sockets, devices) is skipped before it is opened, files above a size
limit and binary files are skipped (all with the reason recorded), reads are capped at the limit,
the walk stops at the file limit, and nothing is written.
"""

from __future__ import annotations

import os
import stat as stat_module
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MAX_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_FILES = 50_000
SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv", ".tox", ".mypy_cache", ".pytest_cache"}
# Binary-looking files we still inspect: DER-encoded certificates and keys.
DER_SUFFIXES = {".der", ".cer", ".crt", ".p7b"}


NON_REGULAR = ((stat_module.S_ISFIFO, "FIFO"), (stat_module.S_ISSOCK, "socket"), (stat_module.S_ISCHR, "character device"),
               (stat_module.S_ISBLK, "block device"), (stat_module.S_ISDIR, "directory"))


def _kind(mode: int) -> str:
    return next((name for test, name in NON_REGULAR if test(mode)), "special file")


def read_regular_file(path: Path, max_bytes: int) -> bytes | str:
    """The file's bytes, or the reason it was skipped. Opens with O_NONBLOCK | O_NOFOLLOW so a FIFO or a
    link swapped in after the lstat check cannot block or redirect the read, re-checks the type on the
    open descriptor, and never reads more than max_bytes + 1 bytes (sizes can lie or grow)."""
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    try:
        info = os.lstat(path)
        if stat_module.S_ISLNK(info.st_mode):
            return "symlink (not followed)"
        if not stat_module.S_ISREG(info.st_mode):
            return f"not a regular file ({_kind(info.st_mode)})"
        if info.st_size > max_bytes:
            return f"larger than {max_bytes} bytes"
        fd = os.open(path, flags)
    except OSError as error:
        return f"unreadable: {error.__class__.__name__}"
    try:
        info = os.fstat(fd)
        if not stat_module.S_ISREG(info.st_mode):
            return f"not a regular file ({_kind(info.st_mode)})"
        chunks, total = [], 0
        while total <= max_bytes:
            chunk = os.read(fd, min(1 << 20, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
    except OSError as error:
        return f"unreadable: {error.__class__.__name__}"
    finally:
        os.close(fd)
    if total > max_bytes:
        return f"larger than {max_bytes} bytes"
    return b"".join(chunks)


@dataclass
class WalkedFile:
    path: Path
    relative: str
    data: bytes
    is_text: bool


def looks_binary(data: bytes) -> bool:
    return b"\x00" in data[:8192]


def without_bom(data: bytes) -> bytes:
    """UTF-16 text with a byte-order mark (common for Windows configuration files) re-encoded as UTF-8, and
    a UTF-8 byte-order mark removed. UTF-16 is full of NUL bytes and would otherwise be skipped as binary.
    UTF-16 without a mark is not recognised: it is still skipped as a binary file, with that reason."""
    if data[:3] == b"\xef\xbb\xbf":
        return data[3:]
    if data[:2] in (b"\xff\xfe", b"\xfe\xff") and data[2:4] != b"\x00\x00":  # not a UTF-32 mark
        try:
            return data.decode("utf-16").encode("utf-8")
        except UnicodeDecodeError:
            return data
    return data


def walk(root: Path, *, max_bytes: int = DEFAULT_MAX_BYTES, max_files: int = DEFAULT_MAX_FILES, skipped: list | None = None):
    """Yield WalkedFile for every regular file under root (root itself may be a single file)."""
    skipped = skipped if skipped is not None else []
    root = Path(root)
    if root.is_symlink():
        skipped.append({"file": root.name, "reason": "symlink (not followed)"})
        return
    if not root.is_dir():  # a single file (regular or not: read_regular_file decides)
        candidates = [(root, root.name)]
        base = root.parent
    else:
        candidates = None
        base = root
    count = 0

    def visit(path: Path, relative: str):
        nonlocal count
        data = read_regular_file(path, max_bytes)
        if isinstance(data, str):
            skipped.append({"file": relative, "reason": data})
            return None
        data = without_bom(data)
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
            if count >= max_files:  # stop here: one entry, not one per remaining file
                skipped.append({"file": path.relative_to(base).as_posix(),
                                "reason": f"file limit {max_files} reached; this and all later files were not read"})
                return
            item = visit(path, path.relative_to(base).as_posix())
            if item:
                yield item
