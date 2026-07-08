"""Vergleich zweier SOP-Versionen und Extraktion der geänderten Textstellen.

Aus dem Vergleich (alte Version vs. neue Version) werden "Fragmente"
gewonnen: die konkreten Wortfolgen, die entfernt oder ersetzt wurden.
Diese Fragmente sind die Suchbegriffe für die Konsistenzprüfung –
überall dort, wo der alte Wortlaut noch vorkommt, ist die Änderung
möglicherweise noch nachzuziehen.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field


def normalize(text: str) -> str:
    """Normalisiert Text für Vergleiche (Kleinschreibung, Whitespace).

    Bewusst lower() statt casefold(): casefold ändert die Stringlänge
    ("ß" -> "ss"), wodurch Trefferpositionen im Originaltext nicht mehr
    stimmen würden.
    """
    return re.sub(r"\s+", " ", text).strip().lower()


_EDGE_PUNCT = ".,;:!?()[]{}\"'„“”‚’«»"


def strip_edges(text: str) -> str:
    """Entfernt Satzzeichen an den Rändern (für robustere Suche)."""
    return text.strip(_EDGE_PUNCT + " ")


@dataclass
class ParagraphChange:
    """Eine Änderung auf Absatz-Ebene zwischen alter und neuer Version."""

    kind: str  # "geändert" | "entfernt" | "hinzugefügt" | "verschoben"
    old_text: str = ""
    new_text: str = ""
    old_index: int = -1  # 1-basierte Absatznummer in der alten Version
    new_index: int = -1  # 1-basierte Absatznummer in der neuen Version


@dataclass
class Fragment:
    """Eine geänderte Wortfolge (alter Wortlaut -> neuer Wortlaut)."""

    old_text: str
    new_text: str = ""
    source: str = ""  # Herkunft, z. B. "Absatz 12" oder "manuell"

    @property
    def norm(self) -> str:
        """Normalisierter Suchbegriff (ohne Satzzeichen an den Rändern)."""
        return strip_edges(normalize(self.old_text))


@dataclass
class DiffResult:
    changes: list[ParagraphChange] = field(default_factory=list)
    fragments: list[Fragment] = field(default_factory=list)


# Kurze Fragmente ("C." -> "B.", "5" -> "10") sind allein nicht suchbar.
# Sie werden um unveränderte Kontextwörter erweitert, bis der Suchbegriff
# mindestens diese Länge erreicht (z. B. "Raumklasse C", "beträgt 5 Minuten").
_MIN_SEARCH_LEN = 12
_MAX_CONTEXT_WORDS = 3


def _word_fragments(old_para: str, new_para: str, min_len: int) -> list[Fragment]:
    """Ermittelt geänderte Wortfolgen innerhalb eines Absatzpaars."""
    old_words = old_para.split()
    new_words = new_para.split()
    matcher = difflib.SequenceMatcher(None, old_words, new_words, autojunk=False)
    fragments = []
    for op, o1, o2, n1, n2 in matcher.get_opcodes():
        if op == "equal" or op == "insert":
            continue

        # Kontext erweitern: die Wörter vor o1 bzw. ab o2 sind in alter und
        # neuer Version identisch (equal-Bereiche), daher für beide gültig.
        left = right = 0

        def old_frag() -> str:
            return " ".join(old_words[o1 - left:o2 + right])

        while len(strip_edges(normalize(old_frag()))) < _MIN_SEARCH_LEN:
            expanded = False
            if right < _MAX_CONTEXT_WORDS and o2 + right < len(old_words):
                right += 1
                expanded = True
            if (len(strip_edges(normalize(old_frag()))) < _MIN_SEARCH_LEN
                    and left < _MAX_CONTEXT_WORDS and o1 - left > 0):
                left += 1
                expanded = True
            if not expanded:
                break

        new_frag = " ".join(
            old_words[o1 - left:o1] + new_words[n1:n2] + old_words[o2:o2 + right])
        frag = Fragment(old_text=old_frag(), new_text=strip_edges(new_frag))
        if len(frag.norm) >= min_len:
            fragments.append(frag)
    return fragments


def diff_documents(
    old_paras: list[str],
    new_paras: list[str],
    min_fragment_len: int = 4,
) -> DiffResult:
    """Vergleicht zwei Versionen absatzweise und extrahiert Änderungen."""
    result = DiffResult()
    new_norm_set = {normalize(p) for p in new_paras}
    seen_fragments: set[str] = set()

    def add_fragment(frag: Fragment) -> None:
        if frag.norm and frag.norm not in seen_fragments:
            seen_fragments.add(frag.norm)
            result.fragments.append(frag)

    matcher = difflib.SequenceMatcher(
        None, [normalize(p) for p in old_paras], [normalize(p) for p in new_paras],
        autojunk=False,
    )
    for op, o1, o2, n1, n2 in matcher.get_opcodes():
        if op == "equal":
            continue

        if op == "replace":
            # Absatzpaare einander zuordnen und wortweise vergleichen
            count = max(o2 - o1, n2 - n1)
            for k in range(count):
                oi = o1 + k if o1 + k < o2 else -1
                ni = n1 + k if n1 + k < n2 else -1
                old_text = old_paras[oi] if oi >= 0 else ""
                new_text = new_paras[ni] if ni >= 0 else ""
                if oi >= 0 and ni >= 0:
                    result.changes.append(ParagraphChange(
                        kind="geändert", old_text=old_text, new_text=new_text,
                        old_index=oi + 1, new_index=ni + 1,
                    ))
                    for frag in _word_fragments(old_text, new_text, min_fragment_len):
                        frag.source = f"Absatz {ni + 1}"
                        add_fragment(frag)
                elif oi >= 0:
                    _add_removed(result, old_text, oi, new_norm_set,
                                 min_fragment_len, add_fragment)
                else:
                    result.changes.append(ParagraphChange(
                        kind="hinzugefügt", new_text=new_text, new_index=ni + 1,
                    ))

        elif op == "delete":
            for oi in range(o1, o2):
                _add_removed(result, old_paras[oi], oi, new_norm_set,
                             min_fragment_len, add_fragment)

        elif op == "insert":
            for ni in range(n1, n2):
                result.changes.append(ParagraphChange(
                    kind="hinzugefügt", new_text=new_paras[ni], new_index=ni + 1,
                ))

    return result


def _add_removed(result, old_text, oi, new_norm_set, min_len, add_fragment) -> None:
    """Behandelt einen in der neuen Version entfernten Absatz."""
    if normalize(old_text) in new_norm_set:
        # Identischer Absatz existiert an anderer Stelle -> nur verschoben,
        # kein Suchbegriff (sonst Fehlalarm an der neuen Position).
        result.changes.append(ParagraphChange(
            kind="verschoben", old_text=old_text, old_index=oi + 1,
        ))
        return
    result.changes.append(ParagraphChange(
        kind="entfernt", old_text=old_text, old_index=oi + 1,
    ))
    if len(normalize(old_text)) >= min_len:
        frag = Fragment(old_text=old_text, source=f"Absatz {oi + 1} (alt, entfernt)")
        add_fragment(frag)


def similarity(a: str, b: str) -> float:
    """Ähnlichkeit zweier Texte (0..1), mit schnellem Vorfilter."""
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    if matcher.real_quick_ratio() < 0.6 or matcher.quick_ratio() < 0.6:
        return 0.0
    return matcher.ratio()
