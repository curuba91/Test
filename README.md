# AZW3 → PDF Konverter

Konvertiert eigene, rechtmäßig erworbene Kindle-Bücher (AZW3) in PDF – für persönliche Backups.

> **Rechtlicher Hinweis:** Das Entfernen von DRM ist nur für den persönlichen Gebrauch mit eigenen, gekauften Inhalten erlaubt. Prüfe die Gesetze in deinem Land.

---

## Voraussetzungen

| Komponente | Zweck |
|---|---|
| [Calibre](https://calibre-ebook.com/) | Ebook-Verwaltung & Konvertierung |
| [DeDRM_tools (noDRM)](https://github.com/noDRM/DeDRM_tools) | Entfernt DRM aus eigenen Kindle-Dateien |
| Python 3.9+ | Für das Konverter-Skript |

---

## Setup (einmalig)

### 1. Calibre + DeDRM installieren

```bash
bash setup.sh
```

Das Skript installiert Calibre (Linux) und lädt DeDRM_tools herunter.

### 2. DeDRM-Plugin in Calibre einbinden

1. Calibre starten
2. **Einstellungen → Plugins → Plugin aus Datei laden**
3. `DeDRM_tools/DeDRM_plugin.zip` auswählen
4. Calibre **neu starten**

### 3. Kindle-Key konfigurieren

**Option A – Kindle for PC/Mac (einfachste Methode):**
- Kindle for PC/Mac installieren und mit Amazon-Konto anmelden
- DeDRM erkennt den Key automatisch beim ersten Konvertieren

**Option B – Kindle-Gerät (Seriennummer):**
1. Calibre → Einstellungen → Plugins → DeDRM → Anpassen
2. „eKindle-Seriennummern" → Seriennummer eingeben
   (Gerät → Einstellungen → Geräteinformationen)

---

## Benutzung

### Einzelne Datei konvertieren

```bash
python3 convert.py /pfad/zu/buch.azw3
```

### Ganzen Ordner konvertieren

```bash
python3 convert.py /pfad/zu/kindle-ordner/
```

### Mit benutzerdefiniertem Ausgabeordner

```bash
python3 convert.py /pfad/zu/kindle-ordner/ -o /pfad/zu/pdfs/
```

### Optionen

```
python3 convert.py --help

Optionen:
  -o, --output DIR       Ausgabeverzeichnis
  --no-page-numbers      Seitenzahlen unterdrücken
  --paper-size {a4,a5,letter,legal}   Papierformat (Standard: a4)
```

---

## Wo liegen die Kindle-Dateien?

| Plattform | Pfad |
|---|---|
| Windows | `C:\Users\<Name>\Documents\My Kindle Content\` |
| macOS | `~/Library/Containers/com.amazon.Kindle/Data/Library/Application Support/Kindle/My Kindle Content/` |
| Linux (Wine) | `~/.wine/drive_c/users/<Name>/Documents/My Kindle Content/` |

---

## Fehlerbehebung

| Fehler | Lösung |
|---|---|
| `DRM` in Fehlermeldung | DeDRM-Plugin prüfen; Key neu konfigurieren |
| `ebook-convert nicht gefunden` | Calibre installieren, PATH prüfen |
| Konvertierung schlägt fehl | Datei gehört evtl. anderem Amazon-Konto |
