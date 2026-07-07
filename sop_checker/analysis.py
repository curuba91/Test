"""Konsistenzprüfungen: innerhalb des Dokuments und gegen den SOP-Pool."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .diffing import DiffResult, Fragment, normalize, similarity
from .docreader import DocumentReadError, read_document


@dataclass
class Finding:
    """Eine gefundene Stelle, die geprüft/angepasst werden muss."""

    category: str      # "alter_wortlaut" | "aehnliche_passage" | "sop_referenz" | "suchbegriff"
    document: str      # Dateiname bzw. "neue Version"
    paragraph_index: int  # 1-basierte Absatznummer
    paragraph_text: str
    match_text: str    # der konkret gefundene Wortlaut
    match_start: int = -1  # Position des Treffers im Absatz (für Hervorhebung)
    suggestion: str = ""   # z. B. der neue Wortlaut
    detail: str = ""


@dataclass
class PoolDocumentResult:
    path: Path
    findings: list[Finding] = field(default_factory=list)
    error: str = ""


@dataclass
class AnalysisResult:
    internal_findings: list[Finding] = field(default_factory=list)
    pool_results: list[PoolDocumentResult] = field(default_factory=list)

    @property
    def pool_findings_count(self) -> int:
        return sum(len(r.findings) for r in self.pool_results)


def _find_occurrences(
    paragraphs: list[str],
    fragment: Fragment,
    document_name: str,
    category: str,
) -> list[Finding]:
    """Sucht den alten Wortlaut eines Fragments in allen Absätzen."""
    findings = []
    needle = fragment.norm
    if not needle:
        return findings
    for idx, para in enumerate(paragraphs):
        haystack = para.lower()  # längenerhaltend, passend zu normalize()
        start = 0
        while True:
            pos = haystack.find(needle, start)
            if pos < 0:
                break
            findings.append(Finding(
                category=category,
                document=document_name,
                paragraph_index=idx + 1,
                paragraph_text=para,
                match_text=para[pos:pos + len(needle)],
                match_start=pos,
                suggestion=fragment.new_text,
                detail=f"Geändert in: {fragment.source}" if fragment.source else "",
            ))
            start = pos + max(len(needle), 1)
    return findings


def _find_similar_paragraphs(
    paragraphs: list[str],
    changed_old_paras: list[tuple[str, str]],  # (alter Absatz, neuer Absatz)
    document_name: str,
    threshold: float,
) -> list[Finding]:
    """Findet Absätze, die einem geänderten (alten) Absatz stark ähneln."""
    findings = []
    for idx, para in enumerate(paragraphs):
        para_norm = normalize(para)
        best_ratio, best_pair = 0.0, None
        for old_text, new_text in changed_old_paras:
            old_norm = normalize(old_text)
            if para_norm == normalize(new_text):
                continue  # das ist bereits der neue Stand
            ratio = similarity(para_norm, old_norm)
            if ratio >= threshold and ratio > best_ratio:
                best_ratio, best_pair = ratio, (old_text, new_text)
        if best_pair:
            findings.append(Finding(
                category="aehnliche_passage",
                document=document_name,
                paragraph_index=idx + 1,
                paragraph_text=para,
                match_text=para,
                suggestion=best_pair[1],
                detail=f"Ähnlichkeit {best_ratio:.0%} zum alten Wortlaut: „{best_pair[0]}“",
            ))
    return findings


def check_internal(
    new_paras: list[str],
    diff: DiffResult,
    extra_terms: list[Fragment] | None = None,
    threshold: float = 0.75,
) -> list[Finding]:
    """Prüft die NEUE Version: Wo steht der alte Wortlaut noch im Dokument?"""
    findings: list[Finding] = []
    for frag in diff.fragments:
        findings.extend(_find_occurrences(new_paras, frag, "neue Version", "alter_wortlaut"))
    for term in extra_terms or []:
        findings.extend(_find_occurrences(new_paras, term, "neue Version", "suchbegriff"))

    changed_pairs = [
        (c.old_text, c.new_text) for c in diff.changes
        if c.kind == "geändert" and len(normalize(c.old_text)) >= 30
    ]
    findings.extend(_find_similar_paragraphs(new_paras, changed_pairs, "neue Version", threshold))
    findings.sort(key=lambda f: (f.paragraph_index, f.match_start))
    return findings


def check_pool(
    pool_paths: list[Path],
    diff: DiffResult | None,
    extra_terms: list[Fragment] | None = None,
    sop_id: str = "",
    threshold: float = 0.75,
    progress=None,
) -> list[PoolDocumentResult]:
    """Prüft alle Pool-Dokumente auf Betroffenheit durch die Änderung."""
    results = []
    changed_pairs = []
    fragments: list[Fragment] = []
    if diff:
        fragments = list(diff.fragments)
        changed_pairs = [
            (c.old_text, c.new_text) for c in diff.changes
            if c.kind == "geändert" and len(normalize(c.old_text)) >= 30
        ]
    sop_id_norm = normalize(sop_id)

    for i, path in enumerate(pool_paths):
        if progress:
            progress(i + 1, len(pool_paths), path.name)
        doc_result = PoolDocumentResult(path=path)
        try:
            paras = read_document(path)
        except DocumentReadError as exc:
            doc_result.error = str(exc)
            results.append(doc_result)
            continue

        for frag in fragments:
            doc_result.findings.extend(
                _find_occurrences(paras, frag, path.name, "alter_wortlaut"))
        for term in extra_terms or []:
            doc_result.findings.extend(
                _find_occurrences(paras, term, path.name, "suchbegriff"))
        doc_result.findings.extend(
            _find_similar_paragraphs(paras, changed_pairs, path.name, threshold))

        if sop_id_norm:
            ref = Fragment(old_text=sop_id, source="SOP-ID")
            for f in _find_occurrences(paras, ref, path.name, "sop_referenz"):
                f.detail = "Dieses Dokument verweist auf die geänderte SOP."
                doc_result.findings.append(f)

        doc_result.findings.sort(key=lambda f: (f.paragraph_index, f.match_start))
        results.append(doc_result)

    return results


def parse_extra_terms(raw: str) -> list[Fragment]:
    """Wandelt manuell eingegebene Suchbegriffe (durch ; oder , getrennt) um.

    Optional kann mit '=>' ein neuer Wortlaut angegeben werden,
    z. B.:  "Raumklasse C => Raumklasse B; Gerät XY-100"
    """
    terms = []
    for part in raw.replace(",", ";").split(";"):
        part = part.strip()
        if not part:
            continue
        if "=>" in part:
            old, new = part.split("=>", 1)
            terms.append(Fragment(old_text=old.strip(), new_text=new.strip(), source="manuell"))
        else:
            terms.append(Fragment(old_text=part, source="manuell"))
    return terms
