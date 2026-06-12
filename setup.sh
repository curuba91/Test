#!/usr/bin/env bash
# Setup-Script: Installiert Calibre und lädt DeDRM_tools herunter.
# Anschließend muss das DeDRM-Plugin manuell in Calibre eingebunden werden.
# Nutzung: bash setup.sh

set -e

echo "=== AZW3-zu-PDF Konverter – Setup ==="
echo ""

# ── Calibre installieren ──────────────────────────────────────────────────────
if command -v calibredb &>/dev/null; then
    echo "[OK] Calibre ist bereits installiert: $(calibredb --version 2>&1 | head -1)"
else
    echo "[...] Installiere Calibre..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo -v
        wget -nv -O- https://download.calibre-ebook.com/linux-installer.sh | sudo sh /dev/stdin
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Bitte Calibre von https://calibre-ebook.com/download_osx herunterladen und installieren."
        exit 1
    else
        echo "Bitte Calibre von https://calibre-ebook.com/download_windows herunterladen und installieren."
        exit 1
    fi
fi

# ── DeDRM_tools herunterladen ─────────────────────────────────────────────────
DEDRM_DIR="./DeDRM_tools"
DEDRM_RELEASE_URL="https://github.com/noDRM/DeDRM_tools/releases/latest/download/DeDRM_tools.zip"

if [[ -d "$DEDRM_DIR" ]]; then
    echo "[OK] DeDRM_tools-Verzeichnis existiert bereits."
else
    echo "[...] Lade DeDRM_tools herunter..."
    mkdir -p "$DEDRM_DIR"
    wget -q "$DEDRM_RELEASE_URL" -O /tmp/DeDRM_tools.zip
    unzip -q /tmp/DeDRM_tools.zip -d "$DEDRM_DIR"
    rm /tmp/DeDRM_tools.zip
    echo "[OK] DeDRM_tools entpackt nach: $DEDRM_DIR"
fi

# ── Anleitung: Plugin in Calibre einbinden ────────────────────────────────────
echo ""
echo "============================================================"
echo "  WICHTIG: DeDRM-Plugin manuell in Calibre einbinden"
echo "============================================================"
echo ""
echo "1. Starte Calibre (GUI)"
echo "2. Einstellungen → Plugins → Plugin aus Datei laden"
echo "3. Wähle: $DEDRM_DIR/DeDRM_plugin.zip"
echo "4. Calibre neu starten"
echo ""
echo "Für Kindle-Geräte/Keys:"
echo "  Einstellungen → Plugins → DeDRM → Anpassen → eKindle-Seriennummern"
echo "  Alternativ: Kindle for PC/Mac installieren (wird automatisch erkannt)"
echo ""
echo "============================================================"
echo "  Setup abgeschlossen – führe jetzt convert.py aus"
echo "============================================================"
