from __future__ import annotations

import argparse
import queue
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from . import lotus_core as lotus
except ImportError:
    import lotus_core as lotus


INDIGO = "#3F375B"
SAND = "#F7EFE3"
TERRACOTTA = "#B55E3F"
OCHRE = "#A66F22"
CLAY = "#6C4B35"
CLAY_MIST = "#F2E4D5"
INK = "#2A201C"
SURFACE = "#FFF9F2"
BORDER = "#D6B89C"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LOTUS social agency scoring app")
    parser.add_argument("--self-test", action="store_true")
    return parser


class LotusApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("LOTUS")
        self.geometry("1320x880")
        self.minsize(1060, 700)
        self.configure(background=SAND)

        self.script_dir = Path(__file__).resolve().parent
        self.lotus_root = (self.script_dir / "LOTUS_UPLOADS").resolve()
        self.status_var = tk.StringVar(value="LOTUS is ready.")
        self.summary_var = tk.StringVar(
            value=(
                "Upload notes to review Lotus scoring across agency, strategy, governance, "
                "operational, creative, and meaning signals."
            )
        )
        self.notes: list[lotus.LotusNote] = []
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
        style.configure("TFrame", background=SAND)
        style.configure("Hero.TFrame", background=INDIGO)
        style.configure("Card.TFrame", background=SURFACE)
        style.configure("Toolbar.TFrame", background=CLAY_MIST)
        style.configure("Header.TLabel", background=INDIGO, foreground="white", font=("Georgia", 21, "bold"))
        style.configure("HeroSub.TLabel", background=INDIGO, foreground="#F4E9DD", font=("Segoe UI", 10))
        style.configure("Section.TLabel", background=CLAY_MIST, foreground=CLAY, font=("Segoe UI", 10, "bold"))
        style.configure("Summary.TLabel", background=CLAY_MIST, foreground=INK)
        style.configure("Status.TLabel", background=CLAY_MIST, foreground=TERRACOTTA, font=("Segoe UI", 10, "bold"))
        style.configure(
            "Primary.TButton",
            background=TERRACOTTA,
            foreground="white",
            bordercolor=TERRACOTTA,
            lightcolor=TERRACOTTA,
            darkcolor=TERRACOTTA,
            padding=(12, 8),
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Primary.TButton", background=[("active", "#C67454"), ("disabled", "#DAB4A2")])
        style.configure(
            "Gold.TButton",
            background=OCHRE,
            foreground="white",
            bordercolor=OCHRE,
            lightcolor=OCHRE,
            darkcolor=OCHRE,
            padding=(12, 8),
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Gold.TButton", background=[("active", "#BD8532"), ("disabled", "#D6BE95")])
        style.configure(
            "Utility.TButton",
            background="white",
            foreground=CLAY,
            bordercolor=CLAY,
            lightcolor="white",
            darkcolor="white",
            padding=(10, 7),
        )
        style.map("Utility.TButton", background=[("active", CLAY_MIST)], foreground=[("active", CLAY)])
        style.configure("Treeview", background="white", fieldbackground="white", foreground=INK, rowheight=26, bordercolor=BORDER)
        style.configure("Treeview.Heading", background=INDIGO, foreground="white", font=("Segoe UI", 9, "bold"))

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)

        hero = ttk.Frame(root, style="Hero.TFrame", padding=(18, 16))
        hero.pack(fill="x")
        ttk.Label(hero, text="LOTUS", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            hero,
            text="Standalone social agency scoring workspace for local notes.",
            style="HeroSub.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        toolbar = ttk.Frame(root, style="Toolbar.TFrame", padding=(16, 12))
        toolbar.pack(fill="x", pady=(0, 12))
        ttk.Button(toolbar, text="Upload Notes", style="Gold.TButton", command=self.upload_notes).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(toolbar, text="Refresh Library", style="Utility.TButton", command=self.refresh_notes).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(toolbar, text="Open Lotus Folder", style="Primary.TButton", command=self.open_lotus_folder).grid(row=0, column=2)
        toolbar.columnconfigure(3, weight=1)

        summary = ttk.Frame(root, style="Card.TFrame", padding=(16, 14))
        summary.pack(fill="x", pady=(0, 12))
        ttk.Label(summary, textvariable=self.summary_var, style="Summary.TLabel", wraplength=1260, justify="left").pack(anchor="w")
        ttk.Label(summary, textvariable=self.status_var, style="Status.TLabel").pack(anchor="w", pady=(4, 0))

        body = ttk.Frame(root)
        body.pack(fill="both", expand=True)

        table_frame = ttk.Frame(body, style="Card.TFrame", padding=(10, 10, 10, 6))
        table_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))
        columns = ("title", "agency_score", "creative_score", "strategic_score", "modified", "signals", "file")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.tree.heading("title", text="Lotus note")
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
        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        preview_frame = ttk.Frame(body, style="Card.TFrame", padding=(12, 12))
        preview_frame.pack(side="right", fill="both", expand=True)
        ttk.Label(preview_frame, text="Preview", style="Section.TLabel").pack(anchor="w")
        self.preview_text = tk.Text(
            preview_frame,
            wrap="word",
            bg=SURFACE,
            fg=INK,
            insertbackground=INDIGO,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=OCHRE,
        )
        self.preview_text.pack(fill="both", expand=True, pady=(8, 0))
        self.preview_text.configure(state="disabled")

    def refresh_notes(self) -> None:
        self.notes = lotus.load_lotus_notes(self.lotus_root)
        for item in self.tree.get_children():
            self.tree.delete(item)
        for note in self.notes:
            self.tree.insert(
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
        self.summary_var.set(
            f"LOTUS has {len(self.notes)} note(s). Social agency scoring is local, content-aware, and separate from the other app ideas in this repo."
        )
        self.status_var.set("LOTUS refreshed.")
        if self.notes:
            self._show_note(self.notes[0])
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
            if sys.platform.startswith("win"):
                subprocess.Popen(["explorer.exe", str(self.lotus_root)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(self.lotus_root)])
            else:
                subprocess.Popen(["xdg-open", str(self.lotus_root)])
        except Exception as exc:
            messagebox.showerror("LOTUS", str(exc))

    def _on_note_selected(self, _event: object) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        index = self.tree.index(selection[0])
        if 0 <= index < len(self.notes):
            self._show_note(self.notes[index])

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
            f"lotus_root={app.lotus_root.name}"
        )
        app.destroy()
        return 0
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
