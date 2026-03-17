# Lotus Launch Assets

This folder is the repo-tracked home for local `Lotus` launcher assets.

Use these files as the source of truth when recreating desktop shortcuts or local launch wrappers. Existing copies under `~/Desktop` or other local folders should be treated as convenience installs, not canonical project files.

The launcher targets the standalone app in `../lotus/`, not the legacy mixed workspace under `scriptorium_v3/`.

Files:
- `launch_lotus.sh`: Linux launcher that resolves the repo path relative to this folder.
- `install_lotus_desktop_entry.sh`: writes a local desktop entry that points back to this repo checkout.
