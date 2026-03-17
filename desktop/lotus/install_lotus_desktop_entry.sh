#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
APP_ROOT="$REPO_ROOT/lotus"
DESKTOP_FILE="${XDG_DATA_HOME:-$HOME/.local/share}/applications/lotus.desktop"
ICON_PATH="$APP_ROOT/lotus_icon.png"
LAUNCHER_PATH="$SCRIPT_DIR/launch_lotus.sh"

mkdir -p "$(dirname "$DESKTOP_FILE")"

cat >"$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=LOTUS
Comment=Open the LOTUS desktop app
Exec=$LAUNCHER_PATH
Path=$APP_ROOT
Icon=$ICON_PATH
Terminal=false
Categories=Office;Education;
StartupNotify=true
EOF

chmod +x "$LAUNCHER_PATH"
printf 'Desktop entry written to %s\n' "$DESKTOP_FILE"
