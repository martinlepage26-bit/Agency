from __future__ import annotations

import datetime as dt
import re
import shutil
import unicodedata
from dataclasses import dataclass
from pathlib import Path


LOTUS_NOTE_EXTENSIONS = {".md", ".txt"}
HASH_SUFFIX_RE = re.compile(r"__([0-9A-F]{8})$", re.IGNORECASE)

AGENCY_SIGNAL_GROUPS: dict[str, dict[str, object]] = {
    "strategic": {
        "weight": 8,
        "terms": [
            "strategy",
            "strategic",
            "roadmap",
            "program",
            "mission",
            "direction",
            "initiative",
            "priority",
            "capability",
            "institution",
            "systems thinking",
        ],
    },
    "governance": {
        "weight": 9,
        "terms": [
            "governance",
            "policy",
            "procurement",
            "oversight",
            "compliance",
            "accountability",
            "framework",
            "standard",
            "control",
            "risk",
            "public interest",
        ],
    },
    "operational": {
        "weight": 7,
        "terms": [
            "operations",
            "workflow",
            "execution",
            "delivery",
            "implementation",
            "process",
            "team",
            "capacity",
            "coordination",
            "scheduling",
            "monitoring",
        ],
    },
    "agency": {
        "weight": 10,
        "terms": [
            "agency",
            "autonomy",
            "influence",
            "choice",
            "self determination",
            "power",
            "capacity to act",
            "institutional leverage",
            "decision",
            "responsibility",
        ],
    },
    "creative": {
        "weight": 8,
        "terms": [
            "creative",
            "imagination",
            "aesthetic",
            "story",
            "narrative",
            "poetic",
            "art",
            "music",
            "film",
            "image",
            "design",
        ],
    },
    "meaning": {
        "weight": 8,
        "terms": [
            "meaning",
            "interpretation",
            "symbolic",
            "ethics",
            "memory",
            "identity",
            "culture",
            "development",
            "brain plasticity",
            "young age",
            "youth",
        ],
    },
}


@dataclass
class LotusNote:
    path: Path
    title: str
    modified_iso: str
    size_kb: int
    agency_score: int
    strategic_score: int
    creative_score: int
    governance_score: int
    operational_score: int
    meaning_score: int
    signals: list[str]
    excerpt: str
    text: str


@dataclass
class MarkdownExtraction:
    meta_title: str = ""
    raw_text: str = ""
    text_preview: str = ""


def ensure_lotus_root(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    return root


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


def clean_candidate_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "").strip(" |-_")
    value = re.sub(r"^\d{1,4}\s+(?=[A-Za-z])", "", value)
    value = value.strip(" .;:-|")
    return value


def fallback_title_from_filename(path: Path) -> str:
    stem = HASH_SUFFIX_RE.sub("", path.stem)
    stem = stem.replace("_", " ").replace(".", " ")
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem


def read_text_file(path: Path) -> str:
    encodings = ["utf-8-sig", "utf-16", "utf-16le", "utf-16be", "utf-8", "cp1252", "latin-1"]
    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="latin-1", errors="replace")


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


def extract_markdown_text(path: Path) -> MarkdownExtraction:
    extracted = MarkdownExtraction()
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
            if key == "title" and value:
                extracted.meta_title = clean_candidate_text(value)

    if not extracted.meta_title:
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                extracted.meta_title = clean_candidate_text(re.sub(r"^#+\s*", "", stripped))
                break

    cleaned = normalize_markdown_text(body)
    extracted.raw_text = cleaned
    extracted.text_preview = cleaned[:12000]
    return extracted


def _read_note_text(path: Path) -> tuple[str, str]:
    if path.suffix.lower() == ".md":
        extracted = extract_markdown_text(path)
        title = extracted.meta_title or clean_candidate_text(fallback_title_from_filename(path))
        text = extracted.raw_text or extracted.text_preview
        return title, text
    text = read_text_file(path)
    title = clean_candidate_text(fallback_title_from_filename(path))
    for line in text.splitlines():
        cleaned = clean_candidate_text(line)
        if cleaned and len(cleaned) >= 6:
            title = cleaned
            break
    return title, text


def _score_group(text: str, terms: list[str], weight: int) -> tuple[int, list[str]]:
    compact_text = normalize_compact(text)
    matched: list[str] = []
    for term in terms:
        if contains_compact_phrase(compact_text, term):
            matched.append(term)
    return min(len(matched) * weight, 100), matched


def score_lotus_text(title: str, text: str) -> dict[str, object]:
    full_text = "\n".join([title, text[:24000]])
    group_scores: dict[str, int] = {}
    matched_terms: dict[str, list[str]] = {}
    for group_name, config in AGENCY_SIGNAL_GROUPS.items():
        score, matched = _score_group(full_text, config["terms"], int(config["weight"]))
        group_scores[group_name] = score
        matched_terms[group_name] = matched

    agency_score = round(
        (
            group_scores["agency"] * 0.28
            + group_scores["strategic"] * 0.22
            + group_scores["governance"] * 0.22
            + group_scores["operational"] * 0.18
            + group_scores["meaning"] * 0.10
        )
    )
    creative_score = round((group_scores["creative"] * 0.6) + (group_scores["meaning"] * 0.4))

    signals: list[str] = []
    for group_name, matches in matched_terms.items():
        if matches:
            signals.append(group_name)
    return {
        "agency_score": min(agency_score, 100),
        "creative_score": min(creative_score, 100),
        "strategic_score": group_scores["strategic"],
        "governance_score": group_scores["governance"],
        "operational_score": group_scores["operational"],
        "meaning_score": group_scores["meaning"],
        "signals": signals,
    }


def load_lotus_notes(root: Path) -> list[LotusNote]:
    root = ensure_lotus_root(root)
    notes: list[LotusNote] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in LOTUS_NOTE_EXTENSIONS:
            continue
        title, text = _read_note_text(path)
        scores = score_lotus_text(title, text)
        stat = path.stat()
        notes.append(
            LotusNote(
                path=path,
                title=title,
                modified_iso=dt.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                size_kb=max(1, stat.st_size // 1024),
                agency_score=int(scores["agency_score"]),
                strategic_score=int(scores["strategic_score"]),
                creative_score=int(scores["creative_score"]),
                governance_score=int(scores["governance_score"]),
                operational_score=int(scores["operational_score"]),
                meaning_score=int(scores["meaning_score"]),
                signals=list(scores["signals"]),
                excerpt=text[:1200],
                text=text,
            )
        )
    return sorted(notes, key=lambda note: (-note.agency_score, -note.creative_score, note.title.lower()))


def import_notes(paths: list[Path], lotus_root: Path) -> list[Path]:
    lotus_root = ensure_lotus_root(lotus_root)
    imported: list[Path] = []
    for source in paths:
        destination = lotus_root / source.name
        counter = 2
        while destination.exists():
            destination = lotus_root / f"{source.stem} [{counter}]{source.suffix}"
            counter += 1
        shutil.copy2(source, destination)
        imported.append(destination)
    return imported
