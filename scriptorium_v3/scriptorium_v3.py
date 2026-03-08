from __future__ import annotations

import argparse
import queue
import sys
import threading
import traceback
from collections import Counter
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import document_sorter as sorter


VIOLET_GEM = "#5B2A86"
VIOLET_MIST = "#F4EEFA"
SCARLET_ROSE = "#B63A64"
MUTED_GOLD = "#B9923B"
TEAL = "#1F7A8C"
TEAL_MIST = "#E7F7F7"
INK = "#23162D"
SUBTLE_INK = "#665671"
SURFACE = "#FFFDF8"
SURFACE_ALT = "#F7F1FB"
TREE_BORDER = "#D8C7E6"
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
    parser = argparse.ArgumentParser(description="Scriptorium.v3 desktop app")
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


class ScriptoriumApp(tk.Tk):
    def __init__(self, initial_paths: list[Path] | None = None) -> None:
        super().__init__()
        self.title("Scriptorium.v3")
        self.geometry("1540x920")
        self.minsize(1180, 720)
        self.configure(background=VIOLET_MIST)

        self.script_dir = Path(__file__).resolve().parent
        self.output_root = (self.script_dir / sorter.DEFAULT_OUTPUT_DIR).resolve()
        self.quarantine_root = (self.script_dir / sorter.DEFAULT_QUARANTINE_DIR).resolve()
        self.report_root = (self.script_dir / sorter.DEFAULT_REPORT_DIR).resolve()
        self.identities = list(sorter.DEFAULT_IDENTITIES)
        self.bibliography_path = (self.script_dir / "MASTER BIBLIOGRAPHY.txt").resolve()

        default_sources = initial_paths or sorter.choose_sources(self.script_dir, [])
        self.source_var = tk.StringVar(value=paths_to_text(default_sources))
        self.mode_var = tk.StringVar(value="copy")
        self.ocr_var = tk.StringVar(value="auto")
        self.sort_by_var = tk.StringVar(value="Proposed")
        self.sort_desc_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready.")
        self.summary_var = tk.StringVar(
            value="Choose a folder or files, click Scan, review the proposed destinations, then click Sort."
        )

        self.current_sources: list[Path] = default_sources
        self.current_records: list[sorter.DocumentRecord] = []
        self.latest_report_paths: dict[str, Path] = {}
        self.latest_run_id = ""
        self.busy = False
        self.worker_queue: queue.Queue[tuple[str, object]] = queue.Queue()

        self._configure_style()
        self._build_ui()
        self.sort_by_var.trace_add("write", self._on_sort_settings_changed)
        self.sort_desc_var.trace_add("write", self._on_sort_settings_changed)
        self.after(200, self._poll_worker_queue)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=VIOLET_MIST, foreground=INK, font=("Segoe UI", 10))
        style.configure("TFrame", background=VIOLET_MIST)
        style.configure("Card.TFrame", background=SURFACE, relief="flat")
        style.configure("TealCard.TFrame", background=TEAL_MIST, relief="flat")
        style.configure("Hero.TFrame", background=VIOLET_GEM)
        style.configure("Toolbar.TFrame", background=SURFACE_ALT)
        style.configure("Header.TLabel", background=VIOLET_GEM, foreground="white", font=("Georgia", 21, "bold"))
        style.configure("HeroSub.TLabel", background=VIOLET_GEM, foreground="#F5EFFF", font=("Segoe UI", 10))
        style.configure("Section.TLabel", background=SURFACE_ALT, foreground=TEAL, font=("Segoe UI", 10, "bold"))
        style.configure("Summary.TLabel", background=TEAL_MIST, foreground=INK)
        style.configure("Status.TLabel", background=TEAL_MIST, foreground=TEAL, font=("Segoe UI", 10, "bold"))
        style.configure("Muted.TLabel", background=VIOLET_MIST, foreground=SUBTLE_INK)
        style.configure("WarmMuted.TLabel", background=SURFACE_ALT, foreground=SUBTLE_INK)
        style.configure("Gold.TLabel", background=VIOLET_GEM, foreground=MUTED_GOLD, font=("Segoe UI", 9, "bold"))
        style.configure(
            "Scan.TButton",
            background=TEAL,
            foreground="white",
            bordercolor=TEAL,
            lightcolor=TEAL,
            darkcolor=TEAL,
            padding=(14, 9),
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Scan.TButton", background=[("active", "#2C8EA0"), ("disabled", "#9EC9D0")])
        style.configure(
            "Sort.TButton",
            background=SCARLET_ROSE,
            foreground="white",
            bordercolor=SCARLET_ROSE,
            lightcolor=SCARLET_ROSE,
            darkcolor=SCARLET_ROSE,
            padding=(14, 9),
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Sort.TButton", background=[("active", "#C64D75"), ("disabled", "#D8A8B6")])
        style.configure(
            "GoldAction.TButton",
            background=MUTED_GOLD,
            foreground="white",
            bordercolor=MUTED_GOLD,
            lightcolor=MUTED_GOLD,
            darkcolor=MUTED_GOLD,
            padding=(12, 9),
            font=("Segoe UI", 10, "bold"),
        )
        style.map("GoldAction.TButton", background=[("active", "#CAA24B"), ("disabled", "#D8C091")])
        style.configure(
            "Utility.TButton",
            background="white",
            foreground=TEAL,
            bordercolor=TEAL,
            lightcolor="white",
            darkcolor="white",
            padding=(10, 7),
        )
        style.map("Utility.TButton", background=[("active", TEAL_MIST)], foreground=[("active", TEAL)])
        style.configure(
            "TEntry",
            fieldbackground="white",
            foreground=INK,
            bordercolor=TEAL,
            lightcolor=MUTED_GOLD,
            darkcolor=TREE_BORDER,
            padding=7,
        )
        style.configure(
            "TCombobox",
            fieldbackground="white",
            background="white",
            foreground=INK,
            bordercolor=TEAL,
            arrowcolor=TEAL,
            padding=6,
        )
        style.map("TCombobox", fieldbackground=[("readonly", "white")], selectbackground=[("readonly", "white")])
        style.configure("TNotebook", background=VIOLET_MIST, borderwidth=0)
        style.configure("TNotebook.Tab", background=TEAL_MIST, foreground=TEAL, padding=(14, 8))
        style.map(
            "TNotebook.Tab",
            background=[("selected", TEAL), ("active", "#2C8EA0")],
            foreground=[("selected", "white"), ("active", "white")],
        )
        style.configure("Treeview", background="white", fieldbackground="white", foreground=INK, rowheight=26, bordercolor=TREE_BORDER)
        style.configure("Treeview.Heading", background=VIOLET_GEM, foreground="white", font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", TEAL_MIST)], foreground=[("selected", INK)])
        style.map("Treeview.Heading", background=[("active", "#7340A2")])
        style.configure("Teal.TCheckbutton", background=SURFACE_ALT, foreground=TEAL, font=("Segoe UI", 9, "bold"))

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root, style="Hero.TFrame", padding=(18, 16))
        header.pack(fill="x")
        ttk.Label(header, text="Scriptorium.v3", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Scan files, extract metadata, preview renaming and sorting, then apply the plan.",
            style="HeroSub.TLabel",
        ).pack(anchor="w", pady=(4, 0))
        ttk.Label(
            header,
            text="Violet gem core  •  scarlet rose action  •  muted gold highlights  •  teal scan flow",
            style="Gold.TLabel",
        ).pack(anchor="w", pady=(8, 0))

        controls = ttk.Frame(root, style="Toolbar.TFrame", padding=(16, 14, 16, 12))
        controls.pack(fill="x")

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

        summary_frame = ttk.Frame(root, style="TealCard.TFrame", padding=(16, 14))
        summary_frame.pack(fill="x", pady=(0, 12))
        ttk.Label(summary_frame, textvariable=self.summary_var, wraplength=1480, justify="left", style="Summary.TLabel").pack(anchor="w")
        ttk.Label(summary_frame, textvariable=self.status_var, style="Status.TLabel").pack(anchor="w", pady=(4, 0))

        table_frame = ttk.Frame(root, style="Card.TFrame", padding=(10, 10, 10, 6))
        table_frame.pack(fill="both", expand=True)

        columns = (
            "relative_source",
            "category",
            "doc_type",
            "language",
            "year",
            "authors",
            "title",
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
        self.tree.heading("duplicate_status", text="Duplicate")
        self.tree.heading("planned_destination", text="Proposed destination")

        self.tree.column("relative_source", width=230, stretch=False)
        self.tree.column("category", width=120, stretch=False)
        self.tree.column("doc_type", width=150, stretch=False)
        self.tree.column("language", width=58, stretch=False, anchor="center")
        self.tree.column("year", width=62, stretch=False, anchor="center")
        self.tree.column("authors", width=180, stretch=False)
        self.tree.column("title", width=360, stretch=True)
        self.tree.column("duplicate_status", width=128, stretch=False)
        self.tree.column("planned_destination", width=520, stretch=True)

        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree.tag_configure("UNCLEAR", background="#FBF6E8")
        self.tree.tag_configure("SCHOLAR", background="#EEF8F9")
        self.tree.tag_configure("PERSONAL_ADMIN", background="#FCEBF1")
        self.tree.tag_configure("PROFESSIONAL", background="#EEE7F8")
        self.tree.tag_configure("CREATIVE", background="#F6ECFB")
        self.tree.tag_configure("duplicate_exact", background="#F7D8E2")
        self.tree.tag_configure("duplicate_probable", background="#F3E2B8")

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=False, pady=(12, 0))

        summary_text_frame = ttk.Frame(notebook)
        log_frame = ttk.Frame(notebook)
        notebook.add(summary_text_frame, text="Report Summary")
        notebook.add(log_frame, text="Activity")

        self.report_text = tk.Text(
            summary_text_frame,
            height=10,
            wrap="word",
            bg=SURFACE,
            fg=INK,
            insertbackground=VIOLET_GEM,
            relief="flat",
            highlightthickness=1,
            highlightbackground=TREE_BORDER,
            highlightcolor=MUTED_GOLD,
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
            highlightcolor=TEAL,
        )
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")

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
                ("Supported documents", "*.pdf *.docx *.doc *.txt"),
                ("PDF files", "*.pdf"),
                ("Word documents", "*.docx *.doc"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )
        if not chosen:
            return
        self.current_sources = [Path(path).resolve() for path in chosen]
        self.source_var.set(paths_to_text(self.current_sources))

    def use_default_sources(self) -> None:
        self.current_sources = sorter.choose_sources(self.script_dir, [])
        self.source_var.set(paths_to_text(self.current_sources))

    def start_scan(self) -> None:
        if self.busy:
            return
        sources = self._resolve_sources()
        if not sources:
            messagebox.showerror("Scriptorium.v3", "Choose at least one existing file or folder to scan.")
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
            messagebox.showinfo("Scriptorium.v3", "Scan files first so there is a plan to apply.")
            return
        mode = self.mode_var.get().strip().lower()
        if mode == "move":
            confirmed = messagebox.askyesno(
                "Scriptorium.v3",
                "Move mode will remove files from the source location after sorting. Continue?",
            )
            if not confirmed:
                return
        self._set_busy(True)
        self.summary_var.set("Applying the proposed sorting plan...")
        self.status_var.set("Sorting in progress.")
        self._append_log(f"Applying plan in {mode} mode.")
        threading.Thread(target=self._sort_worker, args=(mode,), daemon=True).start()

    def start_cross_reference(self) -> None:
        if self.busy:
            return
        if not self.current_records:
            messagebox.showinfo("Scriptorium.v3", "Scan files first so there is a record set to cross-reference.")
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
            messagebox.showinfo("Scriptorium.v3", "Scan files first so there is a record set for the masterlist.")
            return
        self._set_busy(True)
        self.summary_var.set("Rendering the masterlist...")
        self.status_var.set("Masterlist rendering in progress.")
        self._append_log("Rendering masterlist.")
        threading.Thread(target=self._masterlist_worker, daemon=True).start()

    def _resolve_sources(self) -> list[Path]:
        parsed = parse_input_paths(self.source_var.get())
        if parsed:
            return parsed
        return sorter.choose_sources(self.script_dir, [])

    def _on_sort_settings_changed(self, *_args: object) -> None:
        if self.current_records:
            self._refresh_tree(self.current_records)

    def _scan_worker(self, sources: list[Path]) -> None:
        try:
            run_id = sorter.timestamp()
            records = sorter.scan_documents(
                source_roots=sources,
                max_pages=5,
                ocr_mode=self.ocr_var.get().strip().lower(),
                recursive=True,
                limit=None,
                identities=self.identities,
                script_dir=self.script_dir,
                progress_callback=lambda message: self.worker_queue.put(("progress", message)),
            )
            sorter.mark_duplicates(records, similar_dedupe=True)
            sorter.plan_destinations(records, output_root=self.output_root, quarantine_root=self.quarantine_root)
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
                elif event == "error":
                    self._set_busy(False)
                    self.status_var.set("A processing error occurred.")
                    self._append_log(str(payload))
                    messagebox.showerror("Scriptorium.v3", str(payload))
        except queue.Empty:
            pass
        self.after(200, self._poll_worker_queue)

    def _finish_scan(self, payload: dict[str, object]) -> None:
        records = payload["records"]
        if not isinstance(records, list):
            return
        self.latest_run_id = str(payload["run_id"])
        self.current_records = records
        self.latest_report_paths = {
            "csv": payload["csv_path"],
            "json": payload["json_path"],
            "summary": payload["summary_path"],
        }
        self._refresh_tree(records)
        summary = self._build_summary_text(
            records,
            run_id=str(payload["run_id"]),
            summary_path=Path(payload["summary_path"]),
            csv_path=Path(payload["csv_path"]),
            json_path=Path(payload["json_path"]),
            mode="scan",
        )
        self.summary_var.set(
            f"Scan complete. Review the proposed destinations below, then click Sort to apply the plan."
        )
        self.status_var.set(f"Scan complete. {len(records)} document(s) evaluated.")
        self._set_report_text(summary)
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
        self._refresh_tree(records)
        summary = self._build_summary_text(
            records,
            run_id=str(payload["run_id"]),
            summary_path=Path(payload["summary_path"]),
            csv_path=Path(payload["csv_path"]),
            json_path=Path(payload["json_path"]),
            mode=str(payload["mode"]),
        )
        self.summary_var.set(
            f"Sort complete. Files were processed in {payload['mode']} mode and the reports were updated."
        )
        self.status_var.set("Sorting complete.")
        self._set_report_text(summary)
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
            "",
            f"Documents scanned: {len(records)}",
            f"Kept: {duplicates.get('keep', 0)}",
            f"Exact duplicates: {duplicates.get('duplicate_exact', 0)}",
            f"Probable duplicates: {duplicates.get('duplicate_probable', 0)}",
            "",
            "By category:",
        ]
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

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.scan_button.configure(state=state)
        actionable_state = state if self.current_records else "disabled"
        self.sort_button.configure(state=actionable_state)
        self.crossref_button.configure(state=actionable_state)
        self.masterlist_button.configure(state=actionable_state)
        if not busy and self.current_records:
            self.sort_button.configure(state="normal")
            self.crossref_button.configure(state="normal")
            self.masterlist_button.configure(state="normal")

    def run_workflow_self_test(self) -> dict[str, object]:
        sources = self.current_sources or sorter.choose_sources(self.script_dir, [])
        if not sources:
            raise RuntimeError("No valid source path was provided for workflow self-test.")

        run_id = sorter.timestamp()
        records = sorter.scan_documents(
            source_roots=sources,
            max_pages=5,
            ocr_mode=self.ocr_var.get().strip().lower(),
            recursive=True,
            limit=3,
            identities=self.identities,
            script_dir=self.script_dir,
        )
        sorter.mark_duplicates(records, similar_dedupe=True)
        sorter.plan_destinations(records, output_root=self.output_root, quarantine_root=self.quarantine_root)
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
        return {
            "records": len(self.current_records),
            "reports": sorted(self.latest_report_paths.keys()),
            "first_title": sorted_preview[0].title if sorted_preview else "",
            "sort_state": str(self.sort_button["state"]),
            "crossref_state": str(self.crossref_button["state"]),
            "masterlist_state": str(self.masterlist_button["state"]),
        }


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    args = build_parser().parse_args(argv)
    initial_paths = [Path(argument).expanduser().resolve() for argument in args.paths if Path(argument).expanduser().exists()]
    app = ScriptoriumApp(initial_paths=initial_paths)
    if args.self_test:
        app.update_idletasks()
        print(
            "SELFTEST OK "
            f"scan_button={app.scan_button['text']} "
            f"sort_button={app.sort_button['text']} "
            f"crossref_button={app.crossref_button['text']} "
            f"masterlist_button={app.masterlist_button['text']} "
            f"sort_options={len(SORT_BY_OPTIONS)} "
            f"tree_columns={len(app.tree['columns'])}"
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
            f"reports={','.join(result['reports'])} "
            f"first_title={result['first_title']}"
        )
        app.destroy()
        return 0
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
