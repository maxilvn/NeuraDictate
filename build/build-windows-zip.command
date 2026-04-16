#!/bin/zsh
# Builds a Windows installer ZIP that users can download and run install.bat from

set -e
BUILD_DIR="$(cd "$(dirname "$0")" && pwd -P)"
DIR="$(cd "$BUILD_DIR/.." && pwd -P)"
cd "$DIR"

echo "Building NeuraDictate-Windows.zip..."

BUILD=/tmp/NeuraDictate-win
rm -rf "$BUILD"
mkdir -p "$BUILD/NeuraDictate"

# Copy everything needed for Windows install
cp -R "$DIR/voice_input" "$BUILD/NeuraDictate/"
cp "$DIR/start.py" "$BUILD/NeuraDictate/"
cp "$DIR/icon.png" "$BUILD/NeuraDictate/"
cp "$DIR/logo.png" "$BUILD/NeuraDictate/"
cp "$DIR/install.bat" "$BUILD/NeuraDictate/"
cp "$DIR/README.md" "$BUILD/NeuraDictate/"

# Create a big, obvious INSTALL.txt
cat > "$BUILD/NeuraDictate/INSTALL.txt" << 'INSTALL'
===============================
  NeuraDictate Installation
===============================

1) Doppelklick auf install.bat

Das war's! Der Installer:
- Installiert Python (falls noetig)
- Laedt das Whisper-Model herunter
- Installiert die App nach %LOCALAPPDATA%\NeuraDictate
- Erstellt Verknuepfungen auf Desktop, Startmenue, Autostart
- Startet die App

Bei Sicherheitswarnung von Windows Defender:
- Klicke "Weitere Informationen"
- Dann "Trotzdem ausfuehren"

Nach der Installation kannst du diesen Ordner loeschen.

Bedienung:
- Right Alt gedrueckt halten = Aufnahme
- Loslassen = Text wird eingefuegt
- Settings ueber das Tray-Icon (unten rechts)
INSTALL

# Remove macOS-only files and cache
find "$BUILD" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$BUILD" -name ".DS_Store" -delete 2>/dev/null || true

# Create ZIP
cd "$BUILD"
rm -f "$DIR/NeuraDictate-Windows.zip"
zip -r -q "$DIR/NeuraDictate-Windows.zip" NeuraDictate/

echo ""
echo "  [+] NeuraDictate-Windows.zip erstellt"
echo "  Groesse: $(du -h "$DIR/NeuraDictate-Windows.zip" | cut -f1)"
echo ""
echo "  User-Flow auf Windows:"
echo "    1. ZIP herunterladen"
echo "    2. Entpacken (Rechtsklick > Alle extrahieren)"
echo "    3. Doppelklick auf install.bat"
echo ""
