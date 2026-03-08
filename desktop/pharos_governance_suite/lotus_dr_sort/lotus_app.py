from __future__ import annotations

import argparse
import datetime as dt
import queue
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import lotus_core as lotus


INDIGO = "#120E18"
SAND = "#120E18"
TERRACOTTA = "#B76046"
OCHRE = "#C98A2E"
CLAY = "#BAA891"
CLAY_MIST = "#1A1530"
TEAL = "#8E80BE"
TEAL_MIST = "#171123"
INK = "#F1E7D8"
SUBTLE = "#907B65"
SURFACE = "#221C31"
BORDER = "#3A2F4A"

INTAKE_TAB_ORDER = [
    ("profile", "Profile"),
    ("agency", "Agency"),
    ("strategic", "Strategy"),
    ("governance", "Governance"),
    ("operational", "Operations"),
    ("creative", "Creative"),
    ("meaning", "Meaning"),
]

SECTION_HELP = {
    "agency": "Describe who can act, what choices exist, what leverage is available, and where decision-making power sits.",
    "strategic": "Capture the mission, roadmap, institutional direction, priorities, and long-range program logic.",
    "governance": "Record policy, oversight, procurement, risk, standards, compliance, or public-interest considerations.",
    "operational": "Explain delivery, workflow, implementation steps, teams, capacity, and how execution will actually happen.",
    "creative": "Write the aesthetic, story, narrative, design, music, film, or image language that shapes the work.",
    "meaning": "Surface memory, identity, symbolic meaning, ethics, development, youth influence, or brain-plasticity implications.",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LOTUS score app")
    parser.add_argument("--self-test", action="store_true")
    return parser


class LotusApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("LOTUS")
        self.geometry("1380x920")
        self.minsize(1120, 760)
        self.configure(background=SAND)

        self.script_dir = Path(__file__).resolve().parent
        self.lotus_root = (self.script_dir / "LOTUS_UPLOADS").resolve()
        self.dr_sort_launcher = (self.script_dir / "Dr. Sort-Academic Helper.bat").resolve()
        self.status_var = tk.StringVar(value="LOTUS is ready for scoring intake and curated note review.")
        self.summary_var = tk.StringVar(value="Use the library ledger to review prior notes or move into the scoring studio to draft a polished new LOTUS entry.")
        self.draft_score_var = tk.StringVar(value="Projected scores will appear here once you preview a draft.")
        self.draft_signal_var = tk.StringVar(value="Fill the tabs and click Preview Draft & Score to see what the model is detecting.")
        self.draft_path_var = tk.StringVar(value="Structured drafts save into LOTUS_UPLOADS/manual_entries.")
        self.notes: list[lotus.LotusNote] = []
        self.note_by_item: dict[str, lotus.LotusNote] = {}
        self.form_vars = {
            "title": tk.StringVar(value=""),
            "author": tk.StringVar(value=""),
            "date": tk.StringVar(value=dt.date.today().isoformat()),
            "tags": tk.StringVar(value="agency, lotus"),
            "context": tk.StringVar(value=""),
            "source": tk.StringVar(value=""),
        }
        self.form_text_widgets: dict[str, tk.Text] = {}
        self.worker_queue: queue.Queue[tuple[str, object]] = queue.Queue()

        self._configure_style()
        self._build_ui()
        self.after(200, self._poll_queue)
        self.refresh_notes()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=SAND, foreground=INK, font=("Segoe UI", 10))
        style.configure("Shell.TFrame", background=SAND)
        style.configure("TFrame", background=SAND)
        style.configure("Hero.TFrame", background=INDIGO, relief="solid", borderwidth=1)
        style.configure("HeroStat.TFrame", background=CLAY_MIST, relief="solid", borderwidth=1)
        style.configure("Card.TFrame", background=SURFACE, relief="solid", borderwidth=1)
        style.configure("Toolbar.TFrame", background=CLAY_MIST, relief="solid", borderwidth=1)
        style.configure("AccentCard.TFrame", background=TEAL_MIST, relief="solid", borderwidth=1)
        style.configure("TNotebook", background=SAND, borderwidth=0, tabmargins=(0, 8, 0, 0))
        style.configure("TNotebook.Tab", padding=(15, 9), font=("Consolas", 9, "bold"), background=CLAY_MIST, foreground=CLAY)
        style.map("TNotebook.Tab", background=[("selected", SURFACE), ("active", "#2A223B")], foreground=[("selected", OCHRE), ("active", INK)])
        style.configure("Header.TLabel", background=INDIGO, foreground=INK, font=("Georgia", 24, "bold"))
        style.configure("HeroSub.TLabel", background=INDIGO, foreground=CLAY, font=("Segoe UI", 10))
        style.configure("HeroStatLabel.TLabel", background=CLAY_MIST, foreground=OCHRE, font=("Consolas", 8, "bold"))
        style.configure("HeroStatValue.TLabel", background=CLAY_MIST, foreground=INK, font=("Segoe UI", 9, "bold"))
        style.configure("Section.TLabel", background=SURFACE, foreground=INK, font=("Consolas", 9, "bold"))
        style.configure("AccentSection.TLabel", background=TEAL_MIST, foreground=INK, font=("Consolas", 9, "bold"))
        style.configure("Field.TLabel", background=SURFACE, foreground=CLAY, font=("Segoe UI", 9, "bold"))
        style.configure("Hint.TLabel", background=SURFACE, foreground=SUBTLE, font=("Segoe UI", 9))
        style.configure("AccentHint.TLabel", background=TEAL_MIST, foreground=SUBTLE, font=("Segoe UI", 9))
        style.configure("Meta.TLabel", background=SURFACE, foreground=OCHRE, font=("Consolas", 8, "bold"))
        style.configure("Summary.TLabel", background=TEAL_MIST, foreground=INK, font=("Segoe UI", 10))
        style.configure("Status.TLabel", background=TEAL_MIST, foreground=TEAL, font=("Segoe UI", 10, "bold"))
        style.configure("Metric.TLabel", background=TEAL_MIST, foreground=INK, font=("Georgia", 15, "bold"))
        style.configure("MetricSub.TLabel", background=TEAL_MIST, foreground=CLAY, font=("Segoe UI", 9))
        style.configure("Gold.TLabel", background=INDIGO, foreground=OCHRE, font=("Consolas", 8, "bold"))
        style.configure("Ledger.TLabel", background=SURFACE, foreground=OCHRE, font=("Consolas", 8, "bold"))
        style.configure(
            "Primary.TButton",
            background=TERRACOTTA,
            foreground=INK,
            bordercolor=TERRACOTTA,
            lightcolor=TERRACOTTA,
            darkcolor=TERRACOTTA,
            padding=(13, 9),
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Primary.TButton", background=[("active", "#BF664E"), ("disabled", "#6D4B43")], foreground=[("disabled", "#C6A690")])
        style.configure(
            "Gold.TButton",
            background=OCHRE,
            foreground="#170F0A",
            bordercolor=OCHRE,
            lightcolor=OCHRE,
            darkcolor=OCHRE,
            padding=(13, 9),
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Gold.TButton", background=[("active", "#DDB061"), ("disabled", "#67583D")], foreground=[("disabled", "#C6A690")])
        style.configure(
            "Utility.TButton",
            background=CLAY_MIST,
            foreground=INK,
            bordercolor=BORDER,
            lightcolor=CLAY_MIST,
            darkcolor=CLAY_MIST,
            padding=(11, 8),
        )
        style.map("Utility.TButton", background=[("active", "#2A223B")], foreground=[("active", OCHRE)])
        style.configure(
            "TEntry",
            fieldbackground=CLAY_MIST,
            foreground=INK,
            bordercolor=BORDER,
            lightcolor=TEAL,
            darkcolor=BORDER,
            padding=8,
        )
        style.configure("Treeview", background=CLAY_MIST, fieldbackground=CLAY_MIST, foreground=INK, rowheight=30, bordercolor=BORDER)
        style.configure("Treeview.Heading", background=INDIGO, foreground=OCHRE, font=("Consolas", 8, "bold"))
        style.map("Treeview", background=[("selected", "#2A223B")], foreground=[("selected", INK)])

    def _build_ui(self) -> None:
        root = ttk.Frame(self, style="Shell.TFrame", padding=20)
        root.pack(fill="both", expand=True)

        hero = ttk.Frame(root, style="Hero.TFrame", padding=(22, 20))
        hero.pack(fill="x", pady=(0, 14))
        ttk.Label(hero, text="REFINED SCORING WORKSPACE", style="Gold.TLabel").pack(anchor="w")
        ttk.Label(hero, text="LOTUS", style="Header.TLabel").pack(anchor="w", pady=(6, 0))
        ttk.Label(
            hero,
            text="Editorial scoring house for agency, governance, creative meaning, and structured notecraft.",
            style="HeroSub.TLabel",
        ).pack(anchor="w", pady=(4, 0))
        ttk.Label(
            hero,
            text="Obsidian governance shell  •  amber metal accents  •  plum editorial panels  •  violet signal glow",
            style="Gold.TLabel",
        ).pack(anchor="w", pady=(10, 0))
        hero_band = ttk.Frame(hero, style="Hero.TFrame")
        hero_band.pack(fill="x", pady=(16, 0))
        hero_specs = (
            ("Lens", "Agency, strategy, governance, creative, and meaning signals."),
            ("Intake", "Guided tabs for metadata, structured interpretation, and scoring evidence."),
            ("Output", "A clean ledger of notes plus polished draft previews ready to save."),
        )
        for index, (label, value) in enumerate(hero_specs):
            card = ttk.Frame(hero_band, style="HeroStat.TFrame", padding=(14, 12))
            card.grid(row=0, column=index, sticky="nsew", padx=(0, 10) if index < len(hero_specs) - 1 else 0)
            ttk.Label(card, text=label.upper(), style="HeroStatLabel.TLabel").pack(anchor="w")
            ttk.Label(card, text=value, style="HeroStatValue.TLabel", wraplength=320, justify="left").pack(anchor="w", pady=(6, 0))
            hero_band.columnconfigure(index, weight=1)

        toolbar = ttk.Frame(root, style="Toolbar.TFrame", padding=(18, 14))
        toolbar.pack(fill="x", pady=(0, 12))
        ttk.Button(toolbar, text="Upload Notes", style="Gold.TButton", command=self.upload_notes).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(toolbar, text="Refresh Feed", style="Utility.TButton", command=self.refresh_notes).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(toolbar, text="Open LOTUS Folder", style="Utility.TButton", command=self.open_lotus_folder).grid(row=0, column=2, padx=(0, 8))
        ttk.Button(toolbar, text="New Score Draft", style="Utility.TButton", command=self.new_score_draft).grid(row=0, column=3, padx=(0, 8))
        ttk.Button(toolbar, text="Open Dr. Sort", style="Primary.TButton", command=self.open_dr_sort).grid(row=0, column=4)
        toolbar.columnconfigure(5, weight=1)

        summary = ttk.Frame(root, style="AccentCard.TFrame", padding=(18, 16))
        summary.pack(fill="x", pady=(0, 12))
        ttk.Label(summary, textvariable=self.summary_var, style="Summary.TLabel", wraplength=1320, justify="left").pack(anchor="w")
        ttk.Label(summary, textvariable=self.status_var, style="Status.TLabel").pack(anchor="w", pady=(4, 0))

        self.main_notebook = ttk.Notebook(root)
        self.main_notebook.pack(fill="both", expand=True)

        self.library_tab = ttk.Frame(self.main_notebook, style="Card.TFrame", padding=(12, 12))
        self.intake_tab = ttk.Frame(self.main_notebook, style="Card.TFrame", padding=(12, 12))
        self.main_notebook.add(self.library_tab, text="Library Ledger")
        self.main_notebook.add(self.intake_tab, text="Scoring Studio")

        self._build_library_tab(self.library_tab)
        self._build_intake_tab(self.intake_tab)

    def _build_library_tab(self, parent: ttk.Frame) -> None:
        body = ttk.Frame(parent)
        body.pack(fill="both", expand=True)

        table_frame = ttk.Frame(body, style="Card.TFrame", padding=(12, 12, 12, 8))
        table_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))
        ttk.Label(table_frame, text="CURATED NOTE LEDGER", style="Ledger.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        columns = ("title", "agency_score", "creative_score", "strategic_score", "modified", "signals", "file")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.tree.heading("title", text="LOTUS note")
        self.tree.heading("agency_score", text="Agency")
        self.tree.heading("creative_score", text="Creative")
        self.tree.heading("strategic_score", text="Strategic")
        self.tree.heading("modified", text="Modified")
        self.tree.heading("signals", text="Signals")
        self.tree.heading("file", text="File")
        self.tree.column("title", width=280, stretch=True)
        self.tree.column("agency_score", width=78, stretch=False, anchor="center")
        self.tree.column("creative_score", width=78, stretch=False, anchor="center")
        self.tree.column("strategic_score", width=78, stretch=False, anchor="center")
        self.tree.column("modified", width=130, stretch=False)
        self.tree.column("signals", width=180, stretch=False)
        self.tree.column("file", width=220, stretch=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_note_selected)
        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=y_scroll.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        y_scroll.grid(row=1, column=1, sticky="ns")
        table_frame.rowconfigure(1, weight=1)
        table_frame.columnconfigure(0, weight=1)

        preview_frame = ttk.Frame(body, style="Card.TFrame", padding=(14, 14))
        preview_frame.pack(side="right", fill="both", expand=True)
        ttk.Label(preview_frame, text="Reading Preview", style="Section.TLabel").pack(anchor="w")
        self.preview_text = self._build_text_widget(preview_frame, height=30)
        self.preview_text.pack(fill="both", expand=True, pady=(8, 0))
        self.preview_text.configure(state="disabled")

    def _build_intake_tab(self, parent: ttk.Frame) -> None:
        toolbar = ttk.Frame(parent, style="Toolbar.TFrame", padding=(16, 14))
        toolbar.pack(fill="x", pady=(0, 10))
        ttk.Button(toolbar, text="Preview Draft & Score", style="Gold.TButton", command=self.preview_draft).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(toolbar, text="Save to LOTUS", style="Primary.TButton", command=self.save_draft_to_lotus).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(toolbar, text="Clear Form", style="Utility.TButton", command=self.clear_draft_form).grid(row=0, column=2)
        toolbar.columnconfigure(3, weight=1)

        body = ttk.Frame(parent)
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right = ttk.Frame(body, style="Card.TFrame", padding=(16, 16))
        right.pack(side="right", fill="both", expand=True)

        self.intake_notebook = ttk.Notebook(left)
        self.intake_notebook.pack(fill="both", expand=True)

        for key, label in INTAKE_TAB_ORDER:
            tab = ttk.Frame(self.intake_notebook, style="Card.TFrame")
            self.intake_notebook.add(tab, text=label)
            if key == "profile":
                self._build_profile_tab(tab)
            else:
                self._build_section_tab(tab, key, label)

        score_card = ttk.Frame(right, style="AccentCard.TFrame", padding=(14, 14))
        score_card.pack(fill="x")
        ttk.Label(score_card, text="Projected Scoring", style="AccentSection.TLabel").pack(anchor="w")
        ttk.Label(score_card, textvariable=self.draft_score_var, style="Metric.TLabel", wraplength=400, justify="left").pack(anchor="w", pady=(6, 2))
        ttk.Label(score_card, textvariable=self.draft_signal_var, style="MetricSub.TLabel", wraplength=400, justify="left").pack(anchor="w")
        ttk.Label(score_card, textvariable=self.draft_path_var, style="AccentHint.TLabel", wraplength=400, justify="left").pack(anchor="w", pady=(8, 0))

        preview_frame = ttk.Frame(right, style="Card.TFrame", padding=(0, 12, 0, 0))
        preview_frame.pack(fill="both", expand=True)
        ttk.Label(preview_frame, text="Structured Draft Preview", style="Section.TLabel").pack(anchor="w")
        preview_inner = ttk.Frame(preview_frame)
        preview_inner.pack(fill="both", expand=True, pady=(8, 0))
        self.draft_preview_text = self._build_text_widget(preview_inner, height=30)
        draft_scroll = ttk.Scrollbar(preview_inner, orient="vertical", command=self.draft_preview_text.yview)
        self.draft_preview_text.configure(yscrollcommand=draft_scroll.set)
        self.draft_preview_text.grid(row=0, column=0, sticky="nsew")
        draft_scroll.grid(row=0, column=1, sticky="ns")
        preview_inner.rowconfigure(0, weight=1)
        preview_inner.columnconfigure(0, weight=1)
        self._set_draft_preview_text("Draft preview will appear here after you build a scoring note.")

    def _build_profile_tab(self, parent: ttk.Frame) -> None:
        frame = ttk.Frame(parent, style="Card.TFrame", padding=(18, 18))
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Profile", style="Section.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(
            frame,
            text="Use this tab to name the note, set metadata, and summarize the core situation before you complete the scoring sections.",
            style="Hint.TLabel",
            wraplength=760,
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 14))

        fields = [
            ("Title", "title"),
            ("Author / Owner", "author"),
            ("Date", "date"),
            ("Tags", "tags"),
            ("Context / Theme", "context"),
            ("Source / Origin", "source"),
        ]
        for index, (label, key) in enumerate(fields):
            row = 2 + (index // 2) * 2
            column = (index % 2) * 2
            ttk.Label(frame, text=label, style="Field.TLabel").grid(row=row, column=column, sticky="w", pady=(0, 4), padx=(0, 10))
            entry = ttk.Entry(frame, textvariable=self.form_vars[key])
            entry.grid(row=row + 1, column=column, sticky="ew", padx=(0, 18), pady=(0, 10))

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(2, weight=1)

        summary_row = 8
        ttk.Label(frame, text="Summary", style="Field.TLabel").grid(row=summary_row, column=0, columnspan=2, sticky="w", pady=(4, 4))
        ttk.Label(
            frame,
            text="Write the shortest useful framing paragraph. The scoring model uses this together with all the section tabs.",
            style="Hint.TLabel",
            wraplength=760,
            justify="left",
        ).grid(row=summary_row + 1, column=0, columnspan=2, sticky="w", pady=(0, 8))
        summary_text = self._build_text_widget(frame, height=10)
        summary_text.grid(row=summary_row + 2, column=0, columnspan=4, sticky="nsew")
        frame.rowconfigure(summary_row + 2, weight=1)
        self.form_text_widgets["summary"] = summary_text

    def _build_section_tab(self, parent: ttk.Frame, section_key: str, label: str) -> None:
        frame = ttk.Frame(parent, style="Card.TFrame", padding=(18, 18))
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text=label, style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            frame,
            text=SECTION_HELP[section_key],
            style="Hint.TLabel",
            wraplength=780,
            justify="left",
        ).pack(anchor="w", pady=(6, 8))
        signal_terms = ", ".join(lotus.AGENCY_SIGNAL_GROUPS[section_key]["terms"][:8])
        ttk.Label(frame, text=f"Signals scored here: {signal_terms}", style="Meta.TLabel", wraplength=780, justify="left").pack(anchor="w", pady=(0, 8))
        text_widget = self._build_text_widget(frame, height=22)
        text_widget.pack(fill="both", expand=True)
        self.form_text_widgets[section_key] = text_widget

    def _build_text_widget(self, parent: tk.Widget, height: int) -> tk.Text:
        return tk.Text(
            parent,
            height=height,
            wrap="word",
            bg=CLAY_MIST,
            fg=INK,
            insertbackground=OCHRE,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=TEAL,
            padx=10,
            pady=8,
        )

    def refresh_notes(self) -> None:
        self.notes = lotus.load_lotus_notes(self.lotus_root)
        self.note_by_item = {}
        for item in self.tree.get_children():
            self.tree.delete(item)
        for note in self.notes:
            item_id = self.tree.insert(
                "",
                "end",
                values=(
                    note.title,
                    note.agency_score,
                    note.creative_score,
                    note.strategic_score,
                    note.modified_iso,
                    ", ".join(note.signals[:4]),
                    str(note.path.relative_to(self.lotus_root)),
                ),
            )
            self.note_by_item[item_id] = note
        feed_count = sum(1 for note in self.notes if "dr_sort_feed" in note.path.parts)
        manual_count = sum(1 for note in self.notes if "manual_entries" in note.path.parts)
        self.summary_var.set(
            f"LOTUS has {len(self.notes)} note(s), including {feed_count} Dr. Sort feed item(s) and {manual_count} structured intake draft(s)."
        )
        self.status_var.set("LOTUS refreshed.")
        items = self.tree.get_children()
        if items:
            self.tree.selection_set(items[0])
            self.tree.focus(items[0])
            self._show_note(self.note_by_item[items[0]])
        else:
            self._set_preview_text("No LOTUS notes yet.")

    def upload_notes(self) -> None:
        chosen = filedialog.askopenfilenames(
            title="Upload notes to LOTUS",
            filetypes=[("LOTUS notes", "*.md *.txt"), ("Markdown", "*.md"), ("Text", "*.txt")],
        )
        if not chosen:
            return
        imported = lotus.import_notes([Path(path).resolve() for path in chosen], self.lotus_root)
        self.refresh_notes()
        self.status_var.set(f"Imported {len(imported)} note(s) into LOTUS.")

    def open_lotus_folder(self) -> None:
        lotus.ensure_lotus_root(self.lotus_root)
        try:
            subprocess.Popen(["explorer.exe", str(self.lotus_root)])
        except Exception as exc:
            messagebox.showerror("LOTUS", str(exc))

    def open_dr_sort(self) -> None:
        if not self.dr_sort_launcher.exists():
            messagebox.showerror("LOTUS", "Dr. Sort launcher was not found.")
            return
        try:
            subprocess.Popen([str(self.dr_sort_launcher)], cwd=str(self.script_dir))
        except Exception as exc:
            messagebox.showerror("LOTUS", str(exc))

    def new_score_draft(self) -> None:
        self.clear_draft_form()
        self.main_notebook.select(self.intake_tab)
        self.intake_notebook.select(0)
        self.status_var.set("Ready for a new structured LOTUS draft.")

    def preview_draft(self) -> None:
        title, markdown, scores = self._generate_draft_payload()
        self._apply_draft_scores(title, markdown, scores)
        self.status_var.set("Projected LOTUS scores updated from the scoring intake tabs.")

    def save_draft_to_lotus(self) -> None:
        title, markdown, scores = self._generate_draft_payload()
        destination = lotus.save_structured_note(markdown, title, self.lotus_root)
        self._apply_draft_scores(title, markdown, scores)
        self.refresh_notes()
        self._select_note_by_path(destination)
        self.draft_path_var.set(f"Saved to {destination.relative_to(self.lotus_root)}")
        self.status_var.set(f"Saved structured LOTUS note: {destination.name}")
        self.main_notebook.select(self.library_tab)

    def clear_draft_form(self) -> None:
        defaults = {
            "title": "",
            "author": "",
            "date": dt.date.today().isoformat(),
            "tags": "agency, lotus",
            "context": "",
            "source": "",
        }
        for key, value in defaults.items():
            self.form_vars[key].set(value)
        for widget in self.form_text_widgets.values():
            widget.delete("1.0", "end")
        self.draft_score_var.set("Projected scores will appear here once you preview a draft.")
        self.draft_signal_var.set("Fill the tabs and click Preview Draft & Score to see what the model is detecting.")
        self.draft_path_var.set("Structured drafts save into LOTUS_UPLOADS/manual_entries.")
        self._set_draft_preview_text("Draft preview will appear here after you build a scoring note.")

    def _generate_draft_payload(self) -> tuple[str, str, dict[str, object]]:
        title = self.form_vars["title"].get().strip() or "LOTUS note"
        author = self.form_vars["author"].get().strip()
        note_date = self.form_vars["date"].get().strip() or dt.date.today().isoformat()
        raw_tags = self.form_vars["tags"].get().replace(";", ",")
        tags = [tag.strip() for tag in raw_tags.split(",") if tag.strip()]
        summary = self._text_value("summary")
        sections = {section_name: self._text_value(section_name) for section_name in lotus.LOTUS_SCORE_SECTION_ORDER}
        markdown = lotus.build_structured_note_markdown(
            title=title,
            author=author,
            note_date=note_date,
            tags=tags,
            context=self.form_vars["context"].get().strip(),
            source=self.form_vars["source"].get().strip(),
            summary=summary,
            sections=sections,
        )
        scores = lotus.score_lotus_text(title, markdown)
        return title, markdown, scores

    def _apply_draft_scores(self, title: str, markdown: str, scores: dict[str, object]) -> None:
        matched_terms = scores.get("matched_terms", {})
        score_line = (
            f"{title} | Agency {scores['agency_score']} | Creative {scores['creative_score']} | "
            f"Strategic {scores['strategic_score']} | Governance {scores['governance_score']} | "
            f"Operational {scores['operational_score']} | Meaning {scores['meaning_score']}"
        )
        match_parts: list[str] = []
        if isinstance(matched_terms, dict):
            for section_name in lotus.LOTUS_SCORE_SECTION_ORDER:
                section_matches = matched_terms.get(section_name, [])
                if section_matches:
                    match_parts.append(f"{section_name.title()}: {', '.join(section_matches[:4])}")
        self.draft_score_var.set(score_line)
        self.draft_signal_var.set(
            "Matched signals: " + (" | ".join(match_parts) if match_parts else "none yet. Add more concrete, content-rich detail in the tabs.")
        )
        self._set_draft_preview_text(markdown)

    def _text_value(self, key: str) -> str:
        widget = self.form_text_widgets.get(key)
        if widget is None:
            return ""
        return widget.get("1.0", "end").strip()

    def _select_note_by_path(self, path: Path) -> None:
        for item_id, note in self.note_by_item.items():
            if note.path == path:
                self.tree.selection_set(item_id)
                self.tree.focus(item_id)
                self.tree.see(item_id)
                self._show_note(note)
                return

    def _on_note_selected(self, _event: object) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        note = self.note_by_item.get(selection[0])
        if note is not None:
            self._show_note(note)

    def _show_note(self, note: lotus.LotusNote) -> None:
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
        self._set_preview_text("\n".join(preview))

    def _set_preview_text(self, value: str) -> None:
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", value)
        self.preview_text.configure(state="disabled")

    def _set_draft_preview_text(self, value: str) -> None:
        self.draft_preview_text.configure(state="normal")
        self.draft_preview_text.delete("1.0", "end")
        self.draft_preview_text.insert("1.0", value)
        self.draft_preview_text.configure(state="disabled")

    def _poll_queue(self) -> None:
        try:
            while True:
                _event, _payload = self.worker_queue.get_nowait()
        except queue.Empty:
            pass
        self.after(200, self._poll_queue)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    args = build_parser().parse_args(argv)
    app = LotusApp()
    if args.self_test:
        app.update_idletasks()
        print(
            "SELFTEST OK "
            f"title={app.title()} "
            f"columns={len(app.tree['columns'])} "
            f"tabs={len(app.main_notebook.tabs())} "
            f"input_tabs={len(app.intake_notebook.tabs())} "
            f"lotus_root={app.lotus_root.name}"
        )
        app.destroy()
        return 0
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
