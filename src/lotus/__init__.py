"""Canonical Lotus Python package alias.

The historical package name `flowerapp` remains available for compatibility,
but new code should prefer `lotus`.
"""

from flowerapp import APP_NAME, CANONICAL_PACKAGE_NAME, LEGACY_PACKAGE_NAME

__all__ = ["APP_NAME", "CANONICAL_PACKAGE_NAME", "LEGACY_PACKAGE_NAME"]
