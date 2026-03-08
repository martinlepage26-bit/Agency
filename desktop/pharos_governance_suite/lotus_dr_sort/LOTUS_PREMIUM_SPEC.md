# LOTUS Premium Spec

`LOTUS | Dr. Sort-Academic Helper` is evolving from a safe document sorter into a high-end, local-first, content-aware archive application.

## Core Product Direction

- Intelligent AI-assisted classification based on file content, metadata, structure, and naming patterns
- Contextual renaming into standardized descriptive filenames
- Automatic folder hierarchy generation by category, type, date, and future custom schemas such as project or client
- Local-first operation for privacy-sensitive archives
- Review-before-apply workflow with undo

## Premium Feature Set

### Intelligent AI-Powered Automation

- Content-aware analysis for `PDF`, `DOCX`, `DOC`, and `TXT`
- Metadata extraction for title, author, date, DOI, ISBN, language, and file type
- Intelligent tagging for retrieval and downstream automation
- Rules-assisted classification overrides and filename templating
- Contextual renaming into richer descriptive filenames
- Duplicate-aware planning before files are moved or copied

### Deep Integration and Customization

- Plain-English rules file
- Cross-reference reporting against the current scan set and `MASTER BIBLIOGRAPHY.txt`
- Real-time monitoring scaffold for watched folders
- Sort-view controls for proposed actions and review order
- Folder hierarchy generation by category, document type, author, and date cues
- Windows launcher plus PowerShell wrapper for the same engine

### Advanced Search and Security

- Local semantic-style search over title, authors, tags, metadata, and extracted content
- Exact and probable duplicate detection
- Local-only processing by default
- Privacy-first behavior: no cloud dependency is required for the current workflow

### User Experience

- Pre-move review table
- Cross Reference report viewer
- Render Masterlist export
- Undo last sort action
- Search, monitor, rules, and sort controls in one desktop hub

## Current Implementation Status

Implemented now:

- content-aware scan and classification
- duplicate detection
- cross-reference reports
- masterlist rendering
- sort-by review control
- intelligent tag generation
- semantic local search foundation
- plain-English rules foundation
- real-time folder monitoring scaffold
- undo-last-sort support
- contextual renaming templates through rules
- local-first privacy-preserving workflow
- PowerShell access to rules via `-RulesFile`

Planned next:

- cloud sync connectors
- richer rule grammar
- project/client-specific folder schemas
- image/video understanding
- stronger semantic ranking models
- plain-English rule builder inside the GUI
- explicit client/project lenses and saved views

## Requested Premium Vision Mapping

The target product direction from the latest spec is now mapped like this:

- `Intelligent AI-Powered Automation`: implemented in foundation form through content extraction, metadata analysis, classification, tagging, rename templating, and automatic destination planning
- `Deep Integration and Customization`: implemented in foundation form through plain-English rules, monitoring scaffold, desktop UI, and PowerShell wrapper
- `Advanced Search and Security`: implemented in foundation form through local semantic-style search, duplicate detection, and local-only processing
- `User Experience`: implemented now through pre-move review, report viewer, cross-reference, masterlist rendering, and undo

Still premium-roadmap rather than fully shipped:

- cloud-sync connectors for OneDrive, Dropbox, and Google Drive
- content understanding for images and video
- stronger semantic ranking beyond local heuristic scoring
- a fully visual rules engine instead of a text rules file
