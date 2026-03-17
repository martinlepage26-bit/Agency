"""Local-checkout Lotus CLI wrapper.

This keeps `lotus.main` importable from the repo root even though the desktop
app folder and the historical `src/lotus` package share the same name.
"""

from __future__ import annotations

from pathlib import Path

from . import _ensure_src_path

_ensure_src_path()

from flowerapp import main as _legacy_main

DATA_DIR = _legacy_main.DATA_DIR


def main():
    _legacy_main.DATA_DIR = Path(DATA_DIR)
    return _legacy_main.main()


if __name__ == "__main__":
    raise SystemExit(main())
