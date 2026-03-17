#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
APP_ROOT="$REPO_ROOT/lotus"

cd "$APP_ROOT"
exec python3 "$APP_ROOT/lotus_app.py" "$@"
