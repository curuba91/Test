"""Kommandozeilen-Schnittstelle.

Beispiel:
    python -m sop_checker --alt "SOP-042_v3.docx" --neu "SOP-042_v4.docx" \\
        --pool "P:/QM/SOPs" --bericht bericht.html
"""

from __future__ import annotations

import argparse
import sys

from .docreader import DocumentReadError
from .runner import run_check


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sop_checker",
        description="Prüft SOP-Änderungen auf Konsistenz innerhalb des Dokuments "
                    "und gegen einen Pool weiterer SOPs.",
    )
    parser.add_argument("--neu", required=True,
                        help="Neue (geänderte) Version der SOP (.docx/.txt/.md)")
    parser.add_argument("--alt",
                        help="Alte Version der SOP zum Vergleich")
    parser.add_argument("--pool",
                        help="Ordner mit weiteren SOPs (wird rekursiv durchsucht)")
    parser.add_argument("--begriffe", default="",
                        help="Zusätzliche Suchbegriffe, getrennt durch ';'. "
                             "Mit '=>' kann der neue Wortlaut angegeben werden, "
                             "z. B. \"Raumklasse C => Raumklasse B\"")
    parser.add_argument("--sop-id", default="",
                        help="SOP-Kennung für die Verweis-Suche (sonst automatisch erkannt)")
    parser.add_argument("--bericht",
                        help="Zieldatei für den HTML-Bericht "
                             "(Standard: Konsistenzbericht_<Name>.html neben der neuen Version)")
    parser.add_argument("--schwellwert", type=float, default=0.75,
                        help="Ähnlichkeits-Schwellwert 0..1 für 'ähnliche Passagen' (Standard 0.75)")
    parser.add_argument("--min-fragment", type=int, default=4,
                        help="Minimale Länge geänderter Textstellen für die Suche (Standard 4)")
    args = parser.parse_args(argv)

    def progress(i, total, name):
        print(f"  [{i}/{total}] {name}", file=sys.stderr)

    try:
        run_check(
            new_path=args.neu,
            old_path=args.alt,
            pool_folder=args.pool,
            extra_terms_raw=args.begriffe,
            sop_id=args.sop_id,
            report_path=args.bericht,
            threshold=args.schwellwert,
            min_fragment_len=args.min_fragment,
            log=print,
            progress=progress,
        )
    except (DocumentReadError, ValueError, OSError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
