# Scriptorium.v3

Desktop document sorter and report generator for mixed research and admin archives.

Included files:
- `document_sorter.py`: core scan, classification, dedupe, cross-reference, and masterlist engine
- `scriptorium_v3.py`: Tk desktop app
- `Scriptorium.v3.bat`: Windows launcher
- `run_document_sorter.ps1`: PowerShell wrapper
- `pdf_rename_sort.py`: legacy reference script retained for comparison
- `MASTER BIBLIOGRAPHY.txt`: bibliography source used by cross-reference matching

Main functions:
- Scan PDFs, DOCX, DOC, and TXT files
- Extract title, author, date, DOI, ISBN, language, and document type
- Detect exact and probable duplicates
- Preview proposed destinations before sorting
- Render cross-reference reports
- Render masterlists

Windows quick start:

```powershell
py -m pip install pymupdf
cd .\scriptorium_v3
py .\scriptorium_v3.py
```

PowerShell scan with extra reports:

```powershell
cd .\scriptorium_v3
.\run_document_sorter.ps1 -Mode scan -RenderCrossReference -RenderMasterlist
```

Notes:
- OCR support depends on `ocrmypdf` being installed and available.
- Runtime output folders such as `REPORTS_V2`, `SORTED_LIBRARY_V2`, and `QUARANTINE` are intentionally ignored in git.
