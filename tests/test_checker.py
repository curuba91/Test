"""End-to-End-Tests für den SOP-Konsistenz-Checker (nur Standardbibliothek)."""

import tempfile
import unittest
import zipfile
from pathlib import Path

from sop_checker.analysis import check_internal, check_pool, parse_extra_terms
from sop_checker.diffing import diff_documents
from sop_checker.docreader import find_pool_documents, read_document
from sop_checker.runner import guess_sop_id, run_check

OLD_SOP = """SOP-042 Reinigung Abfüllanlage, Version 3

1. Zweck
Diese SOP beschreibt die Reinigung der Abfüllanlage in Raumklasse C.

2. Durchführung
Die Anlage wird mit Reinigungsmittel Deskosept AF gereinigt.
Die Einwirkzeit beträgt 5 Minuten.

3. Dokumentation
Die Reinigung in Raumklasse C ist im Logbuch LB-07 zu dokumentieren.
"""

NEW_SOP = """SOP-042 Reinigung Abfüllanlage, Version 4

1. Zweck
Diese SOP beschreibt die Reinigung der Abfüllanlage in Raumklasse B.

2. Durchführung
Die Anlage wird mit Reinigungsmittel Deskosept AF gereinigt.
Die Einwirkzeit beträgt 10 Minuten.

3. Dokumentation
Die Reinigung in Raumklasse C ist im Logbuch LB-07 zu dokumentieren.
"""

POOL_SOP_AFFECTED = """SOP-100 Umgebungsmonitoring

1. Zweck
Monitoring der Räume.

2. Verweise
Die Reinigung erfolgt gemäß SOP-042 in Raumklasse C.
Die Einwirkzeit beträgt 5 Minuten.
"""

POOL_SOP_CLEAN = """SOP-200 Wareneingang

1. Zweck
Prüfung eingehender Ware. Keine Berührungspunkte mit der Abfüllanlage.
"""


def make_docx(path: Path, paragraphs: list[str]) -> None:
    """Erzeugt eine minimale .docx-Datei mit den gegebenen Absätzen."""
    ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    body = "".join(
        f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs
    )
    document = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f"<w:document {ns}><w:body>{body}</w:body></w:document>")
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.'
        'openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'
    )
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/'
            '2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", document)


class CheckerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "SOP-042_v3.txt").write_text(OLD_SOP, encoding="utf-8")
        (self.dir / "SOP-042_v4.txt").write_text(NEW_SOP, encoding="utf-8")
        pool = self.dir / "pool"
        pool.mkdir()
        (pool / "SOP-100.txt").write_text(POOL_SOP_AFFECTED, encoding="utf-8")
        (pool / "SOP-200.txt").write_text(POOL_SOP_CLEAN, encoding="utf-8")
        self.pool = pool

    def tearDown(self):
        self.tmp.cleanup()

    def test_docx_roundtrip(self):
        docx = self.dir / "test.docx"
        make_docx(docx, ["Absatz eins", "Absatz zwei mit Raumklasse C"])
        paras = read_document(docx)
        self.assertEqual(paras, ["Absatz eins", "Absatz zwei mit Raumklasse C"])

    def test_diff_finds_changed_fragments(self):
        old = read_document(self.dir / "SOP-042_v3.txt")
        new = read_document(self.dir / "SOP-042_v4.txt")
        diff = diff_documents(old, new)
        old_frags = [f.norm for f in diff.fragments]
        self.assertTrue(any("raumklasse c" in f for f in old_frags))
        self.assertTrue(any("5" in f for f in old_frags))

    def test_internal_check_flags_unchanged_spot(self):
        old = read_document(self.dir / "SOP-042_v3.txt")
        new = read_document(self.dir / "SOP-042_v4.txt")
        diff = diff_documents(old, new)
        findings = check_internal(new, diff)
        # "Raumklasse C" steht im Abschnitt Dokumentation noch drin
        texts = [f.paragraph_text for f in findings]
        self.assertTrue(any("Logbuch LB-07" in t for t in texts))

    def test_pool_check_flags_affected_document_only(self):
        old = read_document(self.dir / "SOP-042_v3.txt")
        new = read_document(self.dir / "SOP-042_v4.txt")
        diff = diff_documents(old, new)
        paths = find_pool_documents(self.pool)
        results = check_pool(paths, diff, sop_id="SOP-042")
        by_name = {r.path.name: r for r in results}
        self.assertTrue(by_name["SOP-100.txt"].findings)
        self.assertFalse(by_name["SOP-200.txt"].findings)
        categories = {f.category for f in by_name["SOP-100.txt"].findings}
        self.assertIn("alter_wortlaut", categories)
        self.assertIn("sop_referenz", categories)

    def test_run_check_writes_report(self):
        report = run_check(
            new_path=self.dir / "SOP-042_v4.txt",
            old_path=self.dir / "SOP-042_v3.txt",
            pool_folder=self.pool,
        )
        html = Path(report).read_text(encoding="utf-8")
        self.assertIn("SOP-Konsistenzbericht", html)
        self.assertIn("SOP-100.txt", html)
        self.assertNotIn("<h3>SOP-200.txt", html)

    def test_manual_terms_without_old_version(self):
        report = run_check(
            new_path=self.dir / "SOP-042_v4.txt",
            pool_folder=self.pool,
            extra_terms_raw="Deskosept AF => Deskosept neu; Logbuch LB-07",
        )
        html = Path(report).read_text(encoding="utf-8")
        self.assertIn("Deskosept", html)

    def test_guess_sop_id(self):
        self.assertEqual(guess_sop_id(Path("SOP-042_v4.docx"), []), "SOP-042")
        self.assertEqual(guess_sop_id(Path("Reinigung.docx"),
                                      ["SOP 17 Reinigung", "…"]), "SOP 17")

    def test_parse_extra_terms(self):
        terms = parse_extra_terms("Raumklasse C => Raumklasse B; Gerät XY-100")
        self.assertEqual(len(terms), 2)
        self.assertEqual(terms[0].new_text, "Raumklasse B")
        self.assertEqual(terms[1].old_text, "Gerät XY-100")

    def test_moved_paragraph_not_flagged(self):
        old = ["Titel", "Absatz A bleibt gleich", "Absatz B wird verschoben und ist lang genug"]
        new = ["Titel", "Absatz B wird verschoben und ist lang genug", "Absatz A bleibt gleich"]
        diff = diff_documents(old, new)
        findings = check_internal(new, diff)
        self.assertEqual([f for f in findings if f.category == "alter_wortlaut"], [])


if __name__ == "__main__":
    unittest.main()
