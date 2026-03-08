# PHAROS Governance Desktop Suite

This folder packages the PHAROS-aligned desktop surfaces for:

- `LOTUS`: scoring and structured note intake
- `Dr. Sort-Academic Helper`: professional document sorting and review
- `CompassAI`: governance intake and tiering dashboard

## Layout

- `lotus_dr_sort/`
  - `lotus_app.py`
  - `dr_sort_academic_helper.py`
  - `document_sorter.py`
  - Windows launchers, icons, rules, and previews
- `compass_ai/`
  - `CompassAI.html`
  - Windows launchers, icon, and preview

## What Is Included

- The PHAROS-style visual refresh
- Desktop launchers and shortcut scripts
- Curated screenshots of the current surfaces
- Minimal empty folders for `INBOX/` and `LOTUS_UPLOADS/`

## What Is Not Included

- Local `.venv` folders
- User data, uploaded notes, reports, quarantine, or sorted libraries
- Temporary browser caches and test output

## Python Setup

From PowerShell inside `lotus_dr_sort`:

```powershell
py -m pip install -r requirements.txt
py .\lotus_app.py
py .\dr_sort_academic_helper.py
```

## Windows Launchers

Inside `lotus_dr_sort`:

- `LOTUS.bat`
- `Dr. Sort-Academic Helper.bat`
- `create_lotus_desktop_shortcuts.ps1`

Inside `compass_ai`:

- `CompassAI.bat`
- `create_compass_ai_desktop_shortcut.ps1`

## Notes

- `LOTUS` and `Dr. Sort` are Tk desktop apps and use the closest system-font rendering to the PHAROS web look.
- `CompassAI` is HTML/CSS and can match the PHAROS visual language more directly.
