"""lessons/_pqc.py must never let `import oqs` reach liboqs-python's auto-installer (review finding 12).

liboqs-python 0.16 loads exactly <OQS_INSTALL_PATH or ~/_oqs>/lib{,64}/liboqs.so or whatever
ctypes.util.find_library("oqs") returns, and otherwise clones and builds liboqs from GitHub. The
guard has to accept nothing more than that. These tests only call the guard, never load_oqs().
"""

from __future__ import annotations

import ctypes.util
import os
import sys

import pytest

from _lessons import LESSONS

if str(LESSONS) not in sys.path:
    sys.path.insert(0, str(LESSONS))

import _pqc  # noqa: E402


@pytest.fixture
def no_system_liboqs(monkeypatch):
    monkeypatch.setattr(ctypes.util, "find_library", lambda name: None)


@pytest.mark.parametrize("files", [["liboqs.so.9"], ["liboqs.so.0.16.0"], ["liboqs.a"], ["liboqs.so"]])
def test_guard_rejects_libraries_liboqs_python_would_not_load(tmp_path, monkeypatch, no_system_liboqs, files):
    (tmp_path / "lib").mkdir()
    for name in files:
        (tmp_path / "lib" / name).write_bytes(b"not a shared library")  # an empty/foreign liboqs.so cannot load either
    monkeypatch.setenv("OQS_INSTALL_PATH", str(tmp_path))
    assert _pqc.liboqs_library_path() is None


@pytest.mark.skipif(os.name == "nt", reason="symlinks")
def test_guard_rejects_a_dangling_liboqs_link(tmp_path, monkeypatch, no_system_liboqs):
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "liboqs.so").symlink_to(tmp_path / "lib" / "gone.so")
    monkeypatch.setenv("OQS_INSTALL_PATH", str(tmp_path))
    assert _pqc.liboqs_library_path() is None


def test_load_oqs_does_not_import_oqs_when_the_guard_fails(tmp_path, monkeypatch, no_system_liboqs):
    monkeypatch.setenv("OQS_INSTALL_PATH", str(tmp_path))

    def forbidden_import(*args, **kwargs):
        raise AssertionError("import oqs would run liboqs-python's auto-installer")

    monkeypatch.setattr(_pqc, "_import_oqs", forbidden_import)
    assert _pqc.load_oqs() is None


def test_a_real_liboqs_is_found_and_pinned_through_oqs_install_path(monkeypatch):
    root = os.environ.get("OQS_INSTALL_PATH") or os.path.expanduser("~/_oqs")
    if not any(os.path.isfile(os.path.join(root, sub, "liboqs.so")) for sub in ("lib", "lib64")):
        pytest.skip("no liboqs build in OQS_INSTALL_PATH or ~/_oqs")
    monkeypatch.setenv("OQS_INSTALL_PATH", root)  # restored afterwards; load_oqs() sets it again itself
    monkeypatch.delenv("OQS_INSTALL_PATH")
    path = _pqc.liboqs_library_path()
    assert path is not None and path.name == "liboqs.so"
    assert _pqc.load_oqs() is not None
    assert os.environ["OQS_INSTALL_PATH"] == str(path.parent.parent)  # oqs now looks exactly where we checked
