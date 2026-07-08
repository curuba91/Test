"""SOP-Konsistenz-Checker – grafische Oberfläche (Windows: Doppelklick).

Als .pyw gespeichert startet das Programm unter Windows ohne Konsolenfenster.
Benötigt nur eine Python-Standardinstallation (Tkinter ist enthalten).
"""

from __future__ import annotations

import queue
import threading
import traceback
import webbrowser
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from sop_checker.docreader import DocumentReadError
from sop_checker.runner import run_check


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("SOP-Konsistenz-Checker")
        self.minsize(720, 560)
        self._queue: queue.Queue = queue.Queue()
        self._report_path: Path | None = None
        self._running = False
        self._build_ui()
        self.after(100, self._poll_queue)

    # ------------------------------------------------------------- UI-Aufbau
    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=12, pady=12)
        frame.columnconfigure(1, weight=1)

        self.var_new = tk.StringVar()
        self.var_old = tk.StringVar()
        self.var_pool = tk.StringVar()
        self.var_terms = tk.StringVar()
        self.var_sop_id = tk.StringVar()
        self.var_report = tk.StringVar()
        self.var_threshold = tk.DoubleVar(value=0.75)

        def add_file_row(row: int, label: str, var: tk.StringVar, is_dir=False,
                         save=False, hint: str = "") -> None:
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", **pad)
            ttk.Entry(frame, textvariable=var).grid(row=row, column=1, sticky="ew", **pad)
            ttk.Button(frame, text="…", width=3,
                       command=lambda: self._browse(var, is_dir, save)
                       ).grid(row=row, column=2, **pad)
            if hint:
                ttk.Label(frame, text=hint, foreground="#666").grid(
                    row=row + 1, column=1, sticky="w", padx=8)

        add_file_row(0, "Neue Version (geändert):", self.var_new)
        add_file_row(1, "Alte Version (Vergleich):", self.var_old,
                     hint="optional – ohne alte Version werden nur die Suchbegriffe geprüft")
        add_file_row(3, "SOP-Pool (Ordner):", self.var_pool, is_dir=True,
                     hint="optional – wird rekursiv nach .docx/.txt/.md durchsucht")

        ttk.Label(frame, text="Zusätzliche Suchbegriffe:").grid(
            row=5, column=0, sticky="w", **pad)
        ttk.Entry(frame, textvariable=self.var_terms).grid(
            row=5, column=1, columnspan=2, sticky="ew", **pad)
        ttk.Label(frame, text='getrennt durch ";" – optional mit neuem Wortlaut: '
                              '"Raumklasse C => Raumklasse B"',
                  foreground="#666").grid(row=6, column=1, sticky="w", padx=8)

        ttk.Label(frame, text="SOP-ID (für Verweise):").grid(
            row=7, column=0, sticky="w", **pad)
        ttk.Entry(frame, textvariable=self.var_sop_id, width=24).grid(
            row=7, column=1, sticky="w", **pad)
        ttk.Label(frame, text="leer = automatisch aus Dateiname/Kopf erkennen",
                  foreground="#666").grid(row=8, column=1, sticky="w", padx=8)

        ttk.Label(frame, text="Ähnlichkeits-Schwellwert:").grid(
            row=9, column=0, sticky="w", **pad)
        scale_row = ttk.Frame(frame)
        scale_row.grid(row=9, column=1, sticky="ew", **pad)
        self.lbl_threshold = ttk.Label(scale_row, text="75 %", width=6)
        ttk.Scale(scale_row, from_=0.5, to=0.95, variable=self.var_threshold,
                  command=lambda _v: self.lbl_threshold.config(
                      text=f"{self.var_threshold.get():.0%}")
                  ).pack(side="left", fill="x", expand=True)
        self.lbl_threshold.pack(side="left", padx=6)

        add_file_row(10, "Bericht speichern unter:", self.var_report, save=True,
                     hint="leer = Konsistenzbericht_<Name>.html neben der neuen Version")

        buttons = ttk.Frame(frame)
        buttons.grid(row=12, column=0, columnspan=3, sticky="ew", pady=(10, 4))
        self.btn_run = ttk.Button(buttons, text="Prüfung starten", command=self._start)
        self.btn_run.pack(side="left", padx=8)
        self.btn_open = ttk.Button(buttons, text="Bericht öffnen",
                                   command=self._open_report, state="disabled")
        self.btn_open.pack(side="left", padx=8)

        self.log = tk.Text(frame, height=12, state="disabled", wrap="word",
                           background="#1c2833", foreground="#eaecee")
        self.log.grid(row=13, column=0, columnspan=3, sticky="nsew", **pad)
        frame.rowconfigure(13, weight=1)

    # ------------------------------------------------------------- Aktionen
    def _browse(self, var: tk.StringVar, is_dir: bool, save: bool) -> None:
        if is_dir:
            value = filedialog.askdirectory(title="Ordner wählen")
        elif save:
            value = filedialog.asksaveasfilename(
                title="Bericht speichern", defaultextension=".html",
                filetypes=[("HTML-Bericht", "*.html")])
        else:
            value = filedialog.askopenfilename(
                title="Dokument wählen",
                filetypes=[("SOP-Dokumente", "*.docx *.txt *.md"), ("Alle Dateien", "*.*")])
        if value:
            var.set(value)

    def _log(self, msg: str) -> None:
        self._queue.put(("log", msg))

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "log":
                    self.log.configure(state="normal")
                    self.log.insert("end", payload + "\n")
                    self.log.see("end")
                    self.log.configure(state="disabled")
                elif kind == "done":
                    self._running = False
                    self.btn_run.configure(state="normal", text="Prüfung starten")
                    if payload:
                        self._report_path = payload
                        self.btn_open.configure(state="normal")
                        if messagebox.askyesno(
                                "Fertig", "Prüfung abgeschlossen.\nBericht jetzt öffnen?"):
                            self._open_report()
                elif kind == "error":
                    self._running = False
                    self.btn_run.configure(state="normal", text="Prüfung starten")
                    messagebox.showerror("Fehler", payload)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _start(self) -> None:
        if self._running:
            return
        new_path = self.var_new.get().strip()
        if not new_path:
            messagebox.showwarning("Eingabe fehlt",
                                   "Bitte die neue (geänderte) Version auswählen.")
            return
        if not self.var_old.get().strip() and not self.var_terms.get().strip():
            messagebox.showwarning(
                "Eingabe fehlt",
                "Bitte entweder eine alte Version zum Vergleich wählen\n"
                "oder Suchbegriffe eingeben.")
            return
        self._running = True
        self._report_path = None
        self.btn_run.configure(state="disabled", text="läuft …")
        self.btn_open.configure(state="disabled")
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self) -> None:
        try:
            report = run_check(
                new_path=self.var_new.get().strip(),
                old_path=self.var_old.get().strip() or None,
                pool_folder=self.var_pool.get().strip() or None,
                extra_terms_raw=self.var_terms.get(),
                sop_id=self.var_sop_id.get().strip(),
                report_path=self.var_report.get().strip() or None,
                threshold=self.var_threshold.get(),
                log=self._log,
                progress=lambda i, n, name: self._log(f"  [{i}/{n}] {name}"),
            )
            self._queue.put(("done", report))
        except (DocumentReadError, ValueError, OSError) as exc:
            self._queue.put(("error", str(exc)))
        except Exception:
            self._queue.put(("error", traceback.format_exc()))

    def _open_report(self) -> None:
        if self._report_path:
            webbrowser.open(Path(self._report_path).resolve().as_uri())


if __name__ == "__main__":
    App().mainloop()
