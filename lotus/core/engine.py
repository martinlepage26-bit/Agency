"""Local-checkout Lotus engine wrapper."""

from __future__ import annotations

from lotus import _ensure_src_path

_ensure_src_path()

from flowerapp.core.engine import calculate_agency

__all__ = ["calculate_agency"]
