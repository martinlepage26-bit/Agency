from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable
from xml.etree import ElementTree as ET

import fitz


try:
    fitz.TOOLS.mupdf_display_errors(False)
    fitz.TOOLS.mupdf_display_warnings(False)
except Exception:
    pass


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md"}
DEFAULT_SOURCE_DIRS = ("INBOX", "LEGACY_INBOX")
DEFAULT_OUTPUT_DIR = "SORTED_LIBRARY_V2"
DEFAULT_QUARANTINE_DIR = "QUARANTINE/V2"
DEFAULT_REPORT_DIR = "REPORTS_V2"
EXCLUDED_DIR_NAMES = {
    ".venv",
    "__pycache__",
    "LOGS",
    "REPORTS_V2",
    "SORTED_LIBRARY_V2",
    "TEST_LIBRARY",
    "TEST_LIBRARY_V2",
    "TOOLS",
}
REFERENCE_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "dans",
    "pour",
    "les",
    "des",
    "une",
    "sur",
    "from",
    "into",
    "de",
    "du",
    "la",
    "le",
    "and",
    "et",
    "que",
    "this",
    "that",
    "these",
    "those",
    "book",
    "review",
    "article",
    "report",
    "chapter",
}
RULES_EXAMPLE_NAME = "lotus_rules.example.txt"
REVISION_SENSITIVE_TYPES = {
    "cover_letter",
    "job_application",
    "correspondence",
    "legal_or_contract",
    "cv_resume",
    "screenplay",
    "manuscript",
    "notes_or_journal",
}
DEFAULT_IDENTITIES = [
    "Martin Lepage",
    "Martin LePage",
    "Martin L. Lepage",
    "M. Lepage",
    "Nathon Lee Imeson",
    "Nathon Imeson",
]
MONTHS = {
    "jan": 1,
    "january": 1,
    "janvier": 1,
    "feb": 2,
    "february": 2,
    "fevrier": 2,
    "fevrier.": 2,
    "fevr": 2,
    "fevrier": 2,
    "fevrier": 2,
    "mar": 3,
    "march": 3,
    "mars": 3,
    "apr": 4,
    "april": 4,
    "avr": 4,
    "avril": 4,
    "may": 5,
    "mai": 5,
    "jun": 6,
    "june": 6,
    "juin": 6,
    "jul": 7,
    "july": 7,
    "juillet": 7,
    "aug": 8,
    "august": 8,
    "aout": 8,
    "sept": 9,
    "sep": 9,
    "september": 9,
    "septembre": 9,
    "oct": 10,
    "october": 10,
    "octobre": 10,
    "nov": 11,
    "november": 11,
    "novembre": 11,
    "dec": 12,
    "december": 12,
    "decembre": 12,
}
DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(19\d{2}|20[0-3]\d)\b")
HASH_SUFFIX_RE = re.compile(r"__([0-9A-F]{8})$", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[\w.\-+]+@[\w.\-]+\.\w+\b", re.IGNORECASE)
DATE_SLASH_RE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](19\d{2}|20[0-3]\d)\b")
DATE_LONG_RE = re.compile(
    r"\b(\d{1,2})\s+([A-Za-zÀ-ÿ]+)\s+(19\d{2}|20[0-3]\d)\b",
    re.IGNORECASE,
)
ISO_DATE_RE = re.compile(r"\b(19\d{2}|20[0-3]\d)-(\d{2})-(\d{2})\b")
ISBN_RE = re.compile(r"\b97[89][-\s]?\d[-\s]?\d{2,5}[-\s]?\d{2,7}[-\s]?\d{1,7}[-\s]?\d\b")
NAME_RE = re.compile(
    r"^(?:[A-ZÀ-Ý][a-zà-ÿ'`.-]+|[A-ZÀ-Ý]\.)"
    r"(?:\s+(?:[A-ZÀ-Ý][a-zà-ÿ'`.-]+|[A-ZÀ-Ý]\.)){1,4}$"
)
QUOTE_TITLE_RE = re.compile(r"[\"“«](.+?)[\"”»]")
SCENE_HEADING_RE = re.compile(r"^(?:int|ext)\.?[\s./-]+", re.IGNORECASE)
PAGE_SPAN_RE = re.compile(r"\bp\.?\s*\d+\s*[-–]\s*\d+\b", re.IGNORECASE)
AUTHOR_YEAR_LINE_RE = re.compile(r"^(.+?)\.\s*(19\d{2}|20[0-3]\d)\b")


TYPE_PRIORITY = {
    "cv_resume": 10,
    "cover_letter": 14,
    "job_application": 13,
    "recommendation_letter": 12,
    "tax_or_finance": 11,
    "statement_or_bill": 11,
    "legal_or_contract": 12,
    "correspondence": 7,
    "journal_article": 10,
    "book_chapter": 12,
    "book_or_monograph": 9,
    "thesis_or_dissertation": 11,
    "conference_paper": 10,
    "review": 13,
    "bibliography": 12,
    "report": 9,
    "audit_or_assessment": 10,
    "policy_or_guidance": 8,
    "screenplay": 12,
    "manuscript": 8,
    "notes_or_journal": 7,
    "unclear": 0,
    "ocr_needed": 0,
}


TYPE_RULES = {
    "cv_resume": {
        "category": "PERSONAL_ADMIN",
        "patterns": {
            "curriculum vitae": 12,
            "resume": 12,
            "cv ": 7,
            "academic curriculum vitae": 14,
            "experience professionnelle": 8,
            "references": 3,
        },
    },
    "cover_letter": {
        "category": "PERSONAL_ADMIN",
        "patterns": {
            "cover letter": 14,
            "lettre de motivation": 14,
            "madame, monsieur": 8,
            "to whom it may concern": 10,
            "dear hiring": 10,
            "dear committee": 10,
        },
    },
    "job_application": {
        "category": "PERSONAL_ADMIN",
        "patterns": {
            "job application": 12,
            "statement of interest": 10,
            "candidature": 10,
            "application for": 8,
            "poste": 3,
        },
    },
    "recommendation_letter": {
        "category": "PERSONAL_ADMIN",
        "patterns": {
            "recommendation letter": 14,
            "letter of recommendation": 14,
            "reference letter": 12,
            "lettre de recommandation": 14,
        },
    },
    "tax_or_finance": {
        "category": "PERSONAL_ADMIN",
        "patterns": {
            "canada revenue agency": 14,
            "agence du revenu du canada": 14,
            "revenu quebec": 14,
            "revenu quebec": 14,
            "notice of assessment": 12,
            "avis de cotisation": 12,
            "tax": 6,
            "t4": 10,
            "t4a": 10,
            "rl-1": 10,
            "releve 1": 10,
            "declaration de revenus": 12,
        },
    },
    "statement_or_bill": {
        "category": "PERSONAL_ADMIN",
        "patterns": {
            "statement": 8,
            "billing": 8,
            "invoice": 10,
            "facture": 10,
            "hydro quebec": 16,
            "mon espace client": 12,
            "numero de confirmation": 7,
            "recapitulatif": 7,
            "adresse": 3,
        },
    },
    "legal_or_contract": {
        "category": "PERSONAL_ADMIN",
        "patterns": {
            "agreement": 8,
            "contract": 10,
            "consent": 7,
            "release form": 10,
            "authorization": 7,
            "authorisation": 7,
            "indemnif": 7,
            "governing law": 9,
            "terms and conditions": 8,
            "court of": 8,
        },
    },
    "correspondence": {
        "category": "PERSONAL_ADMIN",
        "patterns": {
            "dear ": 7,
            "sincerely": 7,
            "cordially": 7,
            "bonjour": 6,
            "merci": 3,
            "re:": 5,
            "objet:": 5,
        },
    },
    "journal_article": {
        "category": "SCHOLAR",
        "patterns": {
            "abstract": 6,
            "keywords": 6,
            "references": 6,
            "bibliography": 5,
            "journal": 5,
            "issn": 4,
            "vol.": 4,
            "volume": 3,
            "issue": 3,
            "peer review": 3,
            "doi": 8,
        },
    },
    "book_chapter": {
        "category": "SCHOLAR",
        "patterns": {
            "chapter": 8,
            "chapitre": 8,
            "edited by": 8,
            "sous la direction de": 9,
            "book title": 10,
        },
    },
    "book_or_monograph": {
        "category": "SCHOLAR",
        "patterns": {
            "isbn": 10,
            "contents": 4,
            "all rights reserved": 5,
            "published by": 5,
            "introduction": 2,
            "index": 3,
            "cataloging-in-publication": 9,
        },
    },
    "thesis_or_dissertation": {
        "category": "SCHOLAR",
        "patterns": {
            "dissertation": 14,
            "thesis": 12,
            "these de doctorat": 16,
            "memoire de maitrise": 16,
            "plan de memoire": 12,
            "these": 4,
            "memoire": 4,
            "doctor of philosophy": 14,
            "submitted in partial fulfillment": 12,
            "maitrise": 12,
            "master of arts": 10,
        },
    },
    "conference_paper": {
        "category": "SCHOLAR",
        "patterns": {
            "conference": 10,
            "proceedings": 10,
            "symposium": 8,
            "paper presented": 10,
            "presented at": 10,
            "colloque": 10,
        },
    },
    "review": {
        "category": "SCHOLAR",
        "patterns": {
            "book review": 14,
            "review essay": 12,
            "review article": 12,
            "compte rendu": 14,
            "recension": 14,
        },
    },
    "bibliography": {
        "category": "SCHOLAR",
        "patterns": {
            "bibliography": 16,
            "works cited": 8,
            "references only": 8,
            "master bibliography": 16,
        },
    },
    "report": {
        "category": "PROFESSIONAL",
        "patterns": {
            "report": 10,
            "annual report": 13,
            "final report": 12,
            "executive summary": 5,
            "findings": 5,
            "assessment": 8,
            "evaluation": 8,
        },
    },
    "audit_or_assessment": {
        "category": "PROFESSIONAL",
        "patterns": {
            "audit report": 16,
            "audit": 9,
            "readiness": 9,
            "threat model": 12,
            "risk assessment": 12,
            "compliance": 8,
            "governance": 6,
        },
    },
    "policy_or_guidance": {
        "category": "PROFESSIONAL",
        "patterns": {
            "policy": 10,
            "guidance": 10,
            "framework": 8,
            "standard": 7,
            "protocol": 7,
            "requirements": 6,
            "specification": 8,
        },
    },
    "screenplay": {
        "category": "CREATIVE",
        "patterns": {
            "written by": 14,
            "fade in": 14,
            "screenplay": 14,
            "pilot script": 14,
            "act i": 6,
        },
    },
    "manuscript": {
        "category": "CREATIVE",
        "patterns": {
            "chapter 1": 8,
            "chapter one": 8,
            "field manual": 8,
            "draft": 5,
            "novel": 7,
            "poem": 6,
            "manuscript": 10,
        },
    },
    "notes_or_journal": {
        "category": "CREATIVE",
        "patterns": {
            "notes": 6,
            "journal": 5,
            "reflection": 6,
            "memo": 5,
            "freewrite": 6,
            "outline": 5,
        },
    },
}


@dataclass
class ExtractionResult:
    raw_text: str = ""
    text_preview: str = ""
    page_count: int | None = None
    meta_title: str = ""
    meta_author: str = ""
    meta_subject: str = ""
    meta_keywords: str = ""
    created: str = ""
    modified: str = ""
    ocr_used: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass
class DocumentRecord:
    source_path: Path
    source_root: Path
    extension: str
    size_bytes: int
    sha256: str
    modified_iso: str
    extraction: ExtractionResult
    language: str = "unknown"
    title: str = ""
    title_source: str = ""
    authors: list[str] = field(default_factory=list)
    author_source: str = ""
    year: str = ""
    date_iso: str = ""
    date_source: str = ""
    doi: str = ""
    isbn: str = ""
    doc_type: str = "unclear"
    category: str = "UNCLEAR"
    type_confidence: int = 0
    reasoning: list[str] = field(default_factory=list)
    duplicate_status: str = "keep"
    duplicate_reason: str = ""
    duplicate_group: str = ""
    tags: list[str] = field(default_factory=list)
    matched_rules: list[str] = field(default_factory=list)
    filename_template: str = ""
    planned_destination: Path | None = None
    action: str = "SCANNED"

    @property
    def relative_source(self) -> str:
        return str(self.source_path.relative_to(self.source_root))

    @property
    def primary_author(self) -> str:
        return self.authors[0] if self.authors else ""

    @property
    def author_key(self) -> str:
        author = self.primary_author
        if not author:
            return ""
        parts = [token for token in normalize_for_match(author).split() if token]
        return parts[-1] if parts else ""

    def filename_stub(self) -> str:
        if self.filename_template:
            rendered = render_filename_template(self, self.filename_template)
            if rendered:
                return sanitize_filename_component(rendered, max_len=140)
        year_part = self.year or "Undated"
        author_part = sanitize_filename_component(self.author_key or self.primary_author or "UnknownAuthor", max_len=28)
        title_part = sanitize_filename_component(self.title or fallback_title_from_filename(self.source_path), max_len=90)
        type_part = sanitize_filename_component(self.doc_type, max_len=24)
        parts = [year_part]
        if author_part:
            parts.append(author_part)
        if title_part:
            parts.append(title_part)
        if type_part and type_part != "unclear":
            parts.append(type_part)
        return " - ".join(parts)

    def to_row(self) -> dict[str, str]:
        return {
            "source_path": str(self.source_path),
            "source_root": str(self.source_root),
            "relative_source": self.relative_source,
            "extension": self.extension,
            "size_bytes": str(self.size_bytes),
            "sha256": self.sha256,
            "modified_iso": self.modified_iso,
            "page_count": str(self.extraction.page_count or ""),
            "language": self.language,
            "title": self.title,
            "title_source": self.title_source,
            "authors": "; ".join(self.authors),
            "author_source": self.author_source,
            "year": self.year,
            "date_iso": self.date_iso,
            "date_source": self.date_source,
            "doi": self.doi,
            "isbn": self.isbn,
            "doc_type": self.doc_type,
            "category": self.category,
            "type_confidence": str(self.type_confidence),
            "duplicate_status": self.duplicate_status,
            "duplicate_reason": self.duplicate_reason,
            "duplicate_group": self.duplicate_group,
            "tags": "; ".join(self.tags),
            "matched_rules": "; ".join(self.matched_rules),
            "filename_template": self.filename_template,
            "planned_destination": str(self.planned_destination or ""),
            "action": self.action,
            "meta_title": self.extraction.meta_title,
            "meta_author": self.extraction.meta_author,
            "created": self.extraction.created,
            "modified": self.extraction.modified,
            "ocr_used": str(self.extraction.ocr_used),
            "reasoning": "; ".join(self.reasoning + self.extraction.notes),
        }


@dataclass
class PlainEnglishRule:
    raw_line: str
    action: str
    phrase: str
    category: str = ""
    doc_type: str = ""
    tags: list[str] = field(default_factory=list)
    template: str = ""


def normalize_for_match(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[_\-.]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_compact(text: str) -> str:
    normalized = normalize_for_match(text)
    tokens = re.findall(r"[a-z0-9]+", normalized)
    return " ".join(tokens)


def contains_compact_phrase(compact_text: str, pattern: str) -> bool:
    compact_pattern = normalize_compact(pattern)
    if not compact_pattern:
        return False
    return f" {compact_pattern} " in f" {compact_text} "


def ascii_fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in text if ord(ch) < 128 and not unicodedata.combining(ch))


def sanitize_filename_component(text: str, max_len: int = 80) -> str:
    text = ascii_fold(text)
    text = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" ._-")
    text = text or "Untitled"
    if len(text) > max_len:
        text = text[:max_len].rstrip(" ._-")
    return text


def significant_tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", normalize_compact(text))
        if len(token) >= 4 and token not in REFERENCE_STOPWORDS
    }


def record_match_text(record: DocumentRecord) -> str:
    return normalize_compact(
        "\n".join(
            [
                record.title,
                fallback_title_from_filename(record.source_path),
                " ".join(record.authors),
                " ".join(record.tags),
                record.doc_type,
                record.category,
                record.extraction.meta_title,
                record.extraction.meta_subject,
                record.extraction.meta_keywords,
                record.extraction.raw_text[:12000],
            ]
        )
    )


def semantic_search_score(record: DocumentRecord, query: str) -> int:
    query = query.strip()
    if not query:
        return 0
    compact_query = normalize_compact(query)
    query_tokens = significant_tokens(query)
    if not compact_query and not query_tokens:
        return 0

    title_compact = normalize_compact(record.title)
    author_compact = normalize_compact(" ".join(record.authors))
    tag_compact = normalize_compact(" ".join(record.tags))
    match_text = record_match_text(record)
    match_tokens = significant_tokens(match_text)

    score = 0
    if compact_query and compact_query in title_compact:
        score += 18
    if compact_query and compact_query in author_compact:
        score += 12
    if compact_query and compact_query in tag_compact:
        score += 10
    if compact_query and compact_query in match_text:
        score += 8

    shared = query_tokens & match_tokens
    score += min(len(shared) * 4, 24)

    if record.year and record.year in query:
        score += 4
    if record.language and record.language in compact_query:
        score += 3
    if normalize_compact(record.category) in compact_query or normalize_compact(record.doc_type) in compact_query:
        score += 6
    return score


def search_records(records: list[DocumentRecord], query: str) -> list[tuple[DocumentRecord, int]]:
    scored = [(record, semantic_search_score(record, query)) for record in records]
    return sorted(
        [(record, score) for record, score in scored if score > 0],
        key=lambda item: (-item[1], item[0].title.lower(), item[0].relative_source.lower()),
    )


def clean_candidate_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "").strip(" |-_")
    value = re.sub(r"^\d{1,4}\s+(?=[A-Za-zÀ-ÿ])", "", value)
    value = value.strip(" .;:-|")
    return value


def normalize_author_case(value: str) -> str:
    words: list[str] = []
    for word in re.split(r"(\s+)", value):
        if not word or word.isspace():
            words.append(word)
            continue
        if word.isupper() or word.islower():
            words.append(word.title())
        else:
            words.append(word)
    return "".join(words)


def generate_tags(record: DocumentRecord) -> list[str]:
    tags: list[str] = []
    for value in (record.category, record.doc_type, record.language):
        if value and value not in {"UNCLEAR", "unclear", "unknown"}:
            tags.append(normalize_compact(value).replace(" ", "_"))
    if record.year:
        tags.append(record.year)
    if record.doi:
        tags.append("has_doi")
    if record.isbn:
        tags.append("has_isbn")
    if record.duplicate_status != "keep":
        tags.append(record.duplicate_status)
    if record.extraction.ocr_used:
        tags.append("ocr")
    if record.primary_author:
        tags.append(sanitize_filename_component(record.primary_author, max_len=32).replace(" ", "_").lower())

    topical = significant_tokens(
        " ".join(
            [
                record.title,
                record.extraction.meta_subject,
                record.extraction.meta_keywords,
                record.extraction.raw_text[:4000],
            ]
        )
    )
    for token in sorted(topical)[:8]:
        if token not in {"abstract", "references", "introduction", "chapter"}:
            tags.append(token)

    deduped: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        tag = tag.strip().replace(" ", "_")
        if tag and tag not in seen:
            seen.add(tag)
            deduped.append(tag)
    return deduped[:16]


def render_filename_template(record: DocumentRecord, template: str) -> str:
    mapping = {
        "year": record.year or "Undated",
        "author": record.author_key or sanitize_filename_component(record.primary_author or "UnknownAuthor", max_len=32),
        "title": sanitize_filename_component(record.title or fallback_title_from_filename(record.source_path), max_len=90),
        "doc_type": record.doc_type,
        "category": record.category,
        "language": record.language,
    }
    rendered = template
    for key, value in mapping.items():
        rendered = rendered.replace(f"{{{key}}}", value)
    return rendered


def parse_plain_english_rule(line: str) -> PlainEnglishRule | None:
    text = line.strip()
    if not text or text.startswith("#"):
        return None

    move_match = re.match(
        r'^move all files containing "([^"]+)" to ([A-Za-z0-9_]+)(?:/([A-Za-z0-9_]+))?$',
        text,
        flags=re.IGNORECASE,
    )
    if move_match:
        category = move_match.group(2) or ""
        doc_type = move_match.group(3) or ""
        return PlainEnglishRule(
            raw_line=text,
            action="move",
            phrase=move_match.group(1),
            category=category.upper() if category else "",
            doc_type=doc_type.lower() if doc_type else "",
        )

    tag_match = re.match(
        r'^tag all files containing "([^"]+)" with ([A-Za-z0-9_, -]+)$',
        text,
        flags=re.IGNORECASE,
    )
    if tag_match:
        tags = [normalize_compact(tag).replace(" ", "_") for tag in tag_match.group(2).split(",") if tag.strip()]
        return PlainEnglishRule(raw_line=text, action="tag", phrase=tag_match.group(1), tags=tags)

    rename_match = re.match(
        r'^rename all files containing "([^"]+)" as (.+)$',
        text,
        flags=re.IGNORECASE,
    )
    if rename_match:
        return PlainEnglishRule(
            raw_line=text,
            action="rename",
            phrase=rename_match.group(1),
            template=rename_match.group(2).strip(),
        )
    return None


def load_plain_english_rules(path: Path | None) -> list[PlainEnglishRule]:
    if path is None or not path.exists():
        return []
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="latin-1", errors="replace")
    rules: list[PlainEnglishRule] = []
    for line in content.splitlines():
        rule = parse_plain_english_rule(line)
        if rule:
            rules.append(rule)
    return rules


def apply_plain_english_rules(records: list[DocumentRecord], rules: list[PlainEnglishRule]) -> None:
    if not rules:
        return
    for record in records:
        compact_text = record_match_text(record)
        for rule in rules:
            if not contains_compact_phrase(compact_text, rule.phrase):
                continue
            record.matched_rules.append(rule.raw_line)
            if rule.action == "move":
                if rule.category:
                    record.category = rule.category
                if rule.doc_type:
                    record.doc_type = rule.doc_type
                record.type_confidence = max(record.type_confidence, 95)
                record.reasoning.append(f"rule_move:{rule.phrase}")
            elif rule.action == "tag":
                record.tags.extend(rule.tags)
                record.reasoning.append(f"rule_tag:{rule.phrase}")
            elif rule.action == "rename":
                record.filename_template = rule.template
                record.reasoning.append(f"rule_rename:{rule.phrase}")
        if record.tags:
            deduped: list[str] = []
            seen: set[str] = set()
            for tag in record.tags:
                if tag and tag not in seen:
                    seen.add(tag)
                    deduped.append(tag)
            record.tags = deduped[:20]


def ensure_unique_path(path: Path, used_paths: set[Path]) -> Path:
    candidate = path
    counter = 2
    while candidate in used_paths or candidate.exists():
        candidate = path.with_name(f"{path.stem} [{counter}]{path.suffix}")
        counter += 1
    used_paths.add(candidate)
    return candidate


def timestamp() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")


def parse_pdf_date(value: str) -> str:
    if not value:
        return ""
    match = re.match(r"D:(\d{4})(\d{2})?(\d{2})?", value)
    if not match:
        return ""
    year = match.group(1)
    month = match.group(2) or "01"
    day = match.group(3) or "01"
    return f"{year}-{month}-{day}"


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_text_file(path: Path) -> str:
    encodings = ["utf-8-sig", "utf-16", "utf-16le", "utf-16be", "utf-8", "cp1252", "latin-1"]
    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="latin-1", errors="replace")


def fallback_title_from_filename(path: Path) -> str:
    stem = HASH_SUFFIX_RE.sub("", path.stem)
    stem = stem.replace("_", " ").replace(".", " ")
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem


def discover_files(source_roots: list[Path], recursive: bool, limit: int | None) -> list[tuple[Path, Path]]:
    discovered: list[tuple[Path, Path]] = []
    for source_root in source_roots:
        if not source_root.exists():
            continue
        if source_root.is_file():
            if source_root.suffix.lower() in SUPPORTED_EXTENSIONS and not any(
                part in EXCLUDED_DIR_NAMES for part in source_root.parts
            ):
                discovered.append((source_root.parent, source_root))
            if limit is not None and len(discovered) >= limit:
                return discovered
            continue
        iterator: Iterable[Path]
        iterator = source_root.rglob("*") if recursive else source_root.glob("*")
        for path in sorted(iterator):
            if not path.is_file():
                continue
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
                continue
            discovered.append((source_root, path))
            if limit is not None and len(discovered) >= limit:
                return discovered
    return discovered


def extract_pdf_text(path: Path, max_pages: int) -> ExtractionResult:
    result = ExtractionResult()
    try:
        with fitz.open(path) as doc:
            result.page_count = doc.page_count
            metadata = doc.metadata or {}
            result.meta_title = (metadata.get("title") or "").strip()
            result.meta_author = (metadata.get("author") or "").strip()
            result.meta_subject = (metadata.get("subject") or "").strip()
            result.meta_keywords = (metadata.get("keywords") or "").strip()
            result.created = parse_pdf_date(metadata.get("creationDate") or "")
            result.modified = parse_pdf_date(metadata.get("modDate") or "")
            chunks: list[str] = []
            for page_index in range(min(max_pages, doc.page_count)):
                page = doc.load_page(page_index)
                text = page.get_text("text", sort=True) or ""
                if not text.strip():
                    text = page.get_text("blocks") or ""
                    if isinstance(text, list):
                        text = "\n".join(block[4] for block in text if len(block) >= 5)
                chunks.append(text)
            result.raw_text = "\n".join(chunks).strip()
    except Exception as exc:
        result.notes.append(f"pdf_extract_failed:{type(exc).__name__}")
    result.text_preview = result.raw_text[:12000]
    return result


def find_ocrmypdf_executable(script_dir: Path) -> str | None:
    local_exe = script_dir / ".venv" / "Scripts" / "ocrmypdf.exe"
    if os.name == "nt" and local_exe.exists():
        return str(local_exe)
    found = shutil.which("ocrmypdf")
    return found


def attempt_ocr(path: Path, script_dir: Path, max_pages: int) -> ExtractionResult | None:
    executable = find_ocrmypdf_executable(script_dir)
    if not executable:
        return None
    with tempfile.TemporaryDirectory(prefix="sorter_ocr_") as temp_dir:
        temp_dir_path = Path(temp_dir)
        ocr_pdf = temp_dir_path / f"{path.stem}_ocr.pdf"
        try:
            completed = subprocess.run(
                [executable, "--skip-text", "--force-ocr", str(path), str(ocr_pdf)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=240,
                check=False,
            )
        except Exception:
            return None
        if completed.returncode != 0 or not ocr_pdf.exists():
            return None
        result = extract_pdf_text(ocr_pdf, max_pages=max_pages)
        result.ocr_used = True
        result.notes.append("ocrmypdf")
        return result


def extract_docx_text(path: Path) -> ExtractionResult:
    result = ExtractionResult()
    namespaces = {
        "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
        "dc": "http://purl.org/dc/elements/1.1/",
        "dcterms": "http://purl.org/dc/terms/",
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    }
    try:
        with zipfile.ZipFile(path) as archive:
            if "docProps/core.xml" in archive.namelist():
                root = ET.fromstring(archive.read("docProps/core.xml"))
                result.meta_title = (root.findtext("dc:title", default="", namespaces=namespaces) or "").strip()
                result.meta_author = (root.findtext("dc:creator", default="", namespaces=namespaces) or "").strip()
                result.meta_subject = (root.findtext("dc:subject", default="", namespaces=namespaces) or "").strip()
                result.meta_keywords = (root.findtext("cp:keywords", default="", namespaces=namespaces) or "").strip()
                created = (root.findtext("dcterms:created", default="", namespaces=namespaces) or "").strip()
                modified = (root.findtext("dcterms:modified", default="", namespaces=namespaces) or "").strip()
                result.created = created[:10]
                result.modified = modified[:10]
            if "word/document.xml" in archive.namelist():
                root = ET.fromstring(archive.read("word/document.xml"))
                paragraphs: list[str] = []
                for paragraph in root.findall(".//w:p", namespaces):
                    texts = [
                        node.text or ""
                        for node in paragraph.findall(".//w:t", namespaces)
                        if node.text
                    ]
                    joined = "".join(texts).strip()
                    if joined:
                        paragraphs.append(joined)
                result.raw_text = "\n".join(paragraphs)
    except Exception as exc:
        result.notes.append(f"docx_extract_failed:{type(exc).__name__}")
    result.text_preview = result.raw_text[:12000]
    return result


def extract_doc_binary_text(path: Path) -> ExtractionResult:
    result = ExtractionResult()
    try:
        data = path.read_bytes()
    except Exception as exc:
        result.notes.append(f"doc_read_failed:{type(exc).__name__}")
        return result

    ascii_strings = re.findall(rb"[\x20-\x7e]{6,}", data)
    utf16_strings = re.findall(rb"(?:[\x20-\x7e]\x00){6,}", data)
    decoded: list[str] = []
    decoded.extend(chunk.decode("latin-1", errors="ignore") for chunk in ascii_strings[:600])
    decoded.extend(chunk.decode("utf-16le", errors="ignore") for chunk in utf16_strings[:600])
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in decoded:
        item = re.sub(r"\s+", " ", item).strip()
        if len(item) < 6:
            continue
        if item in seen:
            continue
        seen.add(item)
        cleaned.append(item)
    result.raw_text = "\n".join(cleaned[:250])
    result.text_preview = result.raw_text[:12000]
    if not result.raw_text:
        result.notes.append("doc_binary_only")
    return result


def normalize_markdown_text(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^\s{0,3}#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*>\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\|", " ", text)
    cleaned_lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in cleaned_lines if line)


def extract_markdown_text(path: Path) -> ExtractionResult:
    result = ExtractionResult()
    text = read_text_file(path)
    body = text
    lines = text.splitlines()

    if lines and lines[0].strip() == "---":
        front_matter: list[str] = []
        for index, line in enumerate(lines[1:40], start=1):
            if line.strip() == "---":
                body = "\n".join(lines[index + 1 :])
                break
            front_matter.append(line)
        for line in front_matter:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = normalize_for_match(key)
            value = value.strip().strip('"').strip("'")
            if not value:
                continue
            if key == "title":
                result.meta_title = clean_candidate_text(value)
            elif key in {"author", "authors", "creator"}:
                result.meta_author = clean_candidate_text(value)
            elif key in {"date", "created", "published"}:
                result.created = value[:10]
            elif key in {"tags", "keywords", "category", "categories"}:
                result.meta_keywords = clean_candidate_text(value)
            elif key in {"summary", "description", "abstract"}:
                result.meta_subject = clean_candidate_text(value)

    if not result.meta_title:
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                result.meta_title = clean_candidate_text(re.sub(r"^#+\s*", "", stripped))
                break

    cleaned = normalize_markdown_text(body)
    result.raw_text = cleaned
    result.text_preview = cleaned[:12000]
    return result


def extract_by_extension(path: Path, max_pages: int, ocr_mode: str, script_dir: Path) -> ExtractionResult:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        extracted = extract_pdf_text(path, max_pages=max_pages)
        if ocr_mode == "auto" and len(extracted.raw_text.strip()) < 120:
            ocr_result = attempt_ocr(path, script_dir=script_dir, max_pages=max_pages)
            if ocr_result and len(ocr_result.raw_text.strip()) > len(extracted.raw_text.strip()):
                extracted = ocr_result
        return extracted
    if suffix == ".docx":
        return extract_docx_text(path)
    if suffix == ".doc":
        return extract_doc_binary_text(path)
    if suffix == ".txt":
        text = read_text_file(path)
        return ExtractionResult(raw_text=text, text_preview=text[:12000])
    if suffix == ".md":
        return extract_markdown_text(path)
    return ExtractionResult()


def looks_like_title(value: str) -> bool:
    value = clean_candidate_text(value)
    if len(value) < 6 or len(value) > 180:
        return False
    if not re.search(r"[A-Za-zÀ-ÿ]", value):
        return False
    lowered = normalize_for_match(value)
    disallowed = [
        "untitled",
        "microsoft word",
        "abstract",
        "keywords",
        "references",
        "bibliography",
        "curriculum vitae",
        "table of contents",
    ]
    if lowered in disallowed or lowered.startswith("untitled"):
        return False
    if EMAIL_RE.search(value):
        return False
    if NAME_RE.match(value):
        return False
    return True


def embedded_title_candidates(line: str) -> list[str]:
    candidates: list[str] = []
    for match in QUOTE_TITLE_RE.finditer(line):
        candidate = clean_candidate_text(match.group(1))
        if looks_like_title(candidate):
            candidates.append(candidate)
    return candidates


def choose_title(record: DocumentRecord) -> tuple[str, str]:
    candidates = [
        (clean_candidate_text(record.extraction.meta_title), "meta_title", 100),
        (clean_candidate_text(record.extraction.meta_subject), "meta_subject", 70),
    ]
    filename_title = clean_candidate_text(fallback_title_from_filename(record.source_path))
    candidates.append((filename_title, "filename", 45))

    lines = [clean_candidate_text(line) for line in record.extraction.raw_text.splitlines() if line.strip()]
    for index, line in enumerate(lines[:25]):
        score = 80 - index
        if looks_like_title(line):
            candidates.append((line, f"text_line_{index + 1}", score))
        for embedded in embedded_title_candidates(line):
            candidates.append((embedded, f"text_embedded_{index + 1}", score + 2))
        if index < 8 and index + 1 < len(lines):
            combined = clean_candidate_text(f"{line} {lines[index + 1]}")
            if looks_like_title(combined):
                candidates.append((combined, f"text_joined_{index + 1}", score - 2))

    best_value = filename_title
    best_source = "filename"
    best_score = 0
    for value, source, score in candidates:
        if not value or not looks_like_title(value):
            continue
        if score > best_score:
            best_value, best_source, best_score = value, source, score

    return best_value.strip(), best_source


def plausible_author(value: str) -> bool:
    value = re.sub(r"\s+", " ", value or "").strip(" ,;:-")
    if not value:
        return False
    if EMAIL_RE.search(value):
        return False
    if len(value) > 120:
        return False
    lowered = normalize_for_match(value)
    blocked_terms = [
        "university",
        "universite",
        "department",
        "journal",
        "abstract",
        "keywords",
        "volume",
        "issue",
        "editor",
        "committee",
        "conference",
        "publisher",
    ]
    if any(term in lowered for term in blocked_terms):
        return False
    return bool(NAME_RE.match(value))


def authors_from_citation_line(line: str) -> list[str]:
    line = clean_candidate_text(line)
    match = AUTHOR_YEAR_LINE_RE.match(line)
    if not match:
        return []
    lead = match.group(1).strip(" ,;:-")
    lead = re.sub(r"\b(?:ed|eds|dir|dirs)\.?$", "", lead, flags=re.IGNORECASE).strip(" ,;:-")
    authors: list[str] = []
    if "," in lead:
        surname, remainder = [part.strip() for part in lead.split(",", 1)]
        surname = normalize_author_case(surname)
        if surname and remainder:
            remainder_parts = [part.strip(" ,;:-") for part in re.split(r"\s+(?:et|and|&)\s+", remainder) if part.strip()]
            if remainder_parts:
                candidate = normalize_author_case(f"{remainder_parts[0]} {surname}".strip())
                if plausible_author(candidate):
                    authors.append(candidate)
                for extra in remainder_parts[1:]:
                    extra = normalize_author_case(extra)
                    if plausible_author(extra):
                        authors.append(extra)
    else:
        for part in re.split(r"\s+(?:et|and|&)\s+", lead):
            candidate = normalize_author_case(part.strip(" ,;:-"))
            if plausible_author(candidate):
                authors.append(candidate)

    deduped: list[str] = []
    seen: set[str] = set()
    for author in authors:
        key = normalize_for_match(author)
        if key and key not in seen:
            seen.add(key)
            deduped.append(author)
    return deduped[:4]


def extract_authors_from_text(text: str, title: str) -> list[str]:
    authors: list[str] = []
    lines = [clean_candidate_text(line) for line in text.splitlines() if line.strip()]
    normalized_title = normalize_for_match(title)

    for index, line in enumerate(lines[:40]):
        normalized = normalize_for_match(line)
        if normalized == normalized_title:
            for follow in lines[index + 1 : index + 7]:
                follow = re.sub(r"\s+", " ", follow).strip(" ,;:-")
                if plausible_author(follow):
                    authors.append(follow)
                elif authors:
                    break

    for line in lines[:20]:
        authors.extend(authors_from_citation_line(line))

    for match in re.finditer(r"written by\s+([A-ZÀ-Ý][^\n]{2,80})", text, flags=re.IGNORECASE):
        candidate = match.group(1).splitlines()[0].strip(" ,;:-")
        if plausible_author(candidate):
            authors.append(candidate)

    for match in re.finditer(r"\bby\s+([A-ZÀ-Ý][A-Za-zÀ-ÿ'`.-]+(?:\s+[A-ZÀ-Ý][A-Za-zÀ-ÿ'`.-]+){1,4})", text):
        candidate = match.group(1).strip(" ,;:-")
        if plausible_author(candidate):
            authors.append(candidate)

    deduped: list[str] = []
    seen: set[str] = set()
    for author in authors:
        key = normalize_for_match(author)
        if key and key not in seen:
            seen.add(key)
            deduped.append(author)
    return deduped[:4]


def extract_author_from_filename(path: Path) -> str:
    stem = fallback_title_from_filename(path)
    parts = re.split(r"[_-]", stem)
    for part in parts[:4]:
        part = re.sub(r"\d{4,}", "", part).strip()
        if plausible_author(part):
            return part
    return ""


def choose_authors(record: DocumentRecord) -> tuple[list[str], str]:
    meta_author = re.sub(r"\s+", " ", record.extraction.meta_author or "").strip()
    if plausible_author(meta_author):
        return [meta_author], "meta_author"

    text_authors = extract_authors_from_text(record.extraction.raw_text[:4000], record.title)
    if text_authors:
        return text_authors, "text_or_citation"

    filename_author = extract_author_from_filename(record.source_path)
    if filename_author:
        return [filename_author], "filename"

    return [], ""


def month_to_number(token: str) -> int | None:
    token = normalize_for_match(token).replace(".", "")
    return MONTHS.get(token)


def choose_date(record: DocumentRecord) -> tuple[str, str, str]:
    candidates: list[tuple[int, str, str, str]] = []
    preview = "\n".join([record.title, fallback_title_from_filename(record.source_path), record.extraction.raw_text[:5000]])
    body_excerpt = record.extraction.raw_text[:5000]

    for match in ISO_DATE_RE.finditer(preview):
        iso_value = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        candidates.append((95, match.group(1), iso_value, "iso_text"))

    for match in DATE_SLASH_RE.finditer(preview):
        month = int(match.group(1))
        day = int(match.group(2))
        year = match.group(3)
        if month <= 12 and day <= 31:
            iso_value = f"{year}-{month:02d}-{day:02d}"
            candidates.append((90, year, iso_value, "slash_date"))

    for match in DATE_LONG_RE.finditer(preview):
        month = month_to_number(match.group(2))
        if month:
            day = int(match.group(1))
            year = match.group(3)
            iso_value = f"{year}-{month:02d}-{day:02d}"
            candidates.append((92, year, iso_value, "long_date"))

    for year in YEAR_RE.findall(record.title):
        candidates.append((88, year, f"{year}-01-01", "title_year"))

    for year in YEAR_RE.findall(fallback_title_from_filename(record.source_path)):
        candidates.append((80, year, f"{year}-01-01", "filename_year"))

    body_year_counts = defaultdict(int)
    for year in YEAR_RE.findall(body_excerpt):
        body_year_counts[year] += 1
    for year, count in body_year_counts.items():
        candidates.append((78 + min(count, 3), year, f"{year}-01-01", "body_year"))

    for value, source, score in [
        (record.extraction.created, "meta_created", 55),
        (record.extraction.modified, "meta_modified", 45),
        (record.modified_iso, "filesystem_modified", 20),
    ]:
        if value and YEAR_RE.search(value):
            year = YEAR_RE.search(value).group(1)
            iso_value = value if len(value) >= 10 else f"{year}-01-01"
            candidates.append((score, year, iso_value[:10], source))

    if not candidates:
        return "", "", ""

    score, year, iso_value, source = max(candidates, key=lambda item: (item[0], item[1], item[2]))
    return year, iso_value, source


def detect_language(record: DocumentRecord) -> str:
    raw_preview = "\n".join([record.title, record.extraction.raw_text[:5000], fallback_title_from_filename(record.source_path)])
    text = f" {normalize_compact(raw_preview)} "
    french_markers = [
        " le ",
        " la ",
        " les ",
        " des ",
        " du ",
        " et ",
        " que ",
        " dans ",
        " pour ",
        " avec ",
        " au ",
        " aux ",
        " these ",
        " memoire ",
        " universite ",
        " lettre ",
    ]
    english_markers = [
        " the ",
        " and ",
        " that ",
        " with ",
        " for ",
        " abstract ",
        " chapter ",
        " university ",
        " report ",
        " audit ",
        " written by ",
    ]
    french_score = sum(text.count(marker) for marker in french_markers)
    english_score = sum(text.count(marker) for marker in english_markers)
    french_score += sum(raw_preview.lower().count(ch) for ch in ("é", "è", "à", "ç", "ù", "ê", "â"))
    if french_score > english_score + 1:
        return "fr"
    if english_score > french_score + 1:
        return "en"
    return "unknown"


def classify_document(record: DocumentRecord, identities: list[str]) -> tuple[str, str, int, list[str]]:
    raw_excerpt = "\n".join(
        [
            fallback_title_from_filename(record.source_path),
            record.title,
            record.extraction.meta_title,
            record.extraction.meta_subject,
            record.extraction.meta_keywords,
            record.extraction.raw_text[:8000],
        ]
    )
    combined = normalize_compact(
        "\n".join(
            [
                fallback_title_from_filename(record.source_path),
                record.title,
                record.extraction.meta_title,
                record.extraction.meta_subject,
                record.extraction.meta_keywords,
                record.extraction.raw_text[:8000],
            ]
        )
    )
    title_compact = normalize_compact(record.title)
    filename_compact = normalize_compact(fallback_title_from_filename(record.source_path))
    lines = [clean_candidate_text(line) for line in record.extraction.raw_text.splitlines() if line.strip()]
    scores: dict[str, int] = defaultdict(int)
    reasons: dict[str, list[str]] = defaultdict(list)

    for doc_type, config in TYPE_RULES.items():
        for pattern, weight in config["patterns"].items():
            if contains_compact_phrase(combined, pattern):
                scores[doc_type] += weight
                reasons[doc_type].append(pattern)

    if record.extension == ".pdf" and len(record.extraction.raw_text.strip()) < 40 and not record.extraction.ocr_used:
        return "ocr_needed", "UNCLEAR", 1, ["low_text_pdf"]

    if record.doi:
        scores["journal_article"] += 9
        reasons["journal_article"].append("doi")

    if record.isbn:
        scores["book_or_monograph"] += 8
        reasons["book_or_monograph"].append("isbn")

    if record.extraction.page_count and record.extraction.page_count > 80:
        scores["book_or_monograph"] += 3
        scores["thesis_or_dissertation"] += 2

    if contains_compact_phrase(combined, "references") and contains_compact_phrase(combined, "abstract"):
        scores["journal_article"] += 4
        reasons["journal_article"].append("abstract+references")

    if contains_compact_phrase(combined, "fade in") and contains_compact_phrase(combined, "written by"):
        scores["screenplay"] += 12
        reasons["screenplay"].append("screenplay_structure")

    if contains_compact_phrase(combined, "chapter 1") and not contains_compact_phrase(combined, "references"):
        scores["manuscript"] += 4
        reasons["manuscript"].append("chapter_without_refs")

    if contains_compact_phrase(title_compact, "book review") or contains_compact_phrase(title_compact, "compte rendu"):
        scores["review"] += 20
        reasons["review"].append("review_title")

    if contains_compact_phrase(title_compact, "pilot script") or contains_compact_phrase(title_compact, "screenplay"):
        scores["screenplay"] += 18
        reasons["screenplay"].append("screenplay_title")

    if contains_compact_phrase(title_compact, "plan de memoire"):
        scores["thesis_or_dissertation"] += 10
        reasons["thesis_or_dissertation"].append("thesis_plan_title")

    first_lines = " ".join(lines[:6])
    first_lines_compact = normalize_compact(first_lines)
    quoted_title_near_year = any(QUOTE_TITLE_RE.search(line) and YEAR_RE.search(line) for line in lines[:6])
    citation_line = next((line for line in lines[:6] if AUTHOR_YEAR_LINE_RE.match(line)), "")
    if quoted_title_near_year and (
        contains_compact_phrase(first_lines_compact, " dans ")
        or contains_compact_phrase(first_lines_compact, " edited by ")
        or contains_compact_phrase(first_lines_compact, " sous la direction de ")
        or PAGE_SPAN_RE.search(first_lines)
        or " (dir" in first_lines.lower()
        or " ed." in first_lines.lower()
    ):
        scores["book_chapter"] += 18
        reasons["book_chapter"].append("bibliographic_chapter_citation")

    if citation_line and PAGE_SPAN_RE.search(first_lines):
        scores["book_chapter"] += 6
        reasons["book_chapter"].append("page_span_citation")

    scene_heading_count = sum(1 for line in lines[:200] if SCENE_HEADING_RE.match(line))
    if scene_heading_count >= 2:
        scores["screenplay"] += 18
        reasons["screenplay"].append("scene_headings")
    elif scene_heading_count == 1 and contains_compact_phrase(combined, "written by"):
        scores["screenplay"] += 8
        reasons["screenplay"].append("single_scene_heading")

    if record.language == "fr" and contains_compact_phrase(filename_compact, "glossaire"):
        scores["book_chapter"] += 8
        reasons["book_chapter"].append("glossaire_filename")

    if contains_compact_phrase(combined, "hydro quebec"):
        scores["statement_or_bill"] += 12
        reasons["statement_or_bill"].append("hydro_quebec")

    if any(normalize_for_match(identity) in combined for identity in identities):
        if scores["screenplay"] or scores["manuscript"]:
            scores["manuscript"] += 2
            reasons["manuscript"].append("identity_match")
        elif scores["cover_letter"] or scores["job_application"] or scores["cv_resume"]:
            scores["cover_letter"] += 1
        elif not any(scores.values()):
            scores["correspondence"] += 2
            reasons["correspondence"].append("identity_only")

    if not scores:
        return "unclear", "UNCLEAR", 0, ["no_strong_signals"]

    best_type, best_score = max(
        scores.items(),
        key=lambda item: (item[1], TYPE_PRIORITY.get(item[0], 0), item[0]),
    )
    best_category = TYPE_RULES[best_type]["category"]
    why = reasons[best_type] or ["weak_match"]

    if best_score < 6:
        return "unclear", "UNCLEAR", best_score, why + ["low_confidence"]

    return best_type, best_category, best_score, why


def probable_duplicate_key(record: DocumentRecord) -> str:
    if record.category == "UNCLEAR" or record.doc_type == "ocr_needed":
        return ""
    if record.doc_type in REVISION_SENSITIVE_TYPES:
        return ""
    if record.doi:
        return f"doi::{record.doi.lower()}"
    normalized_title = normalize_for_match(record.title)
    if len(normalized_title) < 12:
        return ""
    if record.title_source == "filename" and not record.authors and not record.doi and len(record.extraction.raw_text.strip()) < 120:
        return ""
    if not record.year:
        return ""
    if not record.author_key and record.category == "SCHOLAR":
        return f"title_year::{normalized_title}::{record.year}::{record.doc_type}"
    if record.author_key:
        return f"title_author_year::{normalized_title}::{record.author_key}::{record.year}::{record.doc_type}"
    return ""


def quality_score(record: DocumentRecord) -> int:
    score = len(record.extraction.raw_text.strip()) // 40
    score += (record.extraction.page_count or 0) * 4
    score += min(record.size_bytes // 50_000, 40)
    if record.title_source:
        score += 18
    if record.author_source:
        score += 14
    if record.year:
        score += 10
    if record.doi:
        score += 24
    if record.extraction.ocr_used:
        score += 8
    extension_bonus = {
        ".pdf": 10 if record.category in {"SCHOLAR", "PROFESSIONAL"} else 4,
        ".docx": 10 if record.category in {"PERSONAL_ADMIN", "CREATIVE"} else 5,
        ".doc": 2,
        ".txt": 4,
    }
    score += extension_bonus.get(record.extension, 0)
    return score


def mark_duplicates(records: list[DocumentRecord], similar_dedupe: bool) -> None:
    hash_groups: dict[str, list[DocumentRecord]] = defaultdict(list)
    for record in records:
        hash_groups[record.sha256].append(record)

    for digest, group in hash_groups.items():
        if len(group) < 2:
            continue
        winner = max(group, key=quality_score)
        for record in group:
            if record is winner:
                record.duplicate_status = "keep"
                continue
            record.duplicate_status = "duplicate_exact"
            record.duplicate_reason = "same_sha256_as_better_copy"
            record.duplicate_group = digest[:12]

    if not similar_dedupe:
        return

    probable_groups: dict[str, list[DocumentRecord]] = defaultdict(list)
    for record in records:
        if record.duplicate_status != "keep":
            continue
        key = probable_duplicate_key(record)
        if key:
            probable_groups[key].append(record)

    for key, group in probable_groups.items():
        if len(group) < 2:
            continue
        winner = max(group, key=quality_score)
        for record in group:
            if record is winner:
                continue
            record.duplicate_status = "duplicate_probable"
            record.duplicate_reason = "same_title_author_year_signature"
            record.duplicate_group = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def build_destination(
    record: DocumentRecord,
    output_root: Path,
    quarantine_root: Path,
    destination_schema: str = "category_type_year",
) -> Path:
    year_bucket = record.year or "Undated"
    filename = f"{record.filename_stub()}{record.extension}"
    if record.duplicate_status == "duplicate_exact":
        return quarantine_root / "Duplicates" / "Exact" / year_bucket / filename
    if record.duplicate_status == "duplicate_probable":
        return quarantine_root / "Duplicates" / "Probable" / year_bucket / filename
    if record.doc_type == "ocr_needed":
        return output_root / "UNCLEAR" / "Scans_OCR_Needed" / year_bucket / filename
    if record.category == "UNCLEAR":
        return output_root / "UNCLEAR" / year_bucket / filename
    if destination_schema == "category_year_type":
        return output_root / record.category / year_bucket / record.doc_type / filename
    if destination_schema == "category_author_year":
        author_bucket = sanitize_filename_component(record.author_key or record.primary_author or "UnknownAuthor", max_len=40)
        return output_root / record.category / author_bucket / year_bucket / record.doc_type / filename
    return output_root / record.category / record.doc_type / year_bucket / filename


def choose_sources(script_dir: Path, sources: list[str]) -> list[Path]:
    if sources:
        return [Path(source).expanduser().resolve() for source in sources if Path(source).expanduser().exists()]
    discovered = []
    for name in DEFAULT_SOURCE_DIRS:
        candidate = (script_dir / name).resolve()
        if candidate.exists():
            discovered.append(candidate)
    return discovered


def cross_reference_signature(record: DocumentRecord) -> tuple[str, str]:
    if record.doi:
        return f"doi::{record.doi.lower()}", "doi"
    title_key = normalize_compact(record.title or fallback_title_from_filename(record.source_path))
    if title_key and record.author_key and record.year:
        return f"title_author_year::{title_key}::{record.author_key}::{record.year}", "title_author_year"
    if title_key and record.year:
        return f"title_year::{title_key}::{record.year}", "title_year"
    if title_key:
        return f"title_only::{title_key}", "title_only"
    return f"sha256::{record.sha256}", "sha256"


def load_master_bibliography_entries(path: Path | None) -> list[dict[str, object]]:
    if path is None or not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        lines = path.read_text(encoding="latin-1", errors="replace").splitlines()

    entries: list[dict[str, object]] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.upper() == line and len(line.split()) <= 4:
            continue
        normalized = normalize_compact(line)
        tokens = significant_tokens(line)
        if len(tokens) < 2 and len(normalized) < 18:
            continue
        entries.append({"line": line, "normalized": normalized, "tokens": tokens})
    return entries


def bibliography_matches_for_record(
    record: DocumentRecord,
    entries: list[dict[str, object]],
    limit: int = 3,
) -> list[str]:
    if not entries:
        return []
    title = record.title or fallback_title_from_filename(record.source_path)
    normalized_title = normalize_compact(title)
    title_tokens = significant_tokens(title)
    if len(normalized_title) < 12 and len(title_tokens) < 2:
        return []

    author_key = record.author_key
    year = record.year
    matches: list[tuple[int, str]] = []
    for entry in entries:
        normalized_line = str(entry["normalized"])
        line_tokens = entry["tokens"]
        score = 0
        if normalized_title and (normalized_title in normalized_line or normalized_line in normalized_title):
            score += 6
        shared = title_tokens & set(line_tokens)
        score += min(len(shared), 4)
        if author_key and author_key in normalized_line:
            score += 2
        if year and year in normalized_line:
            score += 1
        if score >= 4:
            matches.append((score, str(entry["line"])))
    matches.sort(key=lambda item: (-item[0], item[1].lower()))
    deduped: list[str] = []
    seen: set[str] = set()
    for _, line in matches:
        key = normalize_compact(line)
        if key not in seen:
            seen.add(key)
            deduped.append(line)
        if len(deduped) >= limit:
            break
    return deduped


def write_cross_reference_report(
    records: list[DocumentRecord],
    report_root: Path,
    run_id: str,
    bibliography_path: Path | None = None,
) -> tuple[Path, Path, Path]:
    report_root.mkdir(parents=True, exist_ok=True)
    csv_path = report_root / f"cross_reference_{run_id}.csv"
    json_path = report_root / f"cross_reference_{run_id}.json"
    summary_path = report_root / f"cross_reference_{run_id}.txt"

    bibliography_entries = load_master_bibliography_entries(bibliography_path)
    grouped: dict[str, list[DocumentRecord]] = defaultdict(list)
    signatures: dict[str, str] = {}
    for record in records:
        signature, basis = cross_reference_signature(record)
        grouped[signature].append(record)
        signatures[signature] = basis

    rows: list[dict[str, str]] = []
    bibliography_hit_count = 0
    for signature, group in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
        members = sorted(group, key=lambda record: (record.year or "9999", record.primary_author.lower(), record.title.lower()))
        for record in members:
            matches = bibliography_matches_for_record(record, bibliography_entries)
            if matches:
                bibliography_hit_count += 1
            rows.append(
                {
                    "cross_reference_key": signature,
                    "cross_reference_basis": signatures[signature],
                    "group_size": str(len(group)),
                    "group_members": " | ".join(member.relative_source for member in members),
                    "source_path": str(record.source_path),
                    "relative_source": record.relative_source,
                    "title": record.title,
                    "authors": "; ".join(record.authors),
                    "year": record.year,
                    "doi": record.doi,
                    "duplicate_status": record.duplicate_status,
                    "duplicate_group": record.duplicate_group,
                    "planned_destination": str(record.planned_destination or ""),
                    "planned_destination_exists": str(bool(record.planned_destination and record.planned_destination.exists())),
                    "bibliography_matches": " | ".join(matches),
                    "bibliography_match_count": str(len(matches)),
                }
            )

    fieldnames = list(rows[0].keys()) if rows else [
        "cross_reference_key",
        "cross_reference_basis",
        "group_size",
        "group_members",
        "source_path",
        "relative_source",
        "title",
        "authors",
        "year",
        "doi",
        "duplicate_status",
        "duplicate_group",
        "planned_destination",
        "planned_destination_exists",
        "bibliography_matches",
        "bibliography_match_count",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2)

    multi_groups = sum(1 for group in grouped.values() if len(group) > 1)
    lines = [
        f"Cross reference run: {run_id}",
        f"Records indexed: {len(records)}",
        f"Unique cross-reference groups: {len(grouped)}",
        f"Groups with multiple scan matches: {multi_groups}",
        f"Rows with bibliography matches: {bibliography_hit_count}",
        "",
        "Largest groups:",
    ]
    largest = sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))[:10]
    for signature, group in largest:
        title = group[0].title or fallback_title_from_filename(group[0].source_path)
        lines.append(f"  {len(group)}x [{signatures[signature]}] {title}")
    if bibliography_entries:
        lines.append("")
        lines.append(f"Bibliography source: {bibliography_path}")
    with summary_path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")

    return csv_path, json_path, summary_path


def render_masterlist(
    records: list[DocumentRecord],
    report_root: Path,
    run_id: str,
) -> tuple[Path, Path, Path]:
    report_root.mkdir(parents=True, exist_ok=True)
    csv_path = report_root / f"masterlist_{run_id}.csv"
    markdown_path = report_root / f"masterlist_{run_id}.md"
    text_path = report_root / f"masterlist_{run_id}.txt"

    sorted_records = sorted(
        records,
        key=lambda record: (
            record.category,
            record.doc_type,
            record.year or "9999",
            record.primary_author.lower(),
            record.title.lower(),
            record.relative_source.lower(),
        ),
    )

    rows = [
        {
            "category": record.category,
            "doc_type": record.doc_type,
            "year": record.year,
            "author": record.primary_author,
            "title": record.title,
            "language": record.language,
            "duplicate_status": record.duplicate_status,
            "doi": record.doi,
            "source_path": str(record.source_path),
            "planned_destination": str(record.planned_destination or ""),
        }
        for record in sorted_records
    ]
    fieldnames = list(rows[0].keys()) if rows else [
        "category",
        "doc_type",
        "year",
        "author",
        "title",
        "language",
        "duplicate_status",
        "doi",
        "source_path",
        "planned_destination",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    markdown_lines = [f"# Masterlist {run_id}", ""]
    text_lines = [f"MASTERLIST {run_id}", ""]
    current_bucket = None
    for record in sorted_records:
        bucket = (record.category, record.doc_type)
        if bucket != current_bucket:
            current_bucket = bucket
            markdown_lines.append(f"## {record.category} / {record.doc_type}")
            markdown_lines.append("")
            text_lines.append(f"{record.category} / {record.doc_type}")
        author = record.primary_author or "Unknown author"
        year = record.year or "Undated"
        title = record.title or fallback_title_from_filename(record.source_path)
        destination = str(record.planned_destination or "")
        markdown_lines.append(
            f"- `{year}` | {author} | {title} | `{record.language}` | `{record.duplicate_status}` | `{destination}`"
        )
        text_lines.append(f"- {year} | {author} | {title} | {record.language} | {record.duplicate_status}")
    markdown_lines.append("")
    text_lines.append("")

    with markdown_path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(markdown_lines) + "\n")
    with text_path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(text_lines) + "\n")

    return csv_path, markdown_path, text_path


def write_reports(records: list[DocumentRecord], report_root: Path, run_id: str) -> tuple[Path, Path, Path]:
    report_root.mkdir(parents=True, exist_ok=True)
    csv_path = report_root / f"manifest_{run_id}.csv"
    json_path = report_root / f"manifest_{run_id}.json"
    summary_path = report_root / f"summary_{run_id}.txt"

    rows = [record.to_row() for record in records]
    fieldnames = list(rows[0].keys()) if rows else list(DocumentRecord.__dataclass_fields__.keys())
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2)

    counts_by_category: dict[str, int] = defaultdict(int)
    counts_by_type: dict[str, int] = defaultdict(int)
    duplicate_counts: dict[str, int] = defaultdict(int)
    for record in records:
        counts_by_category[record.category] += 1
        counts_by_type[record.doc_type] += 1
        duplicate_counts[record.duplicate_status] += 1

    lines = [
        f"Run: {run_id}",
        f"Documents scanned: {len(records)}",
        "",
        "By category:",
    ]
    lines.extend(f"  {key}: {value}" for key, value in sorted(counts_by_category.items()))
    lines.append("")
    lines.append("By type:")
    lines.extend(f"  {key}: {value}" for key, value in sorted(counts_by_type.items()))
    lines.append("")
    lines.append("Duplicate status:")
    lines.extend(f"  {key}: {value}" for key, value in sorted(duplicate_counts.items()))
    lines.append("")
    lines.append(f"Manifest CSV: {csv_path}")
    lines.append(f"Manifest JSON: {json_path}")
    with summary_path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")

    return csv_path, json_path, summary_path


def scan_documents(
    source_roots: list[Path],
    max_pages: int,
    ocr_mode: str,
    recursive: bool,
    limit: int | None,
    identities: list[str],
    script_dir: Path,
    rules: list[PlainEnglishRule] | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> list[DocumentRecord]:
    records: list[DocumentRecord] = []
    for source_root, source_path in discover_files(source_roots, recursive=recursive, limit=limit):
        stat = source_path.stat()
        extraction = extract_by_extension(source_path, max_pages=max_pages, ocr_mode=ocr_mode, script_dir=script_dir)
        record = DocumentRecord(
            source_path=source_path,
            source_root=source_root,
            extension=source_path.suffix.lower(),
            size_bytes=stat.st_size,
            sha256=hash_file(source_path),
            modified_iso=dt.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d"),
            extraction=extraction,
        )
        record.title, record.title_source = choose_title(record)
        record.authors, record.author_source = choose_authors(record)
        record.year, record.date_iso, record.date_source = choose_date(record)
        record.language = detect_language(record)
        doi_match = DOI_RE.search("\n".join([record.title, extraction.raw_text[:12000], fallback_title_from_filename(source_path)]))
        record.doi = doi_match.group(0) if doi_match else ""
        isbn_match = ISBN_RE.search("\n".join([record.title, extraction.raw_text[:12000], fallback_title_from_filename(source_path)]))
        record.isbn = isbn_match.group(0) if isbn_match else ""
        record.doc_type, record.category, record.type_confidence, record.reasoning = classify_document(record, identities=identities)
        record.tags = generate_tags(record)
        records.append(record)
        message = f"[SCAN] {record.relative_source} -> {record.category}/{record.doc_type}"
        if progress_callback:
            progress_callback(message)
        else:
            print(message, flush=True)
    if rules:
        apply_plain_english_rules(records, rules)
        for record in records:
            generated = generate_tags(record)
            for tag in generated:
                if tag not in record.tags:
                    record.tags.append(tag)
    return records


def plan_destinations(
    records: list[DocumentRecord],
    output_root: Path,
    quarantine_root: Path,
    destination_schema: str = "category_type_year",
) -> None:
    used_paths: set[Path] = set()
    for record in records:
        record.planned_destination = ensure_unique_path(
            build_destination(
                record,
                output_root=output_root,
                quarantine_root=quarantine_root,
                destination_schema=destination_schema,
            ),
            used_paths=used_paths,
        )


def apply_plan(records: list[DocumentRecord], mode: str, progress_callback: Callable[[str], None] | None = None) -> None:
    for record in records:
        destination = record.planned_destination
        if destination is None:
            record.action = "SKIPPED"
            continue
        if mode == "scan":
            record.action = "PLANNED"
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            if mode == "copy":
                shutil.copy2(record.source_path, destination)
                record.action = "COPIED"
            elif mode == "move":
                shutil.move(str(record.source_path), str(destination))
                record.action = "MOVED"
            else:
                raise ValueError(f"Unsupported mode: {mode}")
        except Exception as exc:
            record.action = f"ERROR:{type(exc).__name__}"
            record.reasoning.append(f"apply_failed:{exc}")
        message = f"[APPLY] {record.source_path.name} -> {destination}"
        if progress_callback:
            progress_callback(message)
        else:
            print(message, flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Scan PDFs, DOCX, DOC, and TXT files; extract metadata from multiple sources; "
            "deduplicate; then rename and sort into a structured library."
        )
    )
    parser.add_argument("--source", action="append", default=[], help="Source directory to scan. Repeatable.")
    parser.add_argument(
        "--output-root",
        help="Destination root for sorted files. Defaults to SORTED_LIBRARY_V2 under the script folder.",
    )
    parser.add_argument(
        "--quarantine-root",
        help="Destination root for duplicates. Defaults to QUARANTINE/V2 under the script folder.",
    )
    parser.add_argument(
        "--report-root",
        help="Destination root for reports. Defaults to REPORTS_V2 under the script folder.",
    )
    parser.add_argument("--mode", choices=("scan", "copy", "move"), default="copy")
    parser.add_argument("--max-pages", type=int, default=5, help="How many PDF pages to inspect. Default: 5")
    parser.add_argument("--limit", type=int, help="Optional limit for testing.")
    parser.add_argument("--ocr", choices=("auto", "never"), default="auto")
    parser.add_argument("--no-similar-dedupe", action="store_true", help="Disable title/author/year dedupe.")
    parser.add_argument("--no-recursive", action="store_true", help="Only scan the top level of each source.")
    parser.add_argument("--render-crossref", action="store_true", help="Also render a cross-reference report.")
    parser.add_argument("--render-masterlist", action="store_true", help="Also render a masterlist report.")
    parser.add_argument("--rules-file", help="Optional plain-English rules file.")
    parser.add_argument(
        "--identity",
        action="append",
        default=[],
        help="Identity string used to recognize personal or creative documents. Repeatable.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    sources = choose_sources(script_dir=script_dir, sources=args.source)
    if not sources:
        parser.error("No source folders were found. Pass --source or create INBOX / LEGACY_INBOX.")

    output_root = Path(args.output_root).expanduser().resolve() if args.output_root else (script_dir / DEFAULT_OUTPUT_DIR).resolve()
    quarantine_root = (
        Path(args.quarantine_root).expanduser().resolve()
        if args.quarantine_root
        else (script_dir / DEFAULT_QUARANTINE_DIR).resolve()
    )
    report_root = Path(args.report_root).expanduser().resolve() if args.report_root else (script_dir / DEFAULT_REPORT_DIR).resolve()
    bibliography_path = (script_dir / "MASTER BIBLIOGRAPHY.txt").resolve()
    default_rules_path = (script_dir / RULES_EXAMPLE_NAME).resolve()
    rules_path = Path(args.rules_file).expanduser().resolve() if args.rules_file else (default_rules_path if default_rules_path.exists() else None)
    rules = load_plain_english_rules(rules_path)
    identities = DEFAULT_IDENTITIES + args.identity

    run_id = timestamp()
    print(f"Run ID: {run_id}")
    print(f"Mode: {args.mode}")
    print("Sources:")
    for source in sources:
        print(f"  - {source}")
    print(f"Output root: {output_root}")
    print(f"Quarantine root: {quarantine_root}")
    print(f"Report root: {report_root}")
    if rules_path and rules:
        print(f"Rules file: {rules_path} ({len(rules)} rules)")

    records = scan_documents(
        source_roots=sources,
        max_pages=args.max_pages,
        ocr_mode=args.ocr,
        recursive=not args.no_recursive,
        limit=args.limit,
        identities=identities,
        script_dir=script_dir,
        rules=rules,
    )

    mark_duplicates(records, similar_dedupe=not args.no_similar_dedupe)
    plan_destinations(records, output_root=output_root, quarantine_root=quarantine_root)
    apply_plan(records, mode=args.mode)
    csv_path, json_path, summary_path = write_reports(records, report_root=report_root, run_id=run_id)
    crossref_paths: tuple[Path, Path, Path] | None = None
    masterlist_paths: tuple[Path, Path, Path] | None = None
    if args.render_crossref:
        crossref_paths = write_cross_reference_report(
            records,
            report_root=report_root,
            run_id=run_id,
            bibliography_path=bibliography_path if bibliography_path.exists() else None,
        )
    if args.render_masterlist:
        masterlist_paths = render_masterlist(records, report_root=report_root, run_id=run_id)

    kept = sum(1 for record in records if record.duplicate_status == "keep")
    exact_dupes = sum(1 for record in records if record.duplicate_status == "duplicate_exact")
    probable_dupes = sum(1 for record in records if record.duplicate_status == "duplicate_probable")

    print("")
    print(f"Documents scanned: {len(records)}")
    print(f"Kept: {kept}")
    print(f"Exact duplicates: {exact_dupes}")
    print(f"Probable duplicates: {probable_dupes}")
    print(f"Manifest CSV: {csv_path}")
    print(f"Manifest JSON: {json_path}")
    print(f"Summary: {summary_path}")
    if crossref_paths:
        print(f"Cross Reference CSV: {crossref_paths[0]}")
        print(f"Cross Reference JSON: {crossref_paths[1]}")
        print(f"Cross Reference Summary: {crossref_paths[2]}")
    if masterlist_paths:
        print(f"Masterlist CSV: {masterlist_paths[0]}")
        print(f"Masterlist Markdown: {masterlist_paths[1]}")
        print(f"Masterlist Text: {masterlist_paths[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
