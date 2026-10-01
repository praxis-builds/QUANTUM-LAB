"""Skip post-quantum tests cleanly when the optional [pqc] extra (or liboqs) is not installed."""

from __future__ import annotations

import sys

import pytest

from _lessons import LESSONS

if str(LESSONS) not in sys.path:
    sys.path.insert(0, str(LESSONS))

import _pqc  # noqa: E402

REASON = _pqc.missing_reason()
needs_pqc = pytest.mark.skipif(REASON is not None, reason=REASON or "")
