# Scriptorium v3

This folder is no longer the canonical home of `LOTUS`.

Treat `scriptorium_v3/` as legacy mixed workspace territory for separate app ideas, including document-sorting work and older concept experiments. The standalone Lotus app now lives in `../lotus/`, and the canonical Dr. Sort / Doc sorter app now lives in `../scripto/`.

## What Belongs Here

- wrapper scripts and module shims that preserve older paths for Lotus and Scripto
- placeholder working folders such as `INBOX/` and `LOTUS_UPLOADS/` for older local paths
- older concept space associated with names such as `Scriptorium` or `Paper Builder`

## Lotus Compatibility Shims

These files remain here only so older paths do not break immediately:

- `lotus_app.py`
- `lotus_core.py`
- `agency_lotus_app.py`
- `LOTUS.bat`
- `launch_lotus.vbs`
- `Agency LOTUS.bat`
- `launch_agency_lotus.vbs`
- `create_lotus_desktop_shortcuts.ps1`
- `create_agency_lotus_desktop_shortcuts.ps1`

They should be treated as wrappers that forward to the standalone Lotus app in `../lotus/`.

## Scripto Compatibility Shims

These files remain here only so older Dr. Sort paths do not break immediately:

- `dr_sort_academic_helper.py`
- `document_sorter.py`
- `run_document_sorter.ps1`
- `Dr. Sort-Academic Helper.bat`

They should be treated as wrappers that forward to the standalone Scripto app in `../scripto/`.

## Canonical Assets Moved Out

- Lotus icons and preview now live in `../lotus/`
- Dr. Sort support assets, rules, spec, bibliography, and preview now live in `../scripto/`
- If you need to change real app assets rather than wrappers, work in the canonical app folders instead of here

## Important Boundary

- `LOTUS` is not Dr. Sort.
- `LOTUS` is not Doc sorter.
- `LOTUS` is not Scriptorium.
- `LOTUS` is not Paper Builder.

If you are changing the Lotus app itself, work in `../lotus/`.
