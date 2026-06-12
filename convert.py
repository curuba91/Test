#!/usr/bin/env python3
"""
AZW3 → PDF Konverter
Voraussetzungen:
  - Calibre installiert (ebook-convert im PATH)
  - DeDRM-Plugin in Calibre eingebunden (siehe setup.sh)
  - Kindle-Seriennummer oder Kindle for PC/Mac für Key-Extraktion
"""

import argparse
import subprocess
import sys
from pathlib import Path


PDF_OPTIONS = [
    "--pdf-page-numbers",
    "--paper-size", "a4",
    "--pdf-serif-family", "Georgia",
    "--margin-left", "36",
    "--margin-right", "36",
    "--margin-top", "36",
    "--margin-bottom", "36",
]


def check_calibre() -> None:
    try:
        result = subprocess.run(
            ["ebook-convert", "--version"],
            capture_output=True, text=True, check=True
        )
        print(f"[OK] {result.stdout.strip().splitlines()[0]}")
    except FileNotFoundError:
        sys.exit(
            "[FEHLER] 'ebook-convert' nicht gefunden.\n"
            "Bitte Calibre installieren und setup.sh ausführen."
        )


def convert_file(azw3_path: Path, output_dir: Path, extra_opts: list[str]) -> bool:
    pdf_path = output_dir / azw3_path.with_suffix(".pdf").name
    if pdf_path.exists():
        print(f"[SKIP] Bereits vorhanden: {pdf_path.name}")
        return True

    print(f"[...] Konvertiere: {azw3_path.name} → {pdf_path.name}")
    cmd = ["ebook-convert", str(azw3_path), str(pdf_path)] + PDF_OPTIONS + extra_opts

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        size_mb = pdf_path.stat().st_size / 1_048_576
        print(f"[ OK] {pdf_path.name}  ({size_mb:.1f} MB)")
        return True

    print(f"[ERR] {azw3_path.name}")
    for line in result.stderr.splitlines():
        if any(kw in line for kw in ("Error", "error", "DRM", "drm", "Traceback")):
            print(f"      {line}")
    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Konvertiert AZW3-Dateien nach PDF via Calibre + DeDRM."
    )
    parser.add_argument(
        "input",
        help="Einzelne .azw3-Datei oder Verzeichnis mit .azw3-Dateien",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Ausgabeverzeichnis (Standard: neben den Quelldateien)",
    )
    parser.add_argument(
        "--no-page-numbers",
        action="store_true",
        help="Seitenzahlen im PDF unterdrücken",
    )
    parser.add_argument(
        "--paper-size",
        default="a4",
        choices=["a4", "a5", "letter", "legal"],
        help="Papierformat (Standard: a4)",
    )
    args = parser.parse_args()

    check_calibre()

    input_path = Path(args.input).expanduser().resolve()
    if input_path.is_file():
        if input_path.suffix.lower() != ".azw3":
            sys.exit(f"[FEHLER] Keine .azw3-Datei: {input_path}")
        files = [input_path]
        default_output = input_path.parent
    elif input_path.is_dir():
        files = sorted(input_path.glob("*.azw3")) + sorted(input_path.glob("*.AZW3"))
        if not files:
            sys.exit(f"[FEHLER] Keine .azw3-Dateien in: {input_path}")
        default_output = input_path
    else:
        sys.exit(f"[FEHLER] Pfad nicht gefunden: {input_path}")

    output_dir = Path(args.output).expanduser().resolve() if args.output else default_output
    output_dir.mkdir(parents=True, exist_ok=True)

    # Optionen aus CLI-Argumenten übernehmen
    extra_opts = ["--paper-size", args.paper_size]
    if args.no_page_numbers:
        extra_opts = [o for o in PDF_OPTIONS if o != "--pdf-page-numbers"] + extra_opts

    print(f"\nQuelle    : {input_path}")
    print(f"Ausgabe   : {output_dir}")
    print(f"Dateien   : {len(files)}\n")

    ok = sum(convert_file(f, output_dir, extra_opts) for f in files)
    failed = len(files) - ok

    print(f"\n{'='*50}")
    print(f"Ergebnis: {ok}/{len(files)} erfolgreich konvertiert")
    if failed:
        print(
            f"\nHinweis: {failed} Datei(en) fehlgeschlagen.\n"
            "Mögliche Ursachen:\n"
            "  • DeDRM-Plugin nicht installiert oder falsch konfiguriert\n"
            "  • Kindle-Seriennummer fehlt (Einstellungen → Plugins → DeDRM)\n"
            "  • Datei gehört zu einem anderen Amazon-Konto"
        )
    print(f"{'='*50}\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
