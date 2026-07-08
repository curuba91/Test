"""SOP-Konsistenz-Checker.

Prüft bei einer Änderung an einer SOP:
  1. ob die Änderung an weiteren Stellen im selben Dokument nachgezogen
     werden muss (interne Konsistenz), und
  2. ob weitere SOPs aus einem Dokumenten-Pool betroffen sind
     (dokumentübergreifende Konsistenz).

Funktioniert ohne Zusatzpakete (nur Python-Standardbibliothek) und liest
.docx-, .txt- und .md-Dateien.
"""

__version__ = "1.0.0"
