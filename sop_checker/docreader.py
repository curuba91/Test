"""Einlesen von SOP-Dokumenten als Liste von Absätzen.

Unterstützte Formate:
  - .docx (Word) – wird direkt als ZIP/XML gelesen, kein python-docx nötig.
    Absätze aus Fließtext und Tabellen werden in Dokumentreihenfolge
    zurückgegeben.
  - .txt / .md   – ein Absatz pro nicht-leerer Zeile bzw. Zeilenblock.

Alle Absätze werden whitespace-normalisiert (mehrfache Leerzeichen /
Umbrüche zu einem Leerzeichen zusammengefasst), damit Positionsangaben
und Textsuchen stabil funktionieren.
"""

from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

SUPPORTED_EXTENSIONS = (".docx", ".txt", ".md")

_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class DocumentReadError(Exception):
    """Dokument konnte nicht gelesen werden."""


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _read_docx(path: Path) -> list[str]:
    try:
        with zipfile.ZipFile(path) as zf:
            xml_data = zf.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError, OSError) as exc:
        raise DocumentReadError(f"{path.name}: keine gültige .docx-Datei ({exc})")

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as exc:
        raise DocumentReadError(f"{path.name}: XML-Fehler ({exc})")

    paragraphs: list[str] = []
    # root.iter liefert alle <w:p> in Dokumentreihenfolge,
    # auch die innerhalb von Tabellenzellen.
    for para in root.iter(f"{_W_NS}p"):
        parts: list[str] = []
        for node in para.iter():
            if node.tag == f"{_W_NS}t" and node.text:
                parts.append(node.text)
            elif node.tag in (f"{_W_NS}tab",):
                parts.append(" ")
            elif node.tag in (f"{_W_NS}br", f"{_W_NS}cr"):
                parts.append(" ")
        text = _collapse("".join(parts))
        if text:
            paragraphs.append(text)
    return paragraphs


def _read_plain(path: Path) -> list[str]:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise DocumentReadError(f"{path.name}: {exc}")

    paragraphs = []
    for block in re.split(r"\n\s*\n", raw):
        text = _collapse(block)
        if text:
            paragraphs.append(text)
    return paragraphs


def read_document(path: str | Path) -> list[str]:
    """Liest ein Dokument und gibt die Absätze als Liste zurück."""
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".docx":
        return _read_docx(path)
    if ext in (".txt", ".md"):
        return _read_plain(path)
    raise DocumentReadError(
        f"{path.name}: Format '{ext}' wird nicht unterstützt "
        f"(unterstützt: {', '.join(SUPPORTED_EXTENSIONS)})"
    )


def find_pool_documents(folder: str | Path, exclude: list[Path] | None = None) -> list[Path]:
    """Sucht alle unterstützten Dokumente in einem Ordner (rekursiv)."""
    folder = Path(folder)
    exclude_resolved = {p.resolve() for p in (exclude or [])}
    results = []
    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        if path.name.startswith("~$"):  # Word-Sperrdateien
            continue
        if path.resolve() in exclude_resolved:
            continue
        results.append(path)
    return results
