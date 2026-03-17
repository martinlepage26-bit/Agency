#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
APP_ROOT="$REPO_ROOT/scripto"
DESKTOP_FILE="${XDG_DATA_HOME:-$HOME/.local/share}/applications/dr-sort-academic-helper.desktop"
LAUNCHER_PATH="$SCRIPT_DIR/launch_dr_sort.sh"

mkdir -p "$(dirname "$DESKTOP_FILE")"

cat >"$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Dr. Sort-Academic Helper
Comment=Open the Dr. Sort-Academic Helper desktop app
Exec=$LAUNCHER_PATH
Path=$APP_ROOT
Terminal=false
Categories=Office;Education;
StartupNotify=true
EOF

chmod +x "$LAUNCHER_PATH"
printf 'Desktop entry written to %s\n' "$DESKTOP_FILE"
