"""Local-checkout Lotus web wrapper."""

from __future__ import annotations

from . import _ensure_src_path

_ensure_src_path()

from flowerapp.web import app

__all__ = ["app"]
