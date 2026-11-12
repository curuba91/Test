"""Startdatei des AI Use Case Hub (Doppelklick).

Für die Entwicklung auch von der Konsole:
    python -B AI_UseCase_Hub.pyw --no-browser
"""

import sys

# Der Programmordner darf in einem synchronisierten Ordner liegen und wird zur
# Laufzeit nur gelesen: kein __pycache__ erzeugen.
sys.dont_write_bytecode = True

import os
import time
import traceback

PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
if PROGRAM_DIR not in sys.path:
    sys.path.insert(0, PROGRAM_DIR)


def _python_for_pip() -> str:
    """python.exe statt pythonw.exe, damit pip eine normale Ausgabe hat."""
    exe = sys.executable or "python"
    folder, name = os.path.split(exe)
    if name.lower() == "pythonw.exe" and os.path.isfile(os.path.join(folder, "python.exe")):
        return os.path.join(folder, "python.exe")
    return exe


def _run_pip(result: dict) -> None:
    import subprocess

    command = [_python_for_pip(), "-m", "pip", "install", "--user", "--disable-pip-version-check", "openpyxl"]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        done = subprocess.run(command, capture_output=True, text=True, creationflags=flags, timeout=600)
        result["code"] = done.returncode
        result["output"] = (done.stdout or "") + (done.stderr or "")
    except Exception as exc:  # pip fehlt, Zeitüberschreitung, kein Netz
        result["code"] = 1
        result["output"] = str(exc)


def _ensure_openpyxl() -> None:
    """Installiert openpyxl einmalig im Benutzerkontext, mit sichtbarem Fortschritt."""
    try:
        import openpyxl  # noqa: F401
        return
    except ImportError:
        pass

    import threading

    result = {}
    worker = threading.Thread(target=_run_pip, args=(result,), daemon=True)
    worker.start()
    try:
        import tkinter
        from tkinter import ttk

        root = tkinter.Tk()
        root.title("AI Use Case Hub")
        root.resizable(False, False)
        ttk.Label(root, text="Einmalige Einrichtung: Die Excel-Bibliothek openpyxl wird installiert …",
                  padding=16).pack()
        bar = ttk.Progressbar(root, mode="indeterminate", length=420)
        bar.pack(padx=16, pady=(0, 16))
        bar.start(12)

        def poll():
            if worker.is_alive():
                root.after(200, poll)
            else:
                root.destroy()

        root.protocol("WM_DELETE_WINDOW", lambda: None)  # Installation nicht abbrechen
        root.after(200, poll)
        root.mainloop()
    except Exception:
        pass  # ohne Fenster einfach warten
    worker.join()

    import importlib
    import site

    try:
        site.addsitedir(site.getusersitepackages())
    except Exception:
        pass
    importlib.invalidate_caches()
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        tail = (result.get("output") or "keine Ausgabe")[-1500:]
        raise RuntimeError(
            "openpyxl konnte nicht installiert werden. Manuell ausführen:\n"
            "    python -m pip install --user openpyxl\n\nAusgabe von pip:\n" + tail
        ) from None


def _fatal(text: str) -> None:
    """Fehler beim Start protokollieren und anzeigen (unter pythonw gibt es keine Konsole)."""
    log_path = ""
    try:
        from hub.config import default_data_dir

        folder = default_data_dir()
        folder.mkdir(parents=True, exist_ok=True)
        log_path = str(folder / "hub_fehler.log")
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Start fehlgeschlagen\n{text}\n")
    except Exception:
        pass
    message = "Der AI Use Case Hub konnte nicht gestartet werden.\n\n" + text.strip()[-1200:]
    if log_path:
        message += f"\n\nProtokoll: {log_path}"
    try:
        import tkinter
        from tkinter import messagebox

        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror("AI Use Case Hub", message)
        root.destroy()
    except Exception:
        if sys.stderr is not None:
            sys.stderr.write(message + "\n")


def main() -> int:
    try:
        _ensure_openpyxl()
        from hub import server

        return server.main()
    except SystemExit:
        raise
    except Exception:
        _fatal(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
