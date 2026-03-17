"""Legacy Lotus package namespace.

Lotus is the canonical app name. The historical Python package and CLI alias
`flowerapp` remain available so older scripts and imports keep working.
"""

APP_NAME = "Lotus"
CANONICAL_PACKAGE_NAME = "lotus"
LEGACY_PACKAGE_NAME = "flowerapp"

__all__ = ["APP_NAME", "CANONICAL_PACKAGE_NAME", "LEGACY_PACKAGE_NAME"]
