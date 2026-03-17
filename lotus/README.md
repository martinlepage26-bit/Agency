# LOTUS

`LOTUS` is a standalone app for scoring social agency from local notes.

This is the canonical home of the Lotus app inside the `Agency` git repo.

## Boundaries

- `LOTUS` is its own app.
- `Dr. Sort`, `Doc sorter`, and other document-sorting tools are separate apps.
- `Scripto` is the canonical home for the Dr. Sort / Doc sorter app line.
- `Scriptorium`, `Paper Builder`, and related concepts are separate app ideas.
- `scriptorium_v3/` is legacy mixed workspace territory and compatibility shims, not the canonical Lotus source.

## Included Files

- `lotus_app.py`: standalone desktop app
- `lotus_core.py`: local note loading and social agency scoring logic
- `LOTUS.bat`: Windows launcher
- `launch_lotus.vbs`: quiet Windows launcher
- `create_lotus_desktop_shortcuts.ps1`: creates only the Lotus desktop shortcut
- `lotus_icon.ico` and `lotus_icon.png`: Lotus app icons
- `LOTUS_preview.png`: reference preview capture for the desktop app
- `LOTUS_UPLOADS/README.lotus`: placeholder for local Lotus uploads

## Quick Start

Windows:

```powershell
cd .\lotus
py .\lotus_app.py
```

Linux:

```bash
cd ./lotus
python3 lotus_app.py
```

## Notes

- Lotus reads local `.md` and `.txt` notes from `LOTUS_UPLOADS/`.
- Upload content is intentionally local workspace data and is not versioned except for the placeholder file.
- The repo and remote remain named `Agency`; that is the git umbrella, not the app name.
- The older local CLI and web engine still lives under `src/flowerapp/` for compatibility, with `src/lotus/` as the preferred Python import and CLI alias.
