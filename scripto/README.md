# Scripto

`Scripto` is the canonical home for the Dr. Sort / Doc sorter app line inside the `Agency` git repo.

`Dr. Sort-Academic Helper` is the current desktop surface inside the Scripto app line.

## Boundaries

- `Scripto` owns Dr. Sort, document sorting, cross-reference reporting, masterlists, and related archive-processing tools.
- `Lotus` is a separate app and does not belong inside the canonical Scripto code.
- `Paper Builder` is still only a concept boundary and is not yet separated into its own concrete file set.
- `scriptorium_v3/` is now legacy compatibility territory, not the canonical Scripto source.

## Included Files

- `dr_sort_academic_helper.py`: desktop app
- `document_sorter.py`: CLI/library for scanning, classification, planning, and report generation
- `run_document_sorter.ps1`: PowerShell wrapper for scan/apply/report workflows
- `Dr. Sort-Academic Helper.bat`: Windows launcher
- `launch_dr_sort.vbs`: quiet Windows launcher
- `create_dr_sort_desktop_shortcut.ps1`: creates only the Dr. Sort desktop shortcut
- `capture_app_window.ps1` and `capture_tk_window.py`: screenshot helpers
- `MASTER BIBLIOGRAPHY.txt`: bibliography source used by cross-reference matching
- `scripto_rules.example.txt`: plain-English rules examples for the sorter
- `SCRIPTO_PREMIUM_SPEC.md`: premium product-direction note for the Scripto app line
- `Dr_Sort_preview.png`: reference preview capture for the desktop app
- `INBOX/.gitkeep`: placeholder for the default drop folder

## Quick Start

Windows:

```powershell
cd .\scripto
py .\dr_sort_academic_helper.py
```

PowerShell scan:

```powershell
cd .\scripto
.\run_document_sorter.ps1 -Mode scan -RenderCrossReference -RenderMasterlist
```

## Notes

- Runtime output folders such as `REPORTS_V2`, `SORTED_LIBRARY_V2`, and `QUARANTINE` are intentionally ignored in git.
- The repo and remote remain named `Agency`; that is the umbrella git home, not the app name.
- `Dr. Sort-Academic Helper` is the current user-facing launcher name; `Scripto` names the broader app line and folder.
