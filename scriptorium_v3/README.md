# Agency LOTUS / Dr. Sort-Academic Helper

Desktop document sorter and report generator for mixed research, admin, and creative archives.

Included files:
- `document_sorter.py`: core scan, classification, dedupe, cross-reference, and masterlist engine
- `dr_sort_academic_helper.py`: Tk desktop app
- `Dr. Sort-Academic Helper.bat`: Windows launcher
- `run_document_sorter.ps1`: PowerShell wrapper
- `launch_agency_lotus.vbs`: quiet Windows launcher
- `create_agency_lotus_desktop_shortcuts.ps1`: creates desktop shortcuts
- `pdf_rename_sort.py`: legacy reference script retained for comparison
- `MASTER BIBLIOGRAPHY.txt`: bibliography source used by cross-reference matching
- `agency_lotus_rules.example.txt`: plain-English rules examples
- `AGENCY_LOTUS_PREMIUM_SPEC.md`: premium roadmap and capability notes
- `agency_lotus_icon.ico`: lotus-flower desktop icon
- `LOTUS_UPLOADS/README.lotus`: placeholder for local LOTUS uploads

Main functions:
- Scan PDFs, DOCX, DOC, TXT, and Markdown files
- Extract title, author, date, DOI, ISBN, language, and document type
- Detect exact and probable duplicates
- Preview proposed destinations before sorting
- Render cross-reference reports
- Render masterlists
- Semantic local search, rules, monitor scaffold, and undo support
- LOTUS tab for Agency markdown/text uploads and creative-meaning notes

Windows quick start:

```powershell
py -m pip install pymupdf
cd .\scriptorium_v3
py .\dr_sort_academic_helper.py
```

PowerShell scan with extra reports:

```powershell
cd .\scriptorium_v3
.\run_document_sorter.ps1 -Mode scan -RenderCrossReference -RenderMasterlist
```

Notes:
- The repo folder remains named `scriptorium_v3`, but the app itself is now `Agency LOTUS / Dr. Sort-Academic Helper`.
- OCR support depends on `ocrmypdf` being installed and available.
- LOTUS uploads are local workspace content and are intentionally not versioned except for the placeholder file.
- Runtime output folders such as `REPORTS_V2`, `SORTED_LIBRARY_V2`, and `QUARANTINE` are intentionally ignored in git.
