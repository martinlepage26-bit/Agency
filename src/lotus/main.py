"""Canonical Lotus CLI entry point."""

from __future__ import annotations

from pathlib import Path

from flowerapp import main as _legacy_main

DATA_DIR = _legacy_main.DATA_DIR


def main():
    _legacy_main.DATA_DIR = Path(DATA_DIR)
    return _legacy_main.main()


if __name__ == "__main__":
    raise SystemExit(main())
