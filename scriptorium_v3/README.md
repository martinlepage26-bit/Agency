# Agency LOTUS / Dr. Sort-Academic Helper

Two connected desktop apps for premium local-first archive organization:
- `Dr. Sort-Academic Helper`: professional file sorting, metadata extraction, renaming, dedupe, review, and reporting
- `Agency LOTUS`: standalone note scoring workspace fed by uploads or Dr. Sort plan exports

Included files:
- `document_sorter.py`: core scan, classification, dedupe, cross-reference, destination-planning, and masterlist engine
- `dr_sort_academic_helper.py`: main professional sorter desktop app
- `agency_lotus_core.py`: shared LOTUS note import, scoring, and Dr. Sort feed logic
- `agency_lotus_app.py`: standalone Agency LOTUS score app
- `Dr. Sort-Academic Helper.bat`: Windows launcher for Dr. Sort
- `Agency LOTUS.bat`: Windows launcher for Agency LOTUS
- `run_document_sorter.ps1`: PowerShell wrapper for scan/apply/report workflows
- `launch_dr_sort.vbs`: quiet Windows launcher for Dr. Sort
- `launch_agency_lotus.vbs`: quiet Windows launcher for Agency LOTUS
- `create_agency_lotus_desktop_shortcuts.ps1`: creates separate desktop shortcuts for both apps
- `pdf_rename_sort.py`: legacy reference script retained for comparison
- `MASTER BIBLIOGRAPHY.txt`: bibliography source used by cross-reference matching
- `agency_lotus_rules.example.txt`: plain-English rules examples
- `AGENCY_LOTUS_PREMIUM_SPEC.md`: premium roadmap and capability notes
- `agency_lotus_icon.ico`: lotus-flower desktop icon
- `LOTUS_UPLOADS/README.lotus`: placeholder for local LOTUS uploads

Dr. Sort main functions:
- Scan PDFs, DOCX, DOC, TXT, and Markdown files
- Extract title, author, date, DOI, ISBN, language, and document type
- Detect exact and probable duplicates
- Rename files contextually and plan destinations with multiple folder schemas
- Review by confidence, duplicate state, unclear state, and other sort filters
- Render cross-reference reports and masterlists
- Apply plain-English rules, local semantic search, and folder monitoring scaffolding
- Feed the current sorting plan into LOTUS as a scored note set

Agency LOTUS main functions:
- Upload `.md` and `.txt` files into the LOTUS workspace
- Score notes across agency, strategy, governance, operational, creative, and meaning signals
- Review uploaded notes separately from Dr. Sort while sharing the same LOTUS data root
- Open as a standalone app or inside the LOTUS tab within Dr. Sort

Windows quick start:

```powershell
py -m pip install pymupdf
cd .\scriptorium_v3
py .\dr_sort_academic_helper.py
```

Standalone LOTUS quick start:

```powershell
cd .\scriptorium_v3
py .\agency_lotus_app.py
```

PowerShell scan with extra reports:

```powershell
cd .\scriptorium_v3
.\run_document_sorter.ps1 -Mode scan -RenderCrossReference -RenderMasterlist
```

Notes:
- The repo folder remains named `scriptorium_v3`, while the shipped desktop apps are `Agency LOTUS` and `Dr. Sort-Academic Helper`.
- OCR support depends on `ocrmypdf` being installed and available.
- LOTUS uploads are local workspace content and are intentionally not versioned except for the placeholder file.
- Runtime output folders such as `REPORTS_V2`, `SORTED_LIBRARY_V2`, and `QUARANTINE` are intentionally ignored in git.
