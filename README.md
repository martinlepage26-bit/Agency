# Agency

Git home for the `Lotus` and `Scripto` app lines.

## Canonical Identity

- `Agency` is the repository name and git home.
- `Lotus` is the social agency scoring app name.
- `Scripto` is the archive-sorting app line; `Dr. Sort-Academic Helper` is its current desktop surface.
- `Agency LOTUS` and `AGENCY LOTUS` are legacy aliases for `Lotus`, not separate products.
- `flowerapp` is only a legacy Python package and CLI alias for Lotus compatibility.
- Use `Lotus` and `Scripto` for user-facing app surfaces.
- Use `Agency` for the repo, remote, and umbrella project reference.

## Current Structure

- `lotus/`
  - Canonical home for the standalone `Lotus` app.
  - Contains the live Lotus desktop code, assets, and upload workspace placeholder.
- `scripto/`
  - Canonical home for the standalone Dr. Sort / Doc sorter app line.
  - Contains the live sorting code, launchers, rules file, and report-generation tooling.
- `desktop/lotus/`
  - Repo-tracked local launcher assets for `Lotus`.
  - Preferred source for local launcher scripts instead of stray desktop copies outside git.
- `desktop/scripto/`
  - Repo-tracked local launcher assets for `Scripto`.
  - Preferred source for local Dr. Sort launcher scripts instead of stray desktop copies outside git.
- `scriptorium_v3/`
  - Legacy mixed workspace for separate app ideas and older experiments.
  - Contains compatibility shims that still forward to the standalone `Lotus` and `Scripto` app homes.
- `src/lotus/`
  - Canonical Python import and CLI alias for `Lotus`.
  - Wraps the historical `flowerapp` package so code can move toward `lotus.*` without breaking older imports.
- `src/flowerapp/`
  - Legacy Lotus Python package namespace and compatibility CLI/web engine.
  - `flowerapp` remains available as a backward-compatible import and command alias.
- `src/voice11/`
  - Optional local speech helper used by the legacy CLI.

## Boundary Rules

- `Lotus` belongs in this repo.
- Duplicate `Lotus` copies outside this repo should be treated as convenience launchers, not canonical sources.
- The old PHAROS-side `Lotus` duplicate should not be recreated.
- `Dr. Sort`, `Doc sorter`, `Scriptorium`, and `Paper Builder` should be treated as separate app lines rather than part of Lotus.
- `Scripto` is the canonical home for the Dr. Sort / Doc sorter code line.
- PHAROS surfaces do not belong here long-term:
  - `CompassAI`
  - `AuroraAI`
  - the removed PHAROS desktop export snapshot that now exists only in git history
- Martin's personal and professional `governai.ca` content does not belong here.

## Compatibility Notes

- The repo path and git remote remain `Agency`, which is correct for the git home.
- `lotus/lotus_app.py` and `lotus/lotus_core.py` are the canonical Lotus app module names.
- `src/lotus/` is the preferred Python package surface for Lotus CLI and imports.
- `src/flowerapp/` remains only as the legacy package name for compatibility.
- `scripto/dr_sort_academic_helper.py` and `scripto/document_sorter.py` are the canonical Scripto module names.
- `Dr. Sort-Academic Helper` is the current desktop label inside the Scripto app line.
- The `scriptorium_v3` folder name is retained only for legacy compatibility and other app concepts.
- `scriptorium_v3/lotus_app.py`, `scriptorium_v3/agency_lotus_app.py`, and the old `Agency LOTUS` launch scripts remain only as compatibility shims.
- `scriptorium_v3/dr_sort_academic_helper.py`, `scriptorium_v3/document_sorter.py`, and the old Dr. Sort launch scripts remain only as compatibility shims.
