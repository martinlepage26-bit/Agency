from __future__ import annotations

import argparse
import datetime as dt
import queue
import shutil
import subprocess
import sys
import threading
import traceback
from collections import Counter
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import lotus_core as lotus
import document_sorter as sorter


VIOLET_GEM = "#120E18"
VIOLET_MIST = "#120E18"
SCARLET_ROSE = "#B76046"
MUTED_GOLD = "#C98A2E"
TEAL = "#8E80BE"
TEAL_MIST = "#171123"
INK = "#F1E7D8"
SUBTLE_INK = "#BAA891"
SURFACE = "#221C31"
SURFACE_ALT = "#1A1530"
TREE_BORDER = "#3A2F4A"
DEFAULT_MONITOR_INTERVAL_MS = 15000
LOTUS_UPLOAD_DIR_NAME = "LOTUS_UPLOADS"
SORT_BY_OPTIONS = (
    "Proposed",
    "Source",
    "Category",
    "Type",
    "Year",
    "Author",
    "Title",
    "Duplicate",
    "Language",
    "Confidence",
    "Destination",
)
PROFILE_OPTIONS = (
    "Academic Archive",
    "Administrative Intake",
    "Creative Vault",
    "Mixed Professional",
)
REVIEW_FILTER_OPTIONS = (
    "All Records",
    "Needs Review",
    "Duplicates Only",
    "Low Confidence",
    "Unclear Only",
)
DESTINATION_SCHEMA_OPTIONS = (
    "Category / Type / Year",
    "Category / Year / Type",
    "Category / Author / Year",
)

APP_WINDOW_TITLE = "Dr. Sort-Academic Helper"
APP_HEADER_TITLE = "Dr. Sort-Academic Helper"
APP_HEADER_SUBTITLE = "Institutional-grade document sorting with detailed planning, review control, and LOTUS feed integration."
APP_DIALOG_TITLE = "Dr. Sort-Academic Helper"


def summarize_counts(records: list[sorter.DocumentRecord]) -> tuple[Counter, Counter, Counter]:
    categories = Counter(record.category for record in records)
    types = Counter(record.doc_type for record in records)
    duplicates = Counter(record.duplicate_status for record in records)
    return categories, types, duplicates


def paths_to_text(paths: list[Path]) -> str:
    return "; ".join(str(path) for path in paths)


def parse_input_paths(raw_value: str) -> list[Path]:
    raw_value = raw_value.strip()
    if not raw_value:
        return []
    candidates = [chunk.strip().strip('"') for chunk in raw_value.split(";") if chunk.strip()]
    paths = [Path(candidate).expanduser() for candidate in candidates]
    return [path.resolve() for path in paths if path.exists()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dr. Sort-Academic Helper desktop app")
    parser.add_argument("paths", nargs="*", help="Optional initial files or folders to scan.")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Create the UI, verify core widgets exist, print a short success line, then exit.",
    )
    parser.add_argument(
        "--workflow-self-test",
        action="store_true",
        help="Run a non-interactive app workflow test against the provided paths, then exit.",
    )
    return parser


class DrSortAcademicHelperApp(tk.Tk):
    def __init__(self, initial_paths: list[Path] | None = None) -> None:
        super().__init__()
        self.title(APP_WINDOW_TITLE)
        self.geometry("1540x920")
        self.minsize(1180, 720)
        self.configure(background=VIOLET_MIST)

        self.script_dir = Path(__file__).resolve().parent
        self.output_root = (self.script_dir / sorter.DEFAULT_OUTPUT_DIR).resolve()
        self.quarantine_root = (self.script_dir / sorter.DEFAULT_QUARANTINE_DIR).resolve()
        self.report_root = (self.script_dir / sorter.DEFAULT_REPORT_DIR).resolve()
        self.lotus_root = (self.script_dir / LOTUS_UPLOAD_DIR_NAME).resolve()
        self.identities = list(sorter.DEFAULT_IDENTITIES)
        self.bibliography_path = (self.script_dir / "MASTER BIBLIOGRAPHY.txt").resolve()
        self.default_rules_path = (self.script_dir / sorter.RULES_EXAMPLE_NAME).resolve()

        default_sources = initial_paths or sorter.choose_sources(self.script_dir, [])
        self.source_var = tk.StringVar(value=paths_to_text(default_sources))
        self.profile_var = tk.StringVar(value=PROFILE_OPTIONS[0])
        self.mode_var = tk.StringVar(value="copy")
        self.ocr_var = tk.StringVar(value="auto")
        self.max_pages_var = tk.StringVar(value="5")
        self.destination_schema_var = tk.StringVar(value=DESTINATION_SCHEMA_OPTIONS[0])
        self.review_filter_var = tk.StringVar(value=REVIEW_FILTER_OPTIONS[0])
        self.sort_by_var = tk.StringVar(value="Proposed")
        self.sort_desc_var = tk.BooleanVar(value=False)
        self.recursive_var = tk.BooleanVar(value=True)
        self.similar_dedupe_var = tk.BooleanVar(value=True)
        self.rules_var = tk.StringVar(value=str(self.default_rules_path) if self.default_rules_path.exists() else "")
        self.search_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Ready for controlled scan, review, and sort operations.")
        self.lotus_status_var = tk.StringVar(value="LOTUS is ready to score notes and receive Dr. Sort feeds.")
        self.summary_var = tk.StringVar(
            value="Choose a source, run a scan, review the proposed ledger carefully, then apply the sort when the plan looks right."
        )

        self.sorted_summary_var = tk.StringVar(value="Sorted documents will appear here after you run Sort.")
        self.sorted_records: list[sorter.DocumentRecord] = []

        self.current_sources: list[Path] = default_sources
        self.current_records: list[sorter.DocumentRecord] = []
        self.lotus_notes: list[lotus.LotusNote] = []
        self.latest_report_paths: dict[str, Path] = {}
        self.latest_run_id = ""
        self.last_applied_actions: list[tuple[str, Path, Path]] = []
        self.monitor_enabled = False
        self.monitor_snapshot: tuple[int, int, int] | None = None
        self.busy = False
        self.worker_queue: queue.Queue[tuple[str, object]] = queue.Queue()

        self._configure_style()
        self._build_ui()
        self.sort_by_var.trace_add("write", self._on_sort_settings_changed)
        self.sort_desc_var.trace_add("write", self._on_sort_settings_changed)
        self.review_filter_var.trace_add("write", self._on_sort_settings_changed)
        self.after(200, self._poll_worker_queue)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=VIOLET_MIST, foreground=INK, font=("Segoe UI", 10))
        style.configure("Shell.TFrame", background=VIOLET_MIST)
        style.configure("TFrame", background=VIOLET_MIST)
        style.configure("Card.TFrame", background=SURFACE, relief="solid", borderwidth=1)
        style.configure("TealCard.TFrame", background=TEAL_MIST, relief="solid", borderwidth=1)
        style.configure("Hero.TFrame", background=VIOLET_GEM, relief="solid", borderwidth=1)
        style.configure("HeroStat.TFrame", background=SURFACE_ALT, relief="solid", borderwidth=1)
        style.configure("Toolbar.TFrame", background=SURFACE_ALT, relief="solid", borderwidth=1)
        style.configure("Header.TLabel", background=VIOLET_GEM, foreground=INK, font=("Georgia", 24, "bold"))
        style.configure("HeroSub.TLabel", background=VIOLET_GEM, foreground=SUBTLE_INK, font=("Segoe UI", 10))
        style.configure("HeroStatLabel.TLabel", background=SURFACE_ALT, foreground=MUTED_GOLD, font=("Consolas", 8, "bold"))
        style.configure("HeroStatValue.TLabel", background=SURFACE_ALT, foreground=INK, font=("Segoe UI", 9, "bold"))
        style.configure("Section.TLabel", background=SURFACE_ALT, foreground=INK, font=("Consolas", 8, "bold"))
        style.configure("CardSection.TLabel", background=SURFACE, foreground=INK, font=("Consolas", 8, "bold"))
        style.configure("Summary.TLabel", background=TEAL_MIST, foreground=INK, font=("Segoe UI", 10))
        style.configure("Status.TLabel", background=TEAL_MIST, foreground=TEAL, font=("Segoe UI", 10, "bold"))
        style.configure("Muted.TLabel", background=VIOLET_MIST, foreground=SUBTLE_INK)
        style.configure("WarmMuted.TLabel", background=SURFACE_ALT, foreground=SUBTLE_INK)
        style.configure("Gold.TLabel", background=VIOLET_GEM, foreground=MUTED_GOLD, font=("Consolas", 8, "bold"))
        style.configure("Ledger.TLabel", background=SURFACE, foreground=MUTED_GOLD, font=("Consolas", 8, "bold"))
        style.configure("TealLedger.TLabel", background=TEAL_MIST, foreground=MUTED_GOLD, font=("Consolas", 8, "bold"))
        style.configure(
            "Scan.TButton",
            background=TEAL,
            foreground=INK,
            bordercolor=TEAL,
            lightcolor=TEAL,
            darkcolor=TEAL,
            padding=(14, 10),
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Scan.TButton", background=[("active", "#A79AD3"), ("disabled", "#524963")], foreground=[("disabled", "#8D7CA0")])
        style.configure(
            "Sort.TButton",
            background=SCARLET_ROSE,
            foreground=INK,
            bordercolor=SCARLET_ROSE,
            lightcolor=SCARLET_ROSE,
            darkcolor=SCARLET_ROSE,
            padding=(14, 10),
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Sort.TButton", background=[("active", "#BF664E"), ("disabled", "#5C403B")], foreground=[("disabled", "#B69586")])
        style.configure(
            "GoldAction.TButton",
            background=MUTED_GOLD,
            foreground="#170F0A",
            bordercolor=MUTED_GOLD,
            lightcolor=MUTED_GOLD,
            darkcolor=MUTED_GOLD,
            padding=(13, 10),
            font=("Segoe UI", 10, "bold"),
        )
        style.map("GoldAction.TButton", background=[("active", "#DDB061"), ("disabled", "#66553A")], foreground=[("disabled", "#BDA784")])
        style.configure(
            "Utility.TButton",
            background=SURFACE,
            foreground=INK,
            bordercolor=TREE_BORDER,
            lightcolor=SURFACE,
            darkcolor=SURFACE,
            padding=(11, 8),
        )
        style.map("Utility.TButton", background=[("active", "#2A223B")], foreground=[("active", MUTED_GOLD)])
        style.configure(
            "TEntry",
            fieldbackground=SURFACE_ALT,
            foreground=INK,
            bordercolor=TREE_BORDER,
            lightcolor=TEAL,
            darkcolor=TREE_BORDER,
            padding=8,
        )
        style.configure(
            "TCombobox",
            fieldbackground=SURFACE_ALT,
            background=SURFACE_ALT,
            foreground=INK,
            bordercolor=TREE_BORDER,
            arrowcolor=MUTED_GOLD,
            padding=7,
        )
        style.map("TCombobox", fieldbackground=[("readonly", SURFACE_ALT)], selectbackground=[("readonly", SURFACE_ALT)])
        style.configure("TNotebook", background=VIOLET_MIST, borderwidth=0)
        style.configure("TNotebook.Tab", background=SURFACE_ALT, foreground=SUBTLE_INK, padding=(15, 9), font=("Consolas", 9, "bold"))
        style.map(
            "TNotebook.Tab",
            background=[("selected", SURFACE), ("active", "#2A223B")],
            foreground=[("selected", MUTED_GOLD), ("active", INK)],
        )
        style.configure("Treeview", background=SURFACE_ALT, fieldbackground=SURFACE_ALT, foreground=INK, rowheight=30, bordercolor=TREE_BORDER)
        style.configure("Treeview.Heading", background=VIOLET_GEM, foreground=MUTED_GOLD, font=("Consolas", 8, "bold"))
        style.map("Treeview", background=[("selected", "#2A223B")], foreground=[("selected", INK)])
        style.map("Treeview.Heading", background=[("active", "#221C31")])
        style.configure("Teal.TCheckbutton", background=SURFACE_ALT, foreground=SUBTLE_INK, font=("Segoe UI", 9, "bold"))

    def _build_ui(self) -> None:
        root = ttk.Frame(self, style="Shell.TFrame", padding=20)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root, style="Hero.TFrame", padding=(22, 20))
        header.pack(fill="x", pady=(0, 14))
        ttk.Label(header, text="PREMIUM SORTING SUITE", style="Gold.TLabel").pack(anchor="w")
        ttk.Label(header, text=APP_HEADER_TITLE, style="Header.TLabel").pack(anchor="w", pady=(6, 0))
        ttk.Label(
            header,
            text=APP_HEADER_SUBTITLE,
            style="HeroSub.TLabel",
        ).pack(anchor="w", pady=(4, 0))
        ttk.Label(
            header,
            text="Obsidian governance shell  •  amber metal accents  •  plum review surfaces  •  violet signal glow",
            style="Gold.TLabel",
        ).pack(anchor="w", pady=(8, 0))
        hero_band = ttk.Frame(header, style="Hero.TFrame")
        hero_band.pack(fill="x", pady=(16, 0))
        hero_specs = (
            ("Scope", "Multi-format document intake, metadata extraction, duplicate control, and governed filing."),
            ("Review", "Scan-first workflow with cross reference, masterlist output, and safer pre-move approval."),
            ("Bridge", "LOTUS feed integration for downstream scoring, notes, and interpretive review."),
        )
        for index, (label, value) in enumerate(hero_specs):
            card = ttk.Frame(hero_band, style="HeroStat.TFrame", padding=(14, 12))
            card.grid(row=0, column=index, sticky="nsew", padx=(0, 10) if index < len(hero_specs) - 1 else 0)
            ttk.Label(card, text=label.upper(), style="HeroStatLabel.TLabel").pack(anchor="w")
            ttk.Label(card, text=value, style="HeroStatValue.TLabel", wraplength=360, justify="left").pack(anchor="w", pady=(6, 0))
            hero_band.columnconfigure(index, weight=1)

        controls = ttk.Frame(root, style="Toolbar.TFrame", padding=(18, 16, 18, 14))
        controls.pack(fill="x", pady=(0, 10))

        ttk.Label(controls, text="New files or folders to sort", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        entry = ttk.Entry(controls, textvariable=self.source_var)
        entry.grid(row=1, column=0, columnspan=5, sticky="ew", padx=(0, 8), pady=(6, 8))

        ttk.Button(controls, text="Browse Folder", style="Utility.TButton", command=self.choose_folder).grid(row=1, column=5, padx=(0, 8))
        ttk.Button(controls, text="Browse Files", style="Utility.TButton", command=self.choose_files).grid(row=1, column=6, padx=(0, 8))
        ttk.Button(controls, text="Use Default Inbox", style="Utility.TButton", command=self.use_default_sources).grid(row=1, column=7)

        ttk.Label(controls, text="Sort mode", style="Section.TLabel").grid(row=2, column=0, sticky="w")
        ttk.Combobox(
            controls,
            textvariable=self.mode_var,
            values=("copy", "move"),
            width=12,
            state="readonly",
        ).grid(row=3, column=0, sticky="w", pady=(6, 0))

        ttk.Label(controls, text="OCR", style="Section.TLabel").grid(row=2, column=1, sticky="w")
        ttk.Combobox(
            controls,
            textvariable=self.ocr_var,
            values=("auto", "never"),
            width=12,
            state="readonly",
        ).grid(row=3, column=1, sticky="w", pady=(6, 0))

        ttk.Label(controls, text="Sort results by", style="Section.TLabel").grid(row=2, column=2, sticky="w")
        self.sort_by_combo = ttk.Combobox(
            controls,
            textvariable=self.sort_by_var,
            values=SORT_BY_OPTIONS,
            width=16,
            state="readonly",
        )
        self.sort_by_combo.grid(row=3, column=2, sticky="w", padx=(10, 8), pady=(6, 0))

        self.sort_desc_check = ttk.Checkbutton(
            controls,
            text="Descending",
            variable=self.sort_desc_var,
            style="Teal.TCheckbutton",
        )
        self.sort_desc_check.grid(row=3, column=3, sticky="w", pady=(6, 0))

        self.scan_button = ttk.Button(controls, text="Scan", style="Scan.TButton", command=self.start_scan)
        self.scan_button.grid(row=3, column=4, sticky="w", padx=(10, 8), pady=(6, 0))

        self.crossref_button = ttk.Button(
            controls,
            text="Cross Reference",
            style="Utility.TButton",
            command=self.start_cross_reference,
        )
        self.crossref_button.grid(row=3, column=5, sticky="w", padx=(0, 8), pady=(6, 0))

        self.masterlist_button = ttk.Button(
            controls,
            text="Render Masterlist",
            style="GoldAction.TButton",
            command=self.start_render_masterlist,
        )
        self.masterlist_button.grid(row=3, column=6, sticky="w", padx=(0, 8), pady=(6, 0))

        self.sort_button = ttk.Button(controls, text="Sort", style="Sort.TButton", command=self.start_sort)
        self.sort_button.grid(row=3, column=7, sticky="w", pady=(6, 0))
        self.sort_button.configure(state="disabled")
        self.crossref_button.configure(state="disabled")
        self.masterlist_button.configure(state="disabled")

        ttk.Label(
            controls,
            text=f"Output: {self.output_root}\nDuplicates: {self.quarantine_root}\nReports: {self.report_root}",
            style="WarmMuted.TLabel",
            justify="left",
        ).grid(row=2, column=8, columnspan=2, rowspan=2, sticky="e")

        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=0)
        controls.columnconfigure(2, weight=0)
        controls.columnconfigure(3, weight=0)
        controls.columnconfigure(4, weight=0)
        controls.columnconfigure(5, weight=0)
        controls.columnconfigure(6, weight=0)
        controls.columnconfigure(7, weight=0)
        controls.columnconfigure(8, weight=1)

        premium_frame = ttk.Frame(root, style="Toolbar.TFrame", padding=(18, 12, 18, 12))
        premium_frame.pack(fill="x", pady=(0, 12))
        ttk.Label(premium_frame, text="Rules file", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        self.rules_entry = ttk.Entry(premium_frame, textvariable=self.rules_var)
        self.rules_entry.grid(row=1, column=0, columnspan=3, sticky="ew", padx=(0, 8), pady=(6, 0))
        ttk.Button(premium_frame, text="Browse Rules", style="Utility.TButton", command=self.choose_rules_file).grid(
            row=1, column=3, padx=(0, 14), pady=(6, 0)
        )

        ttk.Label(premium_frame, text="Semantic search", style="Section.TLabel").grid(row=0, column=4, sticky="w")
        self.search_entry = ttk.Entry(premium_frame, textvariable=self.search_var)
        self.search_entry.grid(row=1, column=4, columnspan=2, sticky="ew", padx=(0, 8), pady=(6, 0))
        ttk.Button(premium_frame, text="Search", style="Utility.TButton", command=self.start_search).grid(
            row=1, column=6, padx=(0, 8), pady=(6, 0)
        )
        ttk.Button(premium_frame, text="Clear", style="Utility.TButton", command=self.clear_search).grid(
            row=1, column=7, padx=(0, 14), pady=(6, 0)
        )
        self.monitor_button = ttk.Button(
            premium_frame,
            text="Start Monitor",
            style="Utility.TButton",
            command=self.toggle_monitoring,
        )
        self.monitor_button.grid(row=1, column=8, padx=(0, 8), pady=(6, 0))
        self.undo_button = ttk.Button(
            premium_frame,
            text="Undo Last Sort",
            style="Utility.TButton",
            command=self.start_undo_last_sort,
        )
        self.undo_button.grid(row=1, column=9, pady=(6, 0))
        self.undo_button.configure(state="disabled")

        premium_frame.columnconfigure(0, weight=0)
        premium_frame.columnconfigure(1, weight=0)
        premium_frame.columnconfigure(2, weight=1)
        premium_frame.columnconfigure(3, weight=0)
        premium_frame.columnconfigure(4, weight=0)
        premium_frame.columnconfigure(5, weight=1)
        premium_frame.columnconfigure(6, weight=0)
        premium_frame.columnconfigure(7, weight=0)
        premium_frame.columnconfigure(8, weight=0)
        premium_frame.columnconfigure(9, weight=0)

        ops_frame = ttk.Frame(root, style="Toolbar.TFrame", padding=(18, 12, 18, 12))
        ops_frame.pack(fill="x", pady=(0, 12))
        ttk.Label(ops_frame, text="Professional profile", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            ops_frame,
            textvariable=self.profile_var,
            values=PROFILE_OPTIONS,
            width=22,
            state="readonly",
        ).grid(row=1, column=0, sticky="w", padx=(0, 12), pady=(6, 0))

        ttk.Label(ops_frame, text="Destination schema", style="Section.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Combobox(
            ops_frame,
            textvariable=self.destination_schema_var,
            values=DESTINATION_SCHEMA_OPTIONS,
            width=22,
            state="readonly",
        ).grid(row=1, column=1, sticky="w", padx=(0, 12), pady=(6, 0))

        ttk.Label(ops_frame, text="Review filter", style="Section.TLabel").grid(row=0, column=2, sticky="w")
        ttk.Combobox(
            ops_frame,
            textvariable=self.review_filter_var,
            values=REVIEW_FILTER_OPTIONS,
            width=18,
            state="readonly",
        ).grid(row=1, column=2, sticky="w", padx=(0, 12), pady=(6, 0))

        ttk.Label(ops_frame, text="Max PDF pages", style="Section.TLabel").grid(row=0, column=3, sticky="w")
        ttk.Combobox(
            ops_frame,
            textvariable=self.max_pages_var,
            values=("3", "5", "8", "12", "20"),
            width=10,
            state="readonly",
        ).grid(row=1, column=3, sticky="w", padx=(0, 12), pady=(6, 0))

        ttk.Checkbutton(
            ops_frame,
            text="Recursive Scan",
            variable=self.recursive_var,
            style="Teal.TCheckbutton",
        ).grid(row=1, column=4, sticky="w", padx=(0, 12), pady=(6, 0))

        ttk.Checkbutton(
            ops_frame,
            text="Similar Dedupe",
            variable=self.similar_dedupe_var,
            style="Teal.TCheckbutton",
        ).grid(row=1, column=5, sticky="w", padx=(0, 12), pady=(6, 0))

        ttk.Button(ops_frame, text="Open LOTUS", style="GoldAction.TButton", command=self.open_lotus_app).grid(
            row=1, column=6, sticky="w", padx=(0, 8), pady=(6, 0)
        )
        ttk.Button(ops_frame, text="Feed Current Plan", style="Utility.TButton", command=self.feed_current_plan_to_lotus).grid(
            row=1, column=7, sticky="w", pady=(6, 0)
        )
        ops_frame.columnconfigure(8, weight=1)

        summary_frame = ttk.Frame(root, style="TealCard.TFrame", padding=(18, 16))
        summary_frame.pack(fill="x", pady=(0, 12))
        ttk.Label(summary_frame, text="OPERATIONAL SUMMARY", style="TealLedger.TLabel").pack(anchor="w")
        ttk.Label(summary_frame, textvariable=self.summary_var, wraplength=1480, justify="left", style="Summary.TLabel").pack(anchor="w")
        ttk.Label(summary_frame, textvariable=self.status_var, style="Status.TLabel").pack(anchor="w", pady=(4, 0))

        table_frame = ttk.Frame(root, style="Card.TFrame", padding=(12, 12, 12, 8))
        table_frame.pack(fill="both", expand=True)
        ttk.Label(table_frame, text="PROPOSED SORTING LEDGER", style="Ledger.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))

        columns = (
            "relative_source",
            "category",
            "doc_type",
            "language",
            "year",
            "authors",
            "title",
            "tags",
            "duplicate_status",
            "planned_destination",
        )
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.tree.heading("relative_source", text="Source")
        self.tree.heading("category", text="Category")
        self.tree.heading("doc_type", text="Type")
        self.tree.heading("language", text="Lang")
        self.tree.heading("year", text="Year")
        self.tree.heading("authors", text="Author")
        self.tree.heading("title", text="Title")
        self.tree.heading("tags", text="Tags")
        self.tree.heading("duplicate_status", text="Duplicate")
        self.tree.heading("planned_destination", text="Proposed destination")

        self.tree.column("relative_source", width=230, stretch=False)
        self.tree.column("category", width=120, stretch=False)
        self.tree.column("doc_type", width=150, stretch=False)
        self.tree.column("language", width=58, stretch=False, anchor="center")
        self.tree.column("year", width=62, stretch=False, anchor="center")
        self.tree.column("authors", width=180, stretch=False)
        self.tree.column("title", width=310, stretch=True)
        self.tree.column("tags", width=220, stretch=False)
        self.tree.column("duplicate_status", width=128, stretch=False)
        self.tree.column("planned_destination", width=430, stretch=True)

        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        y_scroll.grid(row=1, column=1, sticky="ns")
        x_scroll.grid(row=2, column=0, sticky="ew")
        table_frame.rowconfigure(1, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree.tag_configure("UNCLEAR", background="#31263A")
        self.tree.tag_configure("SCHOLAR", background="#271F38")
        self.tree.tag_configure("PERSONAL_ADMIN", background="#342328")
        self.tree.tag_configure("PROFESSIONAL", background="#241F2F")
        self.tree.tag_configure("CREATIVE", background="#2E2236")
        self.tree.tag_configure("duplicate_exact", background="#402628")
        self.tree.tag_configure("duplicate_probable", background="#47361F")

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=False, pady=(12, 0))
        self.notebook = notebook

        summary_text_frame = ttk.Frame(notebook)
        log_frame = ttk.Frame(notebook)
        lotus_frame = ttk.Frame(notebook)
        notebook.add(summary_text_frame, text="Report Summary")
        notebook.add(log_frame, text="Activity")
        notebook.add(lotus_frame, text="LOTUS")
        sorted_frame = ttk.Frame(notebook)
        notebook.add(sorted_frame, text="Sorted Documents")
        self._build_sorted_tab(sorted_frame)

        self.report_text = tk.Text(
            summary_text_frame,
            height=10,
            wrap="word",
            bg=SURFACE,
            fg=INK,
            insertbackground=MUTED_GOLD,
            relief="flat",
            highlightthickness=1,
            highlightbackground=TREE_BORDER,
            highlightcolor=TEAL,
        )
        self.report_text.pack(fill="both", expand=True)
        self.report_text.configure(state="disabled")

        self.log_text = tk.Text(
            log_frame,
            height=10,
            wrap="word",
            bg=SURFACE,
            fg=INK,
            insertbackground=SCARLET_ROSE,
            relief="flat",
            highlightthickness=1,
            highlightbackground=TREE_BORDER,
            highlightcolor=MUTED_GOLD,
        )
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")

        lotus_toolbar = ttk.Frame(lotus_frame, style="Toolbar.TFrame", padding=(12, 10))
        lotus_toolbar.pack(fill="x")
        ttk.Label(
            lotus_toolbar,
            text="LOTUS is the standalone score app. It scores uploaded notes and Dr. Sort feed entries for agency, strategy, governance, operational, creative, and meaning signals.",
            style="WarmMuted.TLabel",
            justify="left",
        ).grid(row=0, column=0, columnspan=6, sticky="w")
        ttk.Button(lotus_toolbar, text="Upload to LOTUS", style="GoldAction.TButton", command=self.upload_lotus_files).grid(
            row=1, column=0, padx=(0, 8), pady=(8, 0), sticky="w"
        )
        ttk.Button(lotus_toolbar, text="Refresh LOTUS", style="Utility.TButton", command=self.refresh_lotus_library).grid(
            row=1, column=1, padx=(0, 8), pady=(8, 0), sticky="w"
        )
        ttk.Button(lotus_toolbar, text="Feed Current Plan", style="Utility.TButton", command=self.feed_current_plan_to_lotus).grid(
            row=1, column=2, padx=(0, 8), pady=(8, 0), sticky="w"
        )
        ttk.Button(lotus_toolbar, text="Use LOTUS as Source", style="Utility.TButton", command=self.use_lotus_sources).grid(
            row=1, column=3, padx=(0, 8), pady=(8, 0), sticky="w"
        )
        ttk.Button(lotus_toolbar, text="Scan Selected", style="Scan.TButton", command=self.scan_selected_lotus).grid(
            row=1, column=4, padx=(0, 8), pady=(8, 0), sticky="w"
        )
        ttk.Button(lotus_toolbar, text="Open LOTUS App", style="GoldAction.TButton", command=self.open_lotus_app).grid(
            row=1, column=5, padx=(0, 8), pady=(8, 0), sticky="w"
        )
        ttk.Label(lotus_toolbar, textvariable=self.lotus_status_var, style="Section.TLabel").grid(
            row=1, column=6, sticky="e", pady=(8, 0)
        )
        lotus_toolbar.columnconfigure(6, weight=1)

        lotus_body = ttk.Frame(lotus_frame)
        lotus_body.pack(fill="both", expand=True)

        lotus_table_frame = ttk.Frame(lotus_body, style="Card.TFrame", padding=(10, 10, 10, 6))
        lotus_table_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))
        lotus_columns = ("title", "agency", "creative", "strategic", "modified", "signals", "file")
        self.lotus_tree = ttk.Treeview(lotus_table_frame, columns=lotus_columns, show="headings", height=8)
        self.lotus_tree.heading("title", text="LOTUS note")
        self.lotus_tree.heading("agency", text="Agency")
        self.lotus_tree.heading("creative", text="Creative")
        self.lotus_tree.heading("strategic", text="Strategic")
        self.lotus_tree.heading("modified", text="Modified")
        self.lotus_tree.heading("signals", text="Signals")
        self.lotus_tree.heading("file", text="File")
        self.lotus_tree.column("title", width=280, stretch=True)
        self.lotus_tree.column("agency", width=72, stretch=False, anchor="center")
        self.lotus_tree.column("creative", width=72, stretch=False, anchor="center")
        self.lotus_tree.column("strategic", width=72, stretch=False, anchor="center")
        self.lotus_tree.column("modified", width=140, stretch=False)
        self.lotus_tree.column("signals", width=170, stretch=False)
        self.lotus_tree.column("file", width=220, stretch=True)
        self.lotus_tree.bind("<<TreeviewSelect>>", self._on_lotus_selected)
        lotus_scroll = ttk.Scrollbar(lotus_table_frame, orient="vertical", command=self.lotus_tree.yview)
        self.lotus_tree.configure(yscrollcommand=lotus_scroll.set)
        self.lotus_tree.grid(row=0, column=0, sticky="nsew")
        lotus_scroll.grid(row=0, column=1, sticky="ns")
        lotus_table_frame.rowconfigure(0, weight=1)
        lotus_table_frame.columnconfigure(0, weight=1)

        lotus_preview_frame = ttk.Frame(lotus_body, style="Card.TFrame", padding=(12, 12))
        lotus_preview_frame.pack(side="right", fill="both", expand=True)
        ttk.Label(lotus_preview_frame, text="LOTUS Preview", style="CardSection.TLabel").pack(anchor="w")
        self.lotus_preview_text = tk.Text(
            lotus_preview_frame,
            wrap="word",
            bg=SURFACE,
            fg=INK,
            insertbackground=MUTED_GOLD,
            relief="flat",
            highlightthickness=1,
            highlightbackground=TREE_BORDER,
            highlightcolor=TEAL,
        )
        self.lotus_preview_text.pack(fill="both", expand=True, pady=(8, 0))
        self.lotus_preview_text.configure(state="disabled")
        self.refresh_lotus_library()

    def choose_folder(self) -> None:
        chosen = filedialog.askdirectory(title="Choose a folder to scan")
        if not chosen:
            return
        self.current_sources = [Path(chosen).resolve()]
        self.source_var.set(paths_to_text(self.current_sources))

    def choose_files(self) -> None:
        chosen = filedialog.askopenfilenames(
            title="Choose files to scan",
            filetypes=[
                ("Supported documents", "*.pdf *.docx *.doc *.txt *.md"),
                ("PDF files", "*.pdf"),
                ("Word documents", "*.docx *.doc"),
                ("Text and Markdown", "*.txt *.md"),
                ("All files", "*.*"),
            ],
        )
        if not chosen:
            return
        self.current_sources = [Path(path).resolve() for path in chosen]
        self.source_var.set(paths_to_text(self.current_sources))

    def _ensure_lotus_root(self) -> Path:
        return lotus.ensure_lotus_root(self.lotus_root)

    def _selected_lotus_paths(self) -> list[Path]:
        selected: list[Path] = []
        for item in self.lotus_tree.selection():
            raw_path = self.lotus_tree.item(item, "values")[-1]
            candidate = self.lotus_root / raw_path
            if candidate.exists():
                selected.append(candidate.resolve())
        return selected

    def _selected_lotus_note(self) -> lotus.LotusNote | None:
        selection = self.lotus_tree.selection()
        if not selection:
            return None
        index = self.lotus_tree.index(selection[0])
        if 0 <= index < len(self.lotus_notes):
            return self.lotus_notes[index]
        return None

    def refresh_lotus_library(self) -> None:
        for item in self.lotus_tree.get_children():
            self.lotus_tree.delete(item)
        self.lotus_notes = lotus.load_lotus_notes(self._ensure_lotus_root())
        for note in self.lotus_notes:
            relative_name = str(note.path.relative_to(self.lotus_root))
            self.lotus_tree.insert(
                "",
                "end",
                values=(
                    note.title,
                    note.agency_score,
                    note.creative_score,
                    note.strategic_score,
                    note.modified_iso,
                    ", ".join(note.signals[:4]),
                    relative_name,
                ),
            )
        feed_count = sum(1 for note in self.lotus_notes if "dr_sort_feed" in note.path.parts)
        self.lotus_status_var.set(
            f"LOTUS has {len(self.lotus_notes)} note(s), including {feed_count} Dr. Sort feed item(s)."
        )
        if self.lotus_notes:
            self._show_lotus_note(self.lotus_notes[0])
        else:
            self._set_lotus_preview("No LOTUS notes yet.")

    def upload_lotus_files(self) -> None:
        chosen = filedialog.askopenfilenames(
            title="Upload markdown or text files to LOTUS",
            filetypes=[("LOTUS files", "*.md *.txt"), ("Markdown files", "*.md"), ("Text files", "*.txt")],
        )
        if not chosen:
            return
        imported = lotus.import_notes([Path(raw_path).resolve() for raw_path in chosen], self._ensure_lotus_root())
        self.refresh_lotus_library()
        self.summary_var.set(f"LOTUS uploaded {len(imported)} file(s).")
        self.status_var.set("LOTUS upload complete.")
        self._append_log(f"LOTUS uploaded {len(imported)} markdown/text file(s).")

    def use_lotus_sources(self) -> None:
        lotus_root = self._ensure_lotus_root()
        self.current_sources = [lotus_root]
        self.source_var.set(paths_to_text(self.current_sources))
        self.summary_var.set("LOTUS is loaded as the current source. Click Scan to review the uploaded notes.")
        self.status_var.set("LOTUS source loaded.")

    def scan_selected_lotus(self) -> None:
        selected = self._selected_lotus_paths()
        if not selected:
            messagebox.showinfo(APP_DIALOG_TITLE, "Select at least one LOTUS markdown or text file first.")
            return
        self.current_sources = selected
        self.source_var.set(paths_to_text(self.current_sources))
        self.start_scan()

    def open_lotus_app(self) -> None:
        launcher = (self.script_dir / "LOTUS.bat").resolve()
        if not launcher.exists():
            messagebox.showerror(APP_DIALOG_TITLE, "LOTUS launcher was not found.")
            return
        try:
            subprocess.Popen([str(launcher)], cwd=str(self.script_dir))
        except Exception as exc:
            messagebox.showerror(APP_DIALOG_TITLE, str(exc))

    def feed_current_plan_to_lotus(self) -> None:
        if not self.current_records:
            messagebox.showinfo(APP_DIALOG_TITLE, "Scan files first so there is a current plan to feed into LOTUS.")
            return
        run_id = self.latest_run_id or sorter.timestamp()
        summary_text = self._lotus_feed_summary_text()
        feed_path = lotus.write_dr_sort_feed(
            self.current_records,
            lotus_root=self._ensure_lotus_root(),
            run_id=run_id,
            summary_text=summary_text,
            profile_name=self.profile_var.get(),
            destination_schema=self.destination_schema_var.get(),
        )
        self.refresh_lotus_library()
        self.summary_var.set(f"Current Dr. Sort plan was fed into LOTUS: {feed_path.name}")
        self.status_var.set("LOTUS feed created.")
        self._append_log(f"LOTUS feed created: {feed_path}")

    def _on_lotus_selected(self, _event: object) -> None:
        note = self._selected_lotus_note()
        if note is not None:
            self._show_lotus_note(note)

    def _show_lotus_note(self, note: lotus.LotusNote) -> None:
        preview = [
            f"Title: {note.title}",
            f"Agency Score: {note.agency_score}",
            f"Creative Meaning: {note.creative_score}",
            f"Strategic Signal: {note.strategic_score}",
            f"Governance Signal: {note.governance_score}",
            f"Operational Signal: {note.operational_score}",
            f"Meaning Signal: {note.meaning_score}",
            f"Signals: {', '.join(note.signals) if note.signals else 'none'}",
            f"File: {note.path}",
            "",
            note.excerpt or note.text[:2000] or "No preview available.",
        ]
        self._set_lotus_preview("\n".join(preview))

    def _set_lotus_preview(self, value: str) -> None:
        self.lotus_preview_text.configure(state="normal")
        self.lotus_preview_text.delete("1.0", "end")
        self.lotus_preview_text.insert("1.0", value)
        self.lotus_preview_text.configure(state="disabled")

    def _build_sorted_tab(self, parent: ttk.Frame) -> None:
        header = ttk.Frame(parent)
        header.pack(fill="x", pady=(0, 8))
        ttk.Label(header, text="SORTED DOCUMENTS VIEWER", style="Ledger.TLabel").pack(anchor="w")
        ttk.Label(header, textvariable=self.sorted_summary_var, style="WarmMuted.TLabel", wraplength=1160, justify="left").pack(anchor="w")

        viewer_frame = ttk.Frame(parent)
        viewer_frame.pack(fill="both", expand=True)

        table_frame = ttk.Frame(viewer_frame, style="Card.TFrame", padding=(10, 10, 10, 6))
        table_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))
        columns = ("source", "action", "destination", "category", "doc_type", "modified")
        self.sorted_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=10)
        self.sorted_tree.heading("source", text="Source file")
        self.sorted_tree.heading("action", text="Action")
        self.sorted_tree.heading("destination", text="Destination")
        self.sorted_tree.heading("category", text="Category")
        self.sorted_tree.heading("doc_type", text="Type")
        self.sorted_tree.heading("modified", text="Modified")
        self.sorted_tree.column("source", width=260, stretch=True)
        self.sorted_tree.column("action", width=90, stretch=False, anchor="center")
        self.sorted_tree.column("destination", width=340, stretch=True)
        self.sorted_tree.column("category", width=140, stretch=False)
        self.sorted_tree.column("doc_type", width=130, stretch=False)
        self.sorted_tree.column("modified", width=110, stretch=False)
        self.sorted_tree.bind("<<TreeviewSelect>>", self._on_sorted_selected)
        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.sorted_tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.sorted_tree.xview)
        self.sorted_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.sorted_tree.grid(row=1, column=0, sticky="nsew")
        y_scroll.grid(row=1, column=1, sticky="ns")
        x_scroll.grid(row=2, column=0, sticky="ew")
        table_frame.rowconfigure(1, weight=1)
        table_frame.columnconfigure(0, weight=1)
        for tag, color in (
            ("UNCLEAR", "#31263A"),
            ("SCHOLAR", "#271F38"),
            ("PERSONAL_ADMIN", "#342328"),
            ("PROFESSIONAL", "#241F2F"),
            ("CREATIVE", "#2E2236"),
        ):
            self.sorted_tree.tag_configure(tag, background=color)

        preview_frame = ttk.Frame(viewer_frame, style="Card.TFrame", padding=(12, 12))
        preview_frame.pack(side="right", fill="both", expand=True)
        ttk.Label(preview_frame, text="Document details", style="CardSection.TLabel").pack(anchor="w")
        self.sorted_preview_text = tk.Text(
            preview_frame,
            wrap="word",
            bg=SURFACE,
            fg=INK,
            insertbackground=MUTED_GOLD,
            relief="flat",
            highlightthickness=1,
            highlightbackground=TREE_BORDER,
            highlightcolor=TEAL,
        )
        preview_scroll = ttk.Scrollbar(preview_frame, orient="vertical", command=self.sorted_preview_text.yview)
        preview_scroll.pack(side="right", fill="y")
        self.sorted_preview_text.configure(yscrollcommand=preview_scroll.set)
        self.sorted_preview_text.pack(fill="both", expand=True, pady=(8, 0))
        self._set_sorted_preview("No sorted documents yet. Run Sort to populate this viewer.")

    def choose_rules_file(self) -> None:
        chosen = filedialog.askopenfilename(
            title="Choose a rules file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if chosen:
            self.rules_var.set(str(Path(chosen).resolve()))

    def use_default_sources(self) -> None:
        self.current_sources = sorter.choose_sources(self.script_dir, [])
        self.source_var.set(paths_to_text(self.current_sources))

    def start_scan(self) -> None:
        if self.busy:
            return
        sources = self._resolve_sources()
        if not sources:
            messagebox.showerror(APP_DIALOG_TITLE, "Choose at least one existing file or folder to scan.")
            return
        self.current_sources = sources
        self.current_records = []
        self.latest_report_paths = {}
        self._clear_tree()
        self._set_report_text("")
        self._set_busy(True)
        self.summary_var.set("Scanning and building a proposed sorting plan...")
        self.status_var.set("Scanning in progress.")
        self._append_log(f"Starting scan for {len(sources)} source path(s).")
        threading.Thread(target=self._scan_worker, args=(sources,), daemon=True).start()

    def start_sort(self) -> None:
        if self.busy:
            return
        if not self.current_records:
            messagebox.showinfo(APP_DIALOG_TITLE, "Scan files first so there is a plan to apply.")
            return
        mode = self.mode_var.get().strip().lower()
        if mode == "move":
            confirmed = messagebox.askyesno(
                APP_DIALOG_TITLE,
                "Move mode will remove files from the source location after sorting. Continue?",
            )
            if not confirmed:
                return
        self._set_busy(True)
        self.summary_var.set("Applying the proposed sorting plan...")
        self.status_var.set("Sorting in progress.")
        self._append_log(f"Applying plan in {mode} mode.")
        threading.Thread(target=self._sort_worker, args=(mode,), daemon=True).start()

    def start_search(self) -> None:
        if not self.current_records:
            messagebox.showinfo(APP_DIALOG_TITLE, "Scan files first so there is something to search.")
            return
        query = self.search_var.get().strip()
        if not query:
            self._refresh_tree(self._current_display_records())
            self.summary_var.set("Search cleared. Showing the full proposed plan.")
            return
        matches = sorter.search_records(self._current_display_records(), query)
        records = [record for record, _score in matches]
        self._refresh_tree(records)
        self.summary_var.set(f"Semantic search found {len(records)} result(s) for: {query}")
        self.status_var.set("Semantic search complete.")

    def clear_search(self) -> None:
        self.search_var.set("")
        if self.current_records:
            self._refresh_tree(self._current_display_records())
            self.summary_var.set("Showing the full proposed plan.")
            self.status_var.set("Search cleared.")

    def start_cross_reference(self) -> None:
        if self.busy:
            return
        if not self.current_records:
            messagebox.showinfo(APP_DIALOG_TITLE, "Scan files first so there is a record set to cross-reference.")
            return
        self._set_busy(True)
        self.summary_var.set("Rendering the cross-reference report...")
        self.status_var.set("Cross reference in progress.")
        self._append_log("Rendering cross-reference report.")
        threading.Thread(target=self._cross_reference_worker, daemon=True).start()

    def start_render_masterlist(self) -> None:
        if self.busy:
            return
        if not self.current_records:
            messagebox.showinfo(APP_DIALOG_TITLE, "Scan files first so there is a record set for the masterlist.")
            return
        self._set_busy(True)
        self.summary_var.set("Rendering the masterlist...")
        self.status_var.set("Masterlist rendering in progress.")
        self._append_log("Rendering masterlist.")
        threading.Thread(target=self._masterlist_worker, daemon=True).start()

    def start_undo_last_sort(self) -> None:
        if self.busy:
            return
        if not self.last_applied_actions:
            messagebox.showinfo(APP_DIALOG_TITLE, "There is no completed sort action to undo yet.")
            return
        confirmed = messagebox.askyesno(APP_DIALOG_TITLE, "Undo the last completed sort action?")
        if not confirmed:
            return
        self._set_busy(True)
        self.summary_var.set("Undoing the last sort action...")
        self.status_var.set("Undo in progress.")
        self._append_log("Undoing the last sort action.")
        threading.Thread(target=self._undo_worker, daemon=True).start()

    def toggle_monitoring(self) -> None:
        if self.busy:
            return
        self.monitor_enabled = not self.monitor_enabled
        if self.monitor_enabled:
            self.monitor_snapshot = self._source_snapshot()
            self.status_var.set("Real-time monitoring enabled.")
            self._append_log("Real-time monitoring enabled.")
            self.after(DEFAULT_MONITOR_INTERVAL_MS, self._monitor_tick)
        else:
            self.status_var.set("Real-time monitoring stopped.")
            self._append_log("Real-time monitoring stopped.")
        self._sync_action_states()

    def _resolve_sources(self) -> list[Path]:
        parsed = parse_input_paths(self.source_var.get())
        if parsed:
            return parsed
        return sorter.choose_sources(self.script_dir, [])

    def _resolve_rules(self) -> Path | None:
        raw = self.rules_var.get().strip()
        if not raw:
            return None
        candidate = Path(raw).expanduser()
        return candidate.resolve() if candidate.exists() else None

    def _source_snapshot(self) -> tuple[int, int, int]:
        sources = self._resolve_sources()
        discovered = sorter.discover_files(sources, recursive=self.recursive_var.get(), limit=None)
        count = 0
        total_size = 0
        latest_mtime = 0
        for _source_root, source_path in discovered:
            stat = source_path.stat()
            count += 1
            total_size += stat.st_size
            latest_mtime = max(latest_mtime, int(stat.st_mtime))
        return count, total_size, latest_mtime

    def _monitor_tick(self) -> None:
        if not self.monitor_enabled:
            return
        try:
            snapshot = self._source_snapshot()
            if self.monitor_snapshot is not None and snapshot != self.monitor_snapshot and not self.busy:
                self.monitor_snapshot = snapshot
                self._append_log("Folder change detected. Auto-scanning watched sources.")
                self.start_scan()
            else:
                self.monitor_snapshot = snapshot
        except Exception as exc:
            self._append_log(f"monitor_error: {exc}")
        self.after(DEFAULT_MONITOR_INTERVAL_MS, self._monitor_tick)

    def _on_sort_settings_changed(self, *_args: object) -> None:
        if self.current_records:
            self._refresh_tree(self._current_display_records())

    def _scan_worker(self, sources: list[Path]) -> None:
        try:
            run_id = sorter.timestamp()
            rules = sorter.load_plain_english_rules(self._resolve_rules())
            records = sorter.scan_documents(
                source_roots=sources,
                max_pages=self._max_pages_value(),
                ocr_mode=self.ocr_var.get().strip().lower(),
                recursive=self.recursive_var.get(),
                limit=None,
                identities=self.identities,
                script_dir=self.script_dir,
                rules=rules,
                progress_callback=lambda message: self.worker_queue.put(("progress", message)),
            )
            sorter.mark_duplicates(records, similar_dedupe=self.similar_dedupe_var.get())
            sorter.plan_destinations(
                records,
                output_root=self.output_root,
                quarantine_root=self.quarantine_root,
                destination_schema=self._destination_schema_key(),
            )
            sorter.apply_plan(records, mode="scan", progress_callback=lambda _message: None)
            csv_path, json_path, summary_path = sorter.write_reports(records, report_root=self.report_root, run_id=run_id)
            payload = {
                "records": records,
                "run_id": run_id,
                "csv_path": csv_path,
                "json_path": json_path,
                "summary_path": summary_path,
            }
            self.worker_queue.put(("scan_complete", payload))
        except Exception:
            self.worker_queue.put(("error", traceback.format_exc()))

    def _sort_worker(self, mode: str) -> None:
        try:
            sorter.plan_destinations(
                self.current_records,
                output_root=self.output_root,
                quarantine_root=self.quarantine_root,
                destination_schema=self._destination_schema_key(),
            )
            sorter.apply_plan(
                self.current_records,
                mode=mode,
                progress_callback=lambda message: self.worker_queue.put(("progress", message)),
            )
            run_id = sorter.timestamp()
            csv_path, json_path, summary_path = sorter.write_reports(
                self.current_records,
                report_root=self.report_root,
                run_id=run_id,
            )
            payload = {
                "records": self.current_records,
                "run_id": run_id,
                "csv_path": csv_path,
                "json_path": json_path,
                "summary_path": summary_path,
                "mode": mode,
            }
            self.worker_queue.put(("sort_complete", payload))
        except Exception:
            self.worker_queue.put(("error", traceback.format_exc()))

    def _cross_reference_worker(self) -> None:
        try:
            run_id = sorter.timestamp()
            csv_path, json_path, summary_path = sorter.write_cross_reference_report(
                self.current_records,
                report_root=self.report_root,
                run_id=run_id,
                bibliography_path=self.bibliography_path if self.bibliography_path.exists() else None,
            )
            self.worker_queue.put(
                (
                    "crossref_complete",
                    {
                        "run_id": run_id,
                        "csv_path": csv_path,
                        "json_path": json_path,
                        "summary_path": summary_path,
                    },
                )
            )
        except Exception:
            self.worker_queue.put(("error", traceback.format_exc()))

    def _masterlist_worker(self) -> None:
        try:
            run_id = sorter.timestamp()
            csv_path, markdown_path, text_path = sorter.render_masterlist(
                self.current_records,
                report_root=self.report_root,
                run_id=run_id,
            )
            self.worker_queue.put(
                (
                    "masterlist_complete",
                    {
                        "run_id": run_id,
                        "csv_path": csv_path,
                        "markdown_path": markdown_path,
                        "text_path": text_path,
                    },
                )
            )
        except Exception:
            self.worker_queue.put(("error", traceback.format_exc()))

    def _undo_worker(self) -> None:
        undone = 0
        for action, source_path, destination in reversed(self.last_applied_actions):
            try:
                if action == "COPIED" and destination.exists():
                    destination.unlink()
                    undone += 1
                elif action == "MOVED" and destination.exists():
                    source_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(destination), str(source_path))
                    undone += 1
            except Exception as exc:
                self.worker_queue.put(("error", traceback.format_exc()))
                return
        self.worker_queue.put(("undo_complete", {"undone": undone}))

    def _poll_worker_queue(self) -> None:
        try:
            while True:
                event, payload = self.worker_queue.get_nowait()
                if event == "progress":
                    self.status_var.set(str(payload))
                    self._append_log(str(payload))
                elif event == "scan_complete":
                    self._finish_scan(payload)
                elif event == "sort_complete":
                    self._finish_sort(payload)
                elif event == "crossref_complete":
                    self._finish_cross_reference(payload)
                elif event == "masterlist_complete":
                    self._finish_masterlist(payload)
                elif event == "undo_complete":
                    self._finish_undo(payload)
                elif event == "error":
                    self._set_busy(False)
                    self.status_var.set("A processing error occurred.")
                    self._append_log(str(payload))
                    messagebox.showerror(APP_DIALOG_TITLE, str(payload))
        except queue.Empty:
            pass
        self.after(200, self._poll_worker_queue)

    def _finish_scan(self, payload: dict[str, object]) -> None:
        records = payload["records"]
        if not isinstance(records, list):
            return
        self.latest_run_id = str(payload["run_id"])
        self.current_records = records
        self.last_applied_actions = []
        self.latest_report_paths = {
            "csv": payload["csv_path"],
            "json": payload["json_path"],
            "summary": payload["summary_path"],
        }
        self._refresh_tree(self._current_display_records())
        summary = self._build_summary_text(
            records,
            run_id=str(payload["run_id"]),
            summary_path=Path(payload["summary_path"]),
            csv_path=Path(payload["csv_path"]),
            json_path=Path(payload["json_path"]),
            mode="scan",
        )
        self.summary_var.set(
            f"Scan complete for {self.profile_var.get()}. Review the proposed destinations below, then click Sort to apply the plan using {self.destination_schema_var.get()}."
        )
        self.status_var.set(f"Scan complete. {len(records)} document(s) evaluated.")
        self._set_report_text(summary)
        self._refresh_sorted_viewer([])
        self.monitor_snapshot = self._source_snapshot()
        self._set_busy(False)

    def _finish_sort(self, payload: dict[str, object]) -> None:
        records = payload["records"]
        if not isinstance(records, list):
            return
        self.latest_run_id = str(payload["run_id"])
        self.latest_report_paths = {
            "csv": payload["csv_path"],
            "json": payload["json_path"],
            "summary": payload["summary_path"],
        }
        self.last_applied_actions = [
            (record.action, record.source_path, record.planned_destination)
            for record in records
            if record.action in {"COPIED", "MOVED"} and record.planned_destination is not None
        ]
        self._refresh_tree(self._current_display_records())
        summary = self._build_summary_text(
            records,
            run_id=str(payload["run_id"]),
            summary_path=Path(payload["summary_path"]),
            csv_path=Path(payload["csv_path"]),
            json_path=Path(payload["json_path"]),
            mode=str(payload["mode"]),
        )
        undo_note = " Undo Last Sort is available." if self.last_applied_actions else ""
        self.summary_var.set(
            f"Sort complete. Files were processed in {payload['mode']} mode under {self.profile_var.get()} with {self.destination_schema_var.get()}.{undo_note}"
        )
        self.status_var.set("Sorting complete.")
        self._set_report_text(summary)
        self._refresh_sorted_viewer(records)
        self._set_busy(False)

    def _finish_cross_reference(self, payload: dict[str, object]) -> None:
        self.latest_report_paths.update(
            {
                "crossref_csv": payload["csv_path"],
                "crossref_json": payload["json_path"],
                "crossref_summary": payload["summary_path"],
            }
        )
        summary_path = Path(payload["summary_path"])
        viewer_text = self._read_text_file(summary_path)
        viewer_text += f"\n\nCSV: {payload['csv_path']}\nJSON: {payload['json_path']}"
        self.summary_var.set("Cross-reference report ready.")
        self.status_var.set("Cross reference complete.")
        self._set_report_text(viewer_text)
        self._set_busy(False)

    def _finish_masterlist(self, payload: dict[str, object]) -> None:
        self.latest_report_paths.update(
            {
                "masterlist_csv": payload["csv_path"],
                "masterlist_markdown": payload["markdown_path"],
                "masterlist_text": payload["text_path"],
            }
        )
        text_path = Path(payload["text_path"])
        viewer_text = self._read_text_file(text_path)
        viewer_text += f"\nCSV: {payload['csv_path']}\nMarkdown: {payload['markdown_path']}"
        self.summary_var.set("Masterlist rendered.")
        self.status_var.set("Masterlist complete.")
        self._set_report_text(viewer_text)
        self._set_busy(False)

    def _finish_undo(self, payload: dict[str, object]) -> None:
        undone = int(payload.get("undone", 0))
        self.last_applied_actions = []
        for record in self.current_records:
            if record.action == "COPIED":
                record.action = "UNDO_COPIED"
            elif record.action == "MOVED":
                record.action = "UNDO_MOVED"
        self._refresh_tree(self._current_display_records())
        self.monitor_snapshot = self._source_snapshot()
        self.summary_var.set(f"Undo complete. Reverted {undone} action(s).")
        self.status_var.set("Undo complete.")
        self._append_log(f"Undo complete: {undone} action(s) reverted.")
        self._refresh_sorted_viewer([])
        self._set_busy(False)

    def _build_summary_text(
        self,
        records: list[sorter.DocumentRecord],
        run_id: str,
        summary_path: Path,
        csv_path: Path,
        json_path: Path,
        mode: str,
    ) -> str:
        categories, types, duplicates = summarize_counts(records)
        lines = [
            f"Run ID: {run_id}",
            f"Mode: {mode}",
            f"Sources: {paths_to_text(self.current_sources)}",
            f"Output root: {self.output_root}",
            f"Duplicate quarantine: {self.quarantine_root}",
            f"Reports: {summary_path}",
            f"Profile: {self.profile_var.get()}",
            f"Destination schema: {self.destination_schema_var.get()}",
            f"Recursive scan: {self.recursive_var.get()}",
            f"Similar dedupe: {self.similar_dedupe_var.get()}",
            f"Max PDF pages: {self._max_pages_value()}",
            "",
            f"Documents scanned: {len(records)}",
            f"Kept: {duplicates.get('keep', 0)}",
            f"Exact duplicates: {duplicates.get('duplicate_exact', 0)}",
            f"Probable duplicates: {duplicates.get('duplicate_probable', 0)}",
            f"Tagged records: {sum(1 for record in records if record.tags)}",
            f"Rule matches: {sum(len(record.matched_rules) for record in records)}",
            "",
            "By category:",
        ]
        rules_path = self._resolve_rules()
        if rules_path:
            lines.extend(["", f"Rules file: {rules_path}"])
        lines.extend(f"  {key}: {value}" for key, value in sorted(categories.items()))
        lines.append("")
        lines.append("By type:")
        lines.extend(f"  {key}: {value}" for key, value in sorted(types.items()))
        lines.append("")
        lines.append(f"Manifest CSV: {csv_path}")
        lines.append(f"Manifest JSON: {json_path}")
        return "\n".join(lines)

    def _refresh_tree(self, records: list[sorter.DocumentRecord]) -> None:
        self._clear_tree()
        sorted_records = self._sort_records(records)
        for record in sorted_records:
            values = (
                record.relative_source,
                record.category,
                record.doc_type,
                record.language,
                record.year,
                "; ".join(record.authors),
                record.title,
                "; ".join(record.tags[:6]),
                record.duplicate_status,
                str(record.planned_destination or ""),
            )
            tag = record.duplicate_status if record.duplicate_status != "keep" else record.category
            self.tree.insert("", "end", values=values, tags=(tag,))

    def _clear_tree(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _set_report_text(self, value: str) -> None:
        self.report_text.configure(state="normal")
        self.report_text.delete("1.0", "end")
        self.report_text.insert("1.0", value)
        self.report_text.configure(state="disabled")

    def _refresh_sorted_viewer(self, records: list[sorter.DocumentRecord] | None = None) -> None:
        if not hasattr(self, "sorted_tree"):
            return
        if records is None:
            records = [
                record
                for record in self.current_records
                if record.action in {"COPIED", "MOVED"} and record.planned_destination
            ]
        self.sorted_records = list(records)
        for item in self.sorted_tree.get_children():
            self.sorted_tree.delete(item)
        for record in self.sorted_records:
            values = (
                record.relative_source,
                record.action,
                str(record.planned_destination or ""),
                record.category,
                record.doc_type,
                record.modified_iso,
            )
            tag = record.category or ""
            if tag:
                self.sorted_tree.insert("", "end", values=values, tags=(tag,))
            else:
                self.sorted_tree.insert("", "end", values=values)
        if self.sorted_records:
            first_item = self.sorted_tree.get_children()[0]
            self.sorted_tree.selection_set(first_item)
            self.sorted_tree.focus(first_item)
            self._show_sorted_document(self.sorted_records[0])
            last_action = self.sorted_records[-1].action
            self.sorted_summary_var.set(f"{len(self.sorted_records)} sorted document(s). Last action: {last_action}.")
        else:
            self.sorted_summary_var.set("Sorted documents will appear here after you run Sort.")
            self._set_sorted_preview("No sorted documents yet. Run Sort to populate this viewer.")

    def _on_sorted_selected(self, _event: object) -> None:
        selection = self.sorted_tree.selection()
        if not selection:
            return
        index = self.sorted_tree.index(selection[0])
        if 0 <= index < len(self.sorted_records):
            self._show_sorted_document(self.sorted_records[index])

    def _show_sorted_document(self, record: sorter.DocumentRecord) -> None:
        authors = ", ".join(record.authors) if record.authors else "unknown"
        tags = ", ".join(record.tags) if record.tags else "none"
        reasoning = "; ".join(record.reasoning) if record.reasoning else "none"
        preview = [
            f"Title: {record.title or record.source_path.name}",
            f"Authors: {authors}",
            f"Category: {record.category}",
            f"Type: {record.doc_type}",
            f"Action: {record.action}",
            f"Source: {record.source_path}",
            f"Destination: {record.planned_destination or 'None'}",
            f"Modified: {record.modified_iso}",
            f"Confidence: {record.type_confidence}",
            f"Tags: {tags}",
            f"Reasoning: {reasoning}",
            f"SHA256: {record.sha256}",
        ]
        self._set_sorted_preview("\\n".join(preview))

    def _set_sorted_preview(self, value: str) -> None:
        self.sorted_preview_text.configure(state="normal")
        self.sorted_preview_text.delete("1.0", "end")
        self.sorted_preview_text.insert("1.0", value)
        self.sorted_preview_text.configure(state="disabled")

    def _append_log(self, value: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", value.rstrip() + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _read_text_file(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="latin-1", errors="replace")

    def _current_display_records(self) -> list[sorter.DocumentRecord]:
        records = self.current_records
        filter_name = self.review_filter_var.get()
        if filter_name == "Needs Review":
            records = [record for record in records if record.duplicate_status != "keep" or record.category == "UNCLEAR" or record.type_confidence < 10]
        elif filter_name == "Duplicates Only":
            records = [record for record in records if record.duplicate_status != "keep"]
        elif filter_name == "Low Confidence":
            records = [record for record in records if record.type_confidence < 10]
        elif filter_name == "Unclear Only":
            records = [record for record in records if record.category == "UNCLEAR" or record.doc_type == "ocr_needed"]
        query = self.search_var.get().strip()
        if not query:
            return records
        return [record for record, _score in sorter.search_records(records, query)]

    def _max_pages_value(self) -> int:
        raw = self.max_pages_var.get().strip()
        try:
            return max(1, int(raw))
        except ValueError:
            return 5

    def _destination_schema_key(self) -> str:
        mapping = {
            "Category / Type / Year": "category_type_year",
            "Category / Year / Type": "category_year_type",
            "Category / Author / Year": "category_author_year",
        }
        return mapping.get(self.destination_schema_var.get(), "category_type_year")

    def _lotus_feed_summary_text(self) -> str:
        categories, types, duplicates = summarize_counts(self.current_records)
        lines = [
            f"Profile: {self.profile_var.get()}",
            f"Mode: {self.mode_var.get()}",
            f"Destination schema: {self.destination_schema_var.get()}",
            f"Review filter: {self.review_filter_var.get()}",
            f"Recursive scan: {self.recursive_var.get()}",
            f"Similar dedupe: {self.similar_dedupe_var.get()}",
            "",
            f"Records: {len(self.current_records)}",
            f"Kept: {duplicates.get('keep', 0)}",
            f"Exact duplicates: {duplicates.get('duplicate_exact', 0)}",
            f"Probable duplicates: {duplicates.get('duplicate_probable', 0)}",
            "",
            "Category counts:",
        ]
        lines.extend(f"- {key}: {value}" for key, value in sorted(categories.items()))
        lines.append("")
        lines.append("Type counts:")
        lines.extend(f"- {key}: {value}" for key, value in sorted(types.items()))
        return "\n".join(lines)

    def _sort_records(self, records: list[sorter.DocumentRecord]) -> list[sorter.DocumentRecord]:
        sort_by = self.sort_by_var.get()
        reverse = self.sort_desc_var.get()
        if sort_by == "Source":
            key_func = lambda record: (record.relative_source.lower(), record.title.lower())
        elif sort_by == "Category":
            key_func = lambda record: (record.category, record.doc_type, record.year or "9999", record.title.lower())
        elif sort_by == "Type":
            key_func = lambda record: (record.doc_type, record.category, record.year or "9999", record.title.lower())
        elif sort_by == "Year":
            key_func = lambda record: (record.year or "9999", record.title.lower(), record.relative_source.lower())
        elif sort_by == "Author":
            key_func = lambda record: (record.primary_author.lower(), record.year or "9999", record.title.lower())
        elif sort_by == "Title":
            key_func = lambda record: (record.title.lower(), record.primary_author.lower(), record.year or "9999")
        elif sort_by == "Duplicate":
            key_func = lambda record: (record.duplicate_status, record.duplicate_group, record.title.lower())
        elif sort_by == "Language":
            key_func = lambda record: (record.language, record.category, record.title.lower())
        elif sort_by == "Confidence":
            key_func = lambda record: (record.type_confidence, record.category, record.title.lower())
        elif sort_by == "Destination":
            key_func = lambda record: (str(record.planned_destination or "").lower(), record.title.lower())
        else:
            key_func = lambda record: (
                str(record.planned_destination or "").lower(),
                record.duplicate_status != "keep",
                record.title.lower(),
            )
        return sorted(records, key=key_func, reverse=reverse)

    def _sync_action_states(self) -> None:
        scan_state = "disabled" if self.busy else "normal"
        actionable_state = "normal" if self.current_records and not self.busy else "disabled"
        undo_state = "normal" if self.last_applied_actions and not self.busy else "disabled"
        monitor_state = "disabled" if self.busy else "normal"

        self.scan_button.configure(state=scan_state)
        self.sort_button.configure(state=actionable_state)
        self.crossref_button.configure(state=actionable_state)
        self.masterlist_button.configure(state=actionable_state)
        self.undo_button.configure(state=undo_state)
        self.monitor_button.configure(state=monitor_state, text="Stop Monitor" if self.monitor_enabled else "Start Monitor")

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        self._sync_action_states()

    def run_workflow_self_test(self) -> dict[str, object]:
        sources = self.current_sources or sorter.choose_sources(self.script_dir, [])
        if not sources:
            raise RuntimeError("No valid source path was provided for workflow self-test.")

        run_id = sorter.timestamp()
        rules = sorter.load_plain_english_rules(self._resolve_rules())
        records = sorter.scan_documents(
            source_roots=sources,
            max_pages=self._max_pages_value(),
            ocr_mode=self.ocr_var.get().strip().lower(),
            recursive=self.recursive_var.get(),
            limit=3,
            identities=self.identities,
            script_dir=self.script_dir,
            rules=rules,
        )
        sorter.mark_duplicates(records, similar_dedupe=self.similar_dedupe_var.get())
        sorter.plan_destinations(
            records,
            output_root=self.output_root,
            quarantine_root=self.quarantine_root,
            destination_schema=self._destination_schema_key(),
        )
        sorter.apply_plan(records, mode="scan")
        csv_path, json_path, summary_path = sorter.write_reports(records, report_root=self.report_root, run_id=run_id)
        self._finish_scan(
            {
                "records": records,
                "run_id": run_id,
                "csv_path": csv_path,
                "json_path": json_path,
                "summary_path": summary_path,
            }
        )

        crossref_paths = sorter.write_cross_reference_report(
            self.current_records,
            report_root=self.report_root,
            run_id=run_id,
            bibliography_path=self.bibliography_path if self.bibliography_path.exists() else None,
        )
        self._finish_cross_reference(
            {
                "run_id": run_id,
                "csv_path": crossref_paths[0],
                "json_path": crossref_paths[1],
                "summary_path": crossref_paths[2],
            }
        )

        masterlist_paths = sorter.render_masterlist(self.current_records, report_root=self.report_root, run_id=run_id)
        self._finish_masterlist(
            {
                "run_id": run_id,
                "csv_path": masterlist_paths[0],
                "markdown_path": masterlist_paths[1],
                "text_path": masterlist_paths[2],
            }
        )

        self.sort_by_var.set("Title")
        self.sort_desc_var.set(False)
        sorted_preview = self._sort_records(self.current_records)
        search_hits = 0
        if sorted_preview:
            query = next((token for token in sorted_preview[0].title.split() if len(token) >= 4), sorted_preview[0].title)
            self.search_var.set(query)
            search_hits = len(self._current_display_records())
            self.search_var.set("")
        return {
            "records": len(self.current_records),
            "reports": sorted(self.latest_report_paths.keys()),
            "first_title": sorted_preview[0].title if sorted_preview else "",
            "rules_loaded": len(rules),
            "search_hits": search_hits,
            "lotus_files": len(self.lotus_notes),
            "sort_state": str(self.sort_button["state"]),
            "crossref_state": str(self.crossref_button["state"]),
            "masterlist_state": str(self.masterlist_button["state"]),
            "undo_state": str(self.undo_button["state"]),
            "monitor_label": str(self.monitor_button["text"]),
        }


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    args = build_parser().parse_args(argv)
    initial_paths = [Path(argument).expanduser().resolve() for argument in args.paths if Path(argument).expanduser().exists()]
    app = DrSortAcademicHelperApp(initial_paths=initial_paths)
    if args.self_test:
        app.update_idletasks()
        print(
            "SELFTEST OK "
            f"scan_button={app.scan_button['text']} "
            f"sort_button={app.sort_button['text']} "
            f"crossref_button={app.crossref_button['text']} "
            f"masterlist_button={app.masterlist_button['text']} "
            f"sort_options={len(SORT_BY_OPTIONS)} "
            f"tree_columns={len(app.tree['columns'])} "
            f"tabs={len(app.notebook.tabs())} "
            f"lotus_root={app.lotus_root.name}"
        )
        app.destroy()
        return 0
    if args.workflow_self_test:
        app.update_idletasks()
        result = app.run_workflow_self_test()
        print(
            "WORKFLOW OK "
            f"records={result['records']} "
            f"sort_state={result['sort_state']} "
            f"crossref_state={result['crossref_state']} "
            f"masterlist_state={result['masterlist_state']} "
            f"undo_state={result['undo_state']} "
            f"search_hits={result['search_hits']} "
            f"rules_loaded={result['rules_loaded']} "
            f"lotus_files={result['lotus_files']} "
            f"monitor_label={result['monitor_label']} "
            f"reports={','.join(result['reports'])} "
            f"first_title={result['first_title']}"
        )
        app.destroy()
        return 0
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
