from __future__ import annotations

import datetime as dt
import shutil
from dataclasses import dataclass
from pathlib import Path

import document_sorter as sorter


LOTUS_NOTE_EXTENSIONS = {".md", ".txt"}

LOTUS_SCORE_SECTION_ORDER = ("agency", "strategic", "governance", "operational", "creative", "meaning")

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


def ensure_lotus_root(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    return root


def _read_note_text(path: Path) -> tuple[str, str]:
    if path.suffix.lower() == ".md":
        extracted = sorter.extract_markdown_text(path)
        title = extracted.meta_title or sorter.clean_candidate_text(sorter.fallback_title_from_filename(path))
        text = extracted.raw_text or extracted.text_preview
        return title, text
    text = sorter.read_text_file(path)
    title = sorter.clean_candidate_text(sorter.fallback_title_from_filename(path))
    for line in text.splitlines():
        cleaned = sorter.clean_candidate_text(line)
        if cleaned and len(cleaned) >= 6:
            title = cleaned
            break
    return title, text


def _score_group(text: str, terms: list[str], weight: int) -> tuple[int, list[str]]:
    compact_text = sorter.normalize_compact(text)
    matched: list[str] = []
    for term in terms:
        if sorter.contains_compact_phrase(compact_text, term):
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
        "matched_terms": matched_terms,
    }


def _yaml_value(value: str) -> str:
    return value.replace('"', "'").strip()


def build_structured_note_markdown(
    *,
    title: str,
    author: str = "",
    note_date: str = "",
    tags: list[str] | None = None,
    context: str = "",
    source: str = "",
    summary: str = "",
    sections: dict[str, str] | None = None,
) -> str:
    tags = [tag.strip() for tag in (tags or []) if tag.strip()]
    sections = sections or {}

    lines = [
        "---",
        f'title: "{_yaml_value(title or "LOTUS note")}"',
    ]
    if author.strip():
        lines.append(f'author: "{_yaml_value(author)}"')
    if note_date.strip():
        lines.append(f"date: {note_date.strip()}")
    if tags:
        lines.append(f"tags: {', '.join(tags)}")
    if context.strip():
        lines.append(f'context: "{_yaml_value(context)}"')
    if source.strip():
        lines.append(f'source: "{_yaml_value(source)}"')
    lines.extend(["---", ""])

    lines.extend(["# Summary", "", summary.strip() or "Structured LOTUS scoring draft.", ""])

    for section_name in LOTUS_SCORE_SECTION_ORDER:
        section_title = section_name.replace("_", " ").title()
        content = sections.get(section_name, "").strip()
        lines.extend([f"## {section_title}", "", content or f"No {section_title.lower()} notes entered yet.", ""])

    return "\n".join(lines).strip() + "\n"


def save_structured_note(markdown: str, title: str, lotus_root: Path, subfolder: str = "manual_entries") -> Path:
    lotus_root = ensure_lotus_root(lotus_root)
    target_dir = lotus_root / subfolder
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_title = sorter.sanitize_filename_component(title or "LOTUS note", max_len=90)
    destination = target_dir / f"{safe_title}.md"
    counter = 2
    while destination.exists():
        destination = target_dir / f"{safe_title} [{counter}].md"
        counter += 1
    destination.write_text(markdown, encoding="utf-8")
    return destination


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


def write_dr_sort_feed(
    records: list[object],
    lotus_root: Path,
    run_id: str,
    summary_text: str,
    profile_name: str,
    destination_schema: str,
) -> Path:
    lotus_root = ensure_lotus_root(lotus_root)
    feed_dir = lotus_root / "dr_sort_feed"
    feed_dir.mkdir(parents=True, exist_ok=True)
    feed_path = feed_dir / f"dr_sort_feed_{run_id}.md"

    lines = [
        "---",
        'title: "Dr. Sort Feed"',
        'author: "Dr. Sort-Academic Helper"',
        f"date: {dt.datetime.now().strftime('%Y-%m-%d')}",
        "tags: agency, sorting, feed, governance, archive",
        "---",
        "",
        "# Dr. Sort Feed",
        "",
        f"- Run ID: {run_id}",
        f"- Profile: {profile_name}",
        f"- Destination schema: {destination_schema}",
        f"- Records: {len(records)}",
        "",
        "## Summary",
        "",
        summary_text.strip(),
        "",
        "## Top Records",
        "",
    ]
    for record in records[:20]:
        title = getattr(record, "title", "") or getattr(record, "relative_source", "Untitled")
        category = getattr(record, "category", "")
        doc_type = getattr(record, "doc_type", "")
        year = getattr(record, "year", "")
        duplicate = getattr(record, "duplicate_status", "")
        destination = str(getattr(record, "planned_destination", "") or "")
        lines.extend(
            [
                f"### {title}",
                f"- Category: {category}",
                f"- Type: {doc_type}",
                f"- Year: {year}",
                f"- Duplicate: {duplicate}",
                f"- Proposed destination: {destination}",
                "",
            ]
        )

    feed_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return feed_path
