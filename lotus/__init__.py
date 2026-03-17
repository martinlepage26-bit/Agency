"""Standalone Lotus app package.

This top-level package is the canonical local app home in the repository.
It also exposes compatibility wrappers so `lotus.main`, `lotus.web`, and
`lotus.core.*` work from a normal repo checkout without fighting the
historical `src/lotus` package.
"""

from __future__ import annotations

import sys
from pathlib import Path

APP_NAME = "Lotus"
CANONICAL_PACKAGE_NAME = "lotus"
LEGACY_PACKAGE_NAME = "flowerapp"

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_ROOT = _REPO_ROOT / "src"


def _ensure_src_path() -> Path:
    src_root = _SRC_ROOT.resolve()
    src_root_text = str(src_root)
    if src_root_text not in sys.path:
        sys.path.insert(0, src_root_text)
    return src_root


__all__ = [
    "APP_NAME",
    "CANONICAL_PACKAGE_NAME",
    "LEGACY_PACKAGE_NAME",
    "_ensure_src_path",
]
