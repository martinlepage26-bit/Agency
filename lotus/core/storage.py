"""Local-checkout Lotus storage wrapper."""

from __future__ import annotations

from lotus import _ensure_src_path

_ensure_src_path()

from flowerapp.core.storage import load_project, save_project

__all__ = ["load_project", "save_project"]
