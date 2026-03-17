# pdf_rename_sort.py
# Safe rename + sort for PDFs
# Buckets:
#   PERSONAL\RESEARCH\...
#   PERSONAL\WRITINGS\...
#   SCHOLAR\...
# Fallbacks:
#   UNCLEAR\...

from __future__ import annotations
import unicodedata
import argparse
import unicodedata
import csv
import unicodedata
import datetime as dt
import unicodedata
import re
import unicodedata
from pathlib import Path
import unicodedata
from typing import Dict, List, Optional, Tuple
import unicodedata

import fitz  # PyMuPDF

# Silence MuPDF stderr warnings/errors (prevents 'No default Layer config' spam)
try:
    fitz.TOOLS.mupdf_display_errors(False)
    fitz.TOOLS.mupdf_display_warnings(False)
except Exception:
    pass
import unicodedata


INVALID_CHARS = r'<>:"/\|?*'

def norm(s: str) -> str:
    """
    Lowercase + remove accents/diacritics to make matching robust for French OCR.
    """
    s = (s or "").lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s
RE_INVALID = re.compile(rf"[{re.escape(INVALID_CHARS)}]")
RE_WS = re.compile(r"\s+")

RE_DOI = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
OCR_MIN_TEXT = 999999
RE_NUMERIC_LINE = re.compile(r"^\s*[\dIVXLC]+\s*$", re.IGNORECASE)
RE_PUBLISHER_ONLY = re.compile(r"\b(university press|springer|wiley|elsevier|routledge|sage|taylor\s*&\s*francis)\b", re.IGNORECASE)

def pick_title_from_text(text: str) -> str:
    """
    Choose a sensible title-like line from extracted text.
    Skips numeric-only lines, page headers, and publisher-only lines.
    """
    if not text:
        return ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for ln in lines[:35]:
        low = ln.lower()
        if RE_NUMERIC_LINE.match(ln):
            continue
        if len(ln) < 8:
            continue
        if len(ln) > 160:
            continue
        if "page " in low and any(ch.isdigit() for ch in low):
            continue
        if RE_PUBLISHER_ONLY.search(ln) and len(ln.split()) <= 6:
            continue
        return ln
    return lines[0] if lines else ""
PERSONAL_DOC_HINTS = {
    # ---- CV / Resume ----
    "curriculum vitae": ("PERSONAL", "WRITINGS", "CV_Resume"),
    "resume": ("PERSONAL", "WRITINGS", "CV_Resume"),
    "rÃ©sumÃ©": ("PERSONAL", "WRITINGS", "CV_Resume"),
    "cv": ("PERSONAL", "WRITINGS", "CV_Resume"),
    "experience professionnelle": ("PERSONAL", "WRITINGS", "CV_Resume"),
    "formation": ("PERSONAL", "WRITINGS", "CV_Resume"),
    "competences": ("PERSONAL", "WRITINGS", "CV_Resume"),
    "compÃ©tences": ("PERSONAL", "WRITINGS", "CV_Resume"),
    "references": ("PERSONAL", "WRITINGS", "CV_Resume"),
    "rÃ©fÃ©rences": ("PERSONAL", "WRITINGS", "CV_Resume"),

    # ---- Cover letters / applications ----
    "cover letter": ("PERSONAL", "WRITINGS", "Cover_Letters"),
    "dear hiring": ("PERSONAL", "WRITINGS", "Cover_Letters"),
    "dear sir": ("PERSONAL", "WRITINGS", "Cover_Letters"),
    "dear madam": ("PERSONAL", "WRITINGS", "Cover_Letters"),
    "sincerely": ("PERSONAL", "WRITINGS", "Cover_Letters"),
    "to whom it may concern": ("PERSONAL", "WRITINGS", "Cover_Letters"),
    "lettre de motivation": ("PERSONAL", "WRITINGS", "Cover_Letters"),
    "madame, monsieur": ("PERSONAL", "WRITINGS", "Cover_Letters"),
    "objet :": ("PERSONAL", "WRITINGS", "Cover_Letters"),
    "je vous prie d agreer": ("PERSONAL", "WRITINGS", "Cover_Letters"),
    "veuillez agreer": ("PERSONAL", "WRITINGS", "Cover_Letters"),

    "job application": ("PERSONAL", "WRITINGS", "Job_Applications"),
    "application": ("PERSONAL", "WRITINGS", "Job_Applications"),
    "i am writing to apply": ("PERSONAL", "WRITINGS", "Job_Applications"),
    "statement of interest": ("PERSONAL", "WRITINGS", "Job_Applications"),
    "candidature": ("PERSONAL", "WRITINGS", "Job_Applications"),
    "poste": ("PERSONAL", "WRITINGS", "Job_Applications"),

    # ---- Consulting / invoices ----
    "invoice": ("PERSONAL", "WRITINGS", "Consulting_Deliverables"),
    "statement of work": ("PERSONAL", "WRITINGS", "Consulting_Deliverables"),
    "facture": ("PERSONAL", "WRITINGS", "Consulting_Deliverables"),
    "bon de commande": ("PERSONAL", "WRITINGS", "Consulting_Deliverables"),
    "mandat": ("PERSONAL", "WRITINGS", "Consulting_Deliverables"),

    # ---- Publishing pipeline (contracts / releases / consent) ----
    "publishing agreement": ("PERSONAL", "WRITINGS", "Publishing_Pipeline\\Contracts"),
    "agreement": ("PERSONAL", "WRITINGS", "Publishing_Pipeline\\Contracts"),
    "contract": ("PERSONAL", "WRITINGS", "Publishing_Pipeline\\Contracts"),
    "license": ("PERSONAL", "WRITINGS", "Publishing_Pipeline\\Contracts"),
    "licence": ("PERSONAL", "WRITINGS", "Publishing_Pipeline\\Contracts"),
    "grant of rights": ("PERSONAL", "WRITINGS", "Publishing_Pipeline\\Contracts"),
    "rights granted": ("PERSONAL", "WRITINGS", "Publishing_Pipeline\\Contracts"),
    "governing law": ("PERSONAL", "WRITINGS", "Publishing_Pipeline\\Contracts"),
    "indemnif": ("PERSONAL", "WRITINGS", "Publishing_Pipeline\\Contracts"),
    "publisher": ("PERSONAL", "WRITINGS", "Publishing_Pipeline\\Contracts"),
    "publishing": ("PERSONAL", "WRITINGS", "Publishing_Pipeline\\Contracts"),

    "consent": ("PERSONAL", "WRITINGS", "Publishing_Pipeline\\Consent_Release"),
    "release form": ("PERSONAL", "WRITINGS", "Publishing_Pipeline\\Consent_Release"),
    "authorization": ("PERSONAL", "WRITINGS", "Publishing_Pipeline\\Consent_Release"),
    "authorisation": ("PERSONAL", "WRITINGS", "Publishing_Pipeline\\Consent_Release"),
    "permission to use": ("PERSONAL", "WRITINGS", "Publishing_Pipeline\\Consent_Release"),
    "image release": ("PERSONAL", "WRITINGS", "Publishing_Pipeline\\Consent_Release"),
    "consentement": ("PERSONAL", "WRITINGS", "Publishing_Pipeline\\Consent_Release"),
    "autorisation": ("PERSONAL", "WRITINGS", "Publishing_Pipeline\\Consent_Release"),
    "decharge": ("PERSONAL", "WRITINGS", "Publishing_Pipeline\\Consent_Release"),
    "dÃ©charge": ("PERSONAL", "WRITINGS", "Publishing_Pipeline\\Consent_Release"),
    "droit a l image": ("PERSONAL", "WRITINGS", "Publishing_Pipeline\\Consent_Release"),
    "droit Ã  l image": ("PERSONAL", "WRITINGS", "Publishing_Pipeline\\Consent_Release"),

    # ---- Taxes (keep high precision; add QC/CA + FR triggers) ----
    "canada revenue agency": ("PERSONAL", "Finance", "Taxes"),
    "agence du revenu du canada": ("PERSONAL", "Finance", "Taxes"),
    "revenu quebec": ("PERSONAL", "Finance", "Taxes"),
    "revenu quÃ©bec": ("PERSONAL", "Finance", "Taxes"),
    "agence du revenu": ("PERSONAL", "Finance", "Taxes"),
    "notice of assessment": ("PERSONAL", "Finance", "Taxes"),
    "avis de cotisation": ("PERSONAL", "Finance", "Taxes"),
    "declaration de revenus": ("PERSONAL", "Finance", "Taxes"),
    "dÃ©claration de revenus": ("PERSONAL", "Finance", "Taxes"),
    "t4": ("PERSONAL", "Finance", "Taxes"),
    "t4a": ("PERSONAL", "Finance", "Taxes"),
    "t5": ("PERSONAL", "Finance", "Taxes"),
    "t1": ("PERSONAL", "Finance", "Taxes"),
    "rl-1": ("PERSONAL", "Finance", "Taxes"),
    "rl-2": ("PERSONAL", "Finance", "Taxes"),
    "rl-31": ("PERSONAL", "Finance", "Taxes"),
    "releve 1": ("PERSONAL", "Finance", "Taxes"),
    "relevÃ© 1": ("PERSONAL", "Finance", "Taxes"),
    "irs": ("PERSONAL", "Finance", "Taxes"),
    "form 1040": ("PERSONAL", "Finance", "Taxes"),
    "w-2": ("PERSONAL", "Finance", "Taxes"),
    "social insurance number": ("PERSONAL", "Finance", "Taxes"),
    "numero d assurance sociale": ("PERSONAL", "Finance", "Taxes"),
    "numÃ©ro d assurance sociale": ("PERSONAL", "Finance", "Taxes"),
}
SCHOLAR_HINTS = {
    "abstract": 2,
    "keywords": 2,
    "references": 2,
    "bibliography": 2,
    "journal": 2,
    "issn": 2,
    "isbn": 2,
    "vol.": 1,
    "volume": 1,
    "issue": 1,
    "pp.": 1,
    "doi": 2,
}
RESEARCH_HINTS = {
    "introduction": 1,
    "method": 1,
    "methods": 1,
    "results": 1,
    "discussion": 1,
    "conclusion": 1,
    "literature review": 2,
}

CHAPTER_HINTS = {
    "chapter": 2,
    "edited by": 2,
    "in:": 1,
}

THESIS_HINTS = {
    "dissertation": 3,
    "thesis": 3,
    "submitted in partial fulfillment": 3,
    "doctor of philosophy": 2,
    "phd": 2,
}

CONF_HINTS = {
    "conference": 2,
    "proceedings": 2,
    "symposium": 2,
    "paper presented": 3,
    "presented at": 3,
}


def stamp() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")


def clean_filename(s: str) -> str:
    s = (s or "").strip()
    s = RE_WS.sub(" ", s)
    s = RE_INVALID.sub(" ", s)
    s = RE_WS.sub(" ", s).strip()
    if len(s) > 120:
        s = s[:120].rstrip()
    return s


def dedupe_path(p: Path) -> Path:
    if not p.exists():
        return p
    stem, suf = p.stem, p.suffix
    for i in range(2, 1000):
        cand = p.with_name(f"{stem}_{i:02d}{suf}")
        if not cand.exists():
            return cand
    raise RuntimeError(f"Too many duplicates for {p.name}")


def extract_text(pdf: Path, pages: int = 2) -> str:
    try:
        doc = fitz.open(pdf)  # MuPDF may print to stderr here
        try:
            n = min(pages, doc.page_count)
            out = []
            for i in range(n):
                out.append(doc.load_page(i).get_text("text") or "")
            return "\n".join(out)
        finally:
            doc.close()
    except Exception as e:
        # To identify the offender PDF, uncomment:
        print(f"[WARN] extract_text failed for: {pdf} :: {type(e).__name__}: {e}")
        return ""
def extract_meta_title(pdf: Path) -> str:
    try:
        doc = fitz.open(pdf)
        try:
            meta = doc.metadata or {}
            return (meta.get("title") or "").strip()
        finally:
            doc.close()
    except Exception as e:
        # To identify the offender PDF, uncomment:
        print(f"[WARN] extract_meta_title failed for: {pdf} :: {type(e).__name__}: {e}")
        return ""

# --- Review detection (explicit labels) ---
REVIEW_HINTS = {
    "book review": 5,
    "review essay": 5,
    "review article": 5,
    "essay review": 5,
    "recension": 5,
    "compte rendu": 5,
}

# --- Handbook / encyclopedia cues (strong) ---
HANDBOOK_HINTS = {
    "handbook of": 4,
    "the oxford handbook of": 5,
    "oxford handbook": 4,
    "handbooks online": 6,
    "printed from oxford handbooks online": 8,
    "encyclopedia": 4,
    "encyclopaedia": 4,
    "entry": 2,
}

# --- Book-level / monograph-ish cues ---
BOOK_FRONTMATTER_HINTS = {
    "isbn": 5,
    "cataloging-in-publication": 5,
    "cataloguing in publication": 5,
    "library of congress cataloging": 5,
    "all rights reserved": 2,
    "published by": 2,
    "includes bibliographical references": 3,
    "includes index": 2,
    "index": 1,
    "contents": 1
}

# --- Chapter cues (edited volumes / chapters) ---
CHAPTER_STRONG_HINTS = {
    "book title:": 6,
    "book editor": 6,
    "book editor(s)": 6,
    "edited by": 4,
    "sous la direction de": 5,
    "in:": 2,
    "chapter": 3,
    "chapitre": 4,
}


# --- Review detection (explicit labels) ---
REVIEW_HINTS = {
    "book review": 5,
    "review essay": 5,
    "review article": 5,
    "essay review": 5,
    "recension": 5,
    "compte rendu": 5,
}

# --- Handbook / encyclopedia cues (strong) ---
HANDBOOK_HINTS = {
    "handbook of": 4,
    "the oxford handbook of": 5,
    "oxford handbook": 4,
    "handbooks online": 6,
    "printed from oxford handbooks online": 8,
    "encyclopedia": 4,
    "encyclopaedia": 4,
    "entry": 2,
}

# --- Book-level / monograph-ish cues ---
BOOK_FRONTMATTER_HINTS = {
    "isbn": 5,
    "cataloging-in-publication": 5,
    "cataloguing in publication": 5,
    "library of congress cataloging": 5,
    "all rights reserved": 2,
    "published by": 2,
    "includes bibliographical references": 3,
    "includes index": 2,
    "index": 1,
    "contents": 1
}

# --- Chapter cues (edited volumes / chapters) ---
CHAPTER_STRONG_HINTS = {
    "book title:": 6,
    "book editor": 6,
    "book editor(s)": 6,
    "edited by": 4,
    "sous la direction de": 5,
    "in:": 2,
    "chapter": 3,
    "chapitre": 4,
}

def score_hits(text: str, table: Dict[str, int]) -> Tuple[int, List[str]]:
    t = norm(text)
    score = 0
    reasons = []
    for k, v in table.items():
        if norm(k) in t:
            score += v
            reasons.append(k)
    return score, reasons

def has_any(text: str, phrases: List[str]) -> bool:
    t = norm(text)
    return any(norm(p) in t for p in phrases if p)

def is_review(text: str) -> Tuple[bool, List[str]]:
    score, reasons = score_hits(text, REVIEW_HINTS)
    return score >= 5, reasons

def classify_personal_vs_scholar(text: str, identities: List[str]) -> Tuple[str, List[str]]:
    reasons = []
    tlow = norm(text)
    # Identity match (strong)
    for ident in identities:
        if ident and norm(ident) in tlow:
            reasons.append(f"identity:{ident}")
            return "PERSONAL", reasons

    # Personal admin/pro writing cues (strong)
    for k, target in PERSONAL_DOC_HINTS.items():
        if k in tlow:
            reasons.append(f"personal_hint:{k}")
            return "PERSONAL", reasons

    # Scholar cues
    scholar_score, scholar_reasons = score_hits(text, SCHOLAR_HINTS)
    if RE_DOI.search(text):
        scholar_score += 3
        scholar_reasons.append("doi")

    if scholar_score >= 3:
        reasons.extend([f"scholar_hint:{r}" for r in scholar_reasons])
        return "SCHOLAR", reasons

    # Unclear
    if len(text.strip()) < 80:
        reasons.append("low_text")
        return "UNCLEAR", reasons

    reasons.append("ambiguous")
    return "UNCLEAR", reasons


def classify_personal_subfolder(text: str) -> Tuple[str, str, List[str]]:
    """
    Returns (mid_bucket, leaf_folder, reasons)
    mid_bucket is one of: RESEARCH, WRITINGS, Finance, Admin
    """
    tlow = norm(text)
    reasons = []

    # Strong routing for personal admin/finance/pro docs
    for k, (top, mid, leaf) in PERSONAL_DOC_HINTS.items():
        if norm(k) in tlow:
            reasons.append(k)
            return mid, leaf, reasons

    # Otherwise choose RESEARCH vs WRITINGS
    thesis_score, th_r = score_hits(text, THESIS_HINTS)
    conf_score, c_r = score_hits(text, CONF_HINTS)
    chapter_score, ch_r = score_hits(text, CHAPTER_HINTS)
    research_score, r_r = score_hits(text, RESEARCH_HINTS)

    # Thesis
    if thesis_score >= 3:
        return "RESEARCH", "Thesis_Dissertation", th_r

    # Conference
    if conf_score >= 3:
        return "RESEARCH", "Conference", c_r

    # Chapter
    if chapter_score >= 3:
        return "RESEARCH", "Book_Chapters", ch_r

    # Research paper signals
    if research_score >= 3 or RE_DOI.search(text):
        return "RESEARCH", "Papers", r_r + (["doi"] if RE_DOI.search(text) else [])

    # Default to WRITINGS misc
    return "WRITINGS", "Misc", ["default_writings"]




def classify_research_bucket(text: str) -> Tuple[str, List[str]]:
    """
    Returns (research_folder_name, reasons)
    Folders (in your requested order):
      - Thesis\\PhD
      - Thesis\\Masters
      - Books_and_Chapters
      - Handbook_or_Encyclopedia
      - Articles_or_Full_Issues
    Reviews are rerouted to the folder that matches what they are reviewing.
    """
    reasons: List[str] = []
    t = norm(text)

    # 1) Thesis split (strong + early precedence)
    phd_signals = ["dissertation", "doctor of philosophy", "phd", "doctorat", "these", "thÃ¨se", "thesis"]
    masters_signals = ["master", "maitrise", "maÃ®trise", "memoire", "mÃ©moire"]

    thesis_score, thesis_reasons = score_hits(text, THESIS_HINTS)
    if thesis_score >= 3 or has_any(text, phd_signals + masters_signals):
        if has_any(text, ["dissertation", "doctor of philosophy", "phd", "doctorat", "these", "thÃ¨se", "thesis"]):
            return r"Thesis\PhD", thesis_reasons + ["phd_signal"]
        if has_any(text, ["memoire", "mÃ©moire", "maitrise", "maÃ®trise", "master"]):
            return r"Thesis\Masters", thesis_reasons + ["masters_signal"]
        return r"Thesis\PhD", thesis_reasons + ["thesis_default_phd"]

    # 2) Review reroute
    review_flag, review_reasons = is_review(text)
    if review_flag:
        hb_score, hb_reasons = score_hits(text, HANDBOOK_HINTS)
        if hb_score >= 5:
            return "Handbook_or_Encyclopedia", ["review"] + review_reasons + hb_reasons

        book_score, book_reasons = score_hits(text, BOOK_FRONTMATTER_HINTS)
        if book_score >= 5 or "isbn" in t:
            return "Books_and_Chapters", ["review"] + review_reasons + book_reasons

        return "Articles_or_Full_Issues", ["review"] + review_reasons + ["review_default_journals"]

    # 3) Handbook/Encyclopedia
    hb_score, hb_reasons = score_hits(text, HANDBOOK_HINTS)
    if hb_score >= 5:
        return "Handbook_or_Encyclopedia", hb_reasons

    # 4) Books_and_Chapters (chapters OR monographs)
    ch_score, ch_reasons = score_hits(text, CHAPTER_STRONG_HINTS)
    if ch_score >= 6:
        return "Books_and_Chapters", ch_reasons

    book_score, book_reasons = score_hits(text, BOOK_FRONTMATTER_HINTS)
    if book_score >= 6:
        return "Books_and_Chapters", book_reasons

    # 5) Default: journal articles + full issues lumped together
    return "Articles_or_Full_Issues", ["default_journals"]
def classify_scholar_subfolder(text: str) -> Tuple[str, List[str]]:
    tlow = norm(text)
    reasons = []
    chapter_score, ch_r = score_hits(text, CHAPTER_HINTS)
    conf_score, c_r = score_hits(text, CONF_HINTS)

    if conf_score >= 3:
        return "Conference_Proceedings", c_r

    if chapter_score >= 3:
        return "Book_Chapters", ch_r

    # Article if DOI or strong article cues
    scholar_score, s_r = score_hits(text, SCHOLAR_HINTS)
    if RE_DOI.search(text) or scholar_score >= 4:
        reasons = s_r + (["doi"] if RE_DOI.search(text) else [])
        return "Articles", reasons

    return "Misc", ["default_scholar"]


def build_target(library_root: Path, top: str, mid: str, leaf: str, filename: str) -> Path:
    if top == "PERSONAL":
        return library_root / "PERSONAL_ADMIN" / mid / leaf / filename
    if top == "SCHOLAR":
        return library_root / "RESEARCH" / leaf / filename
    return library_root / "UNCLEAR" / leaf / filename
def try_ocr_pdf(src_pdf: Path, ocr_out: Path) -> bool:
    """
    Optional OCR: prefers project venv ocrmypdf.exe, else PATH.
    """
    try:
        import shutil, subprocess
        exe = shutil.which("ocrmypdf")
        if exe is None:
            here = Path(__file__).resolve().parent
            cand = here / ".venv" / "Scripts" / "ocrmypdf.exe"
            exe = str(cand) if cand.exists() else None
        if exe is None:
            return False

        ocr_out.parent.mkdir(parents=True, exist_ok=True)
        cmd = [exe, "--skip-text", "--force-ocr", str(src_pdf), str(ocr_out)]
        p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return p.returncode == 0 and ocr_out.exists()
    except Exception:
        return False
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Folder to scan for PDFs")
    ap.add_argument("--library-root", required=True, help="Library root for sorted output")
    ap.add_argument("--identity", action="append", default=[], help="Your identity strings (repeatable)")
    ap.add_argument("--apply", action="store_true", help="Actually rename/move (default is dry-run)")
    ap.add_argument("--recursive", action="store_true", help="Scan subfolders under --root")
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    lib = Path(args.library_root).expanduser().resolve()
    lib.mkdir(parents=True, exist_ok=True)

    log_dir = Path(__file__).resolve().parent / "LOGS"
    log_dir.mkdir(parents=True, exist_ok=True)

    run_id = stamp()
    log_csv = log_dir / f"RUN_{run_id}.csv"

    pattern = "**/*.pdf" if args.recursive else "*.pdf"
    pdfs = sorted(root.glob(pattern))

    rows = []
    moved = 0
    skipped = 0

    for pdf in pdfs:
        text = extract_text(pdf, pages=2)
        # Early OCR: if extracted text is weak, OCR to cache then re-extract
        if len(text.strip()) < OCR_MIN_TEXT:
            ocr_cache = Path(args.library_root) / "_OCR_CACHE"
            ocr_out = ocr_cache / pdf.name
            if try_ocr_pdf(pdf, ocr_out):
                text2 = extract_text(ocr_out, pages=2)
                if text2 and len(text2.strip()) > len(text.strip()):
                    text = text2
        meta_title = extract_meta_title(pdf)
        title = meta_title if meta_title else ""

        # fallback: first non-empty line
        # fallback: first non-empty line
        if not title:
            title = pick_title_from_text(text)

        title = clean_filename(title) or clean_filename(pdf.stem)
        new_name = f"{title}.pdf"

        top, auth_reasons = classify_personal_vs_scholar(text, args.identity)

        if top == "PERSONAL":
            mid, leaf, type_reasons = classify_personal_subfolder(text)
            target = build_target(lib, "PERSONAL", mid, leaf, new_name)
        elif top == "SCHOLAR":
            leaf, type_reasons = classify_research_bucket(text)
            target = build_target(lib, "SCHOLAR", "", leaf, new_name)
        else:
            # UNCLEAR routing
            if len(text.strip()) < 80:
                leaf = "Scans_OCR_Needed"
                type_reasons = ["low_text"]
            else:
                leaf = "Needs_Review"
                type_reasons = ["ambiguous"]
            target = lib / "UNCLEAR" / leaf / new_name

        target.parent.mkdir(parents=True, exist_ok=True)
        target = dedupe_path(target)

        action = "DRY_RUN"
        err = ""
        before = str(pdf)
        after = str(target)

        if args.apply:
            try:
                pdf.replace(target)  # move + rename
                moved += 1
                action = "MOVED"
            except Exception as e:
                skipped += 1
                action = "ERROR"
                err = f"{type(e).__name__}: {e}"

        print(f"[PROGRESS] {pdf.name} -> {target}", flush=True)


        rows.append({
            "action": action,
            "before": before,
            "after": after,
            "top_bucket": top,
            "reasons_authorship": ";".join(auth_reasons),
            "reasons_type": ";".join(type_reasons),
            "meta_title": meta_title,
            "error": err,
        })

    with log_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [
            "action","before","after","top_bucket","reasons_authorship","reasons_type","meta_title","error"
        ])
        w.writeheader()
        if rows:
            w.writerows(rows)

    print(f"Root: {root}")
    print(f"Library: {lib}")
    print(f"Mode: {'APPLY' if args.apply else 'DRY_RUN'}")
    print(f"PDFs found: {len(pdfs)}")
    print(f"Moved: {moved}")
    print(f"Skipped/Errors: {skipped}")
    print(f"Log: {log_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())









