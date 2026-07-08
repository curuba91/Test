"""Gemeinsamer Ablauf für CLI und GUI: Prüfung ausführen, Bericht schreiben."""

from __future__ import annotations

import re
from pathlib import Path

from .analysis import AnalysisResult, check_internal, check_pool, parse_extra_terms
from .diffing import diff_documents
from .docreader import find_pool_documents, read_document
from .report import build_report, write_report

_SOP_ID_PATTERN = re.compile(r"\b(SOP[-_ ]?\d+(?:[.\-]\d+)*)", re.IGNORECASE)


def guess_sop_id(new_path: Path, first_paragraphs: list[str]) -> str:
    """Versucht, die SOP-ID aus Dateiname oder Dokumentkopf zu erkennen."""
    match = _SOP_ID_PATTERN.search(new_path.stem)
    if match:
        return match.group(1)
    for para in first_paragraphs[:10]:
        match = _SOP_ID_PATTERN.search(para)
        if match:
            return match.group(1)
    return ""


def run_check(
    new_path: str | Path,
    old_path: str | Path | None = None,
    pool_folder: str | Path | None = None,
    extra_terms_raw: str = "",
    sop_id: str = "",
    report_path: str | Path | None = None,
    threshold: float = 0.75,
    min_fragment_len: int = 4,
    log=lambda msg: None,
    progress=None,
) -> Path:
    """Führt die komplette Prüfung aus und schreibt den HTML-Bericht.

    Gibt den Pfad des Berichts zurück.
    """
    new_path = Path(new_path)
    log(f"Lese neue Version: {new_path.name}")
    new_paras = read_document(new_path)
    log(f"  {len(new_paras)} Absätze gelesen.")

    diff = None
    old_name = ""
    if old_path:
        old_path = Path(old_path)
        old_name = old_path.name
        log(f"Lese alte Version: {old_path.name}")
        old_paras = read_document(old_path)
        log(f"  {len(old_paras)} Absätze gelesen.")
        log("Vergleiche Versionen …")
        diff = diff_documents(old_paras, new_paras, min_fragment_len)
        log(f"  {len(diff.changes)} Änderungen, {len(diff.fragments)} geänderte Textstellen.")

    extra_terms = parse_extra_terms(extra_terms_raw)
    if extra_terms:
        log(f"{len(extra_terms)} manuelle Suchbegriffe.")

    if not diff and not extra_terms:
        raise ValueError(
            "Nichts zu prüfen: Entweder eine alte Version zum Vergleich "
            "oder manuelle Suchbegriffe angeben."
        )

    if not sop_id:
        sop_id = guess_sop_id(new_path, new_paras)
        if sop_id:
            log(f"SOP-ID erkannt: {sop_id}")

    result = AnalysisResult()

    log("Prüfe interne Konsistenz der neuen Version …")
    if diff:
        result.internal_findings = check_internal(new_paras, diff, extra_terms, threshold)
    else:
        from .diffing import DiffResult
        result.internal_findings = check_internal(new_paras, DiffResult(), extra_terms, threshold)
    log(f"  {len(result.internal_findings)} offene Stellen im Dokument.")

    if pool_folder:
        pool_folder = Path(pool_folder)
        exclude = [new_path] + ([old_path] if old_path else [])
        pool_paths = find_pool_documents(pool_folder, exclude=exclude)
        log(f"Prüfe SOP-Pool: {len(pool_paths)} Dokumente in {pool_folder} …")
        result.pool_results = check_pool(
            pool_paths, diff, extra_terms, sop_id, threshold, progress=progress)
        affected = sum(1 for r in result.pool_results if r.findings)
        log(f"  {result.pool_findings_count} Fundstellen in {affected} Dokumenten.")

    if report_path is None:
        report_path = new_path.with_name(f"Konsistenzbericht_{new_path.stem}.html")
    report_html = build_report(
        result, diff, new_path.name, old_name,
        str(pool_folder) if pool_folder else "",
    )
    written = write_report(report_html, report_path)
    log(f"Bericht gespeichert: {written}")
    return written
