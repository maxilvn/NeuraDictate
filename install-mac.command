#!/bin/zsh
# NeuraDictate macOS Installer

set -e
DIR="$(cd "$(dirname "$0")" && pwd -P)"
cd "$DIR"

echo ""
echo "  ================================"
echo "    NeuraDictate - Installation"
echo "  ================================"
echo ""

# Check Python
if ! command -v python3 >/dev/null 2>&1; then
    echo "  [X] Python3 nicht gefunden."
    echo "     Installiere Python von https://python.org/downloads"
    exit 1
fi
echo "  [+] Python gefunden: $(python3 --version)"

echo ""
echo "  [1/4] Installiere Dependencies..."
python3 -m pip install --quiet --upgrade pip
python3 -m pip install --quiet faster-whisper sounddevice numpy rumps \
    pyobjc-framework-Quartz pyobjc-framework-Cocoa
echo "  [+] Dependencies installiert"

echo ""
echo "  [2/4] Lade Whisper Model herunter (466 MB)..."
python3 -c "import sys; sys.path.insert(0, '$DIR'); from voice_input.transcriber import download_model; download_model('small')"
echo "  [+] Model heruntergeladen"

echo ""
echo "  [3/4] Installiere NeuraDictate.app nach /Applications..."
if [ -d "$DIR/NeuraDictate.app" ]; then
    # Update the launcher to point to this project directory
    cat > "$DIR/NeuraDictate.app/Contents/MacOS/NeuraDictate" << LAUNCHER
#!/bin/zsh
cd "$DIR"
export NEURADICTATE_HEADLESS=1
exec /usr/bin/env python3 start.py
LAUNCHER
    chmod +x "$DIR/NeuraDictate.app/Contents/MacOS/NeuraDictate"

    # Copy to /Applications
    rm -rf "/Applications/NeuraDictate.app"
    cp -R "$DIR/NeuraDictate.app" /Applications/
    echo "  [+] NeuraDictate.app in /Applications installiert"
else
    echo "  [X] NeuraDictate.app nicht gefunden im Ordner"
    exit 1
fi

echo ""
echo "  [4/4] Autostart einrichten..."
PLIST="$HOME/Library/LaunchAgents/com.neura.dictate.plist"
cat > "$PLIST" << PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.neura.dictate</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/NeuraDictate.app/Contents/MacOS/NeuraDictate</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
PLISTEOF
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "  [+] Startet automatisch bei Login"

echo ""
echo "  ================================"
echo "    Installation abgeschlossen!"
echo "  ================================"
echo ""
echo "  NeuraDictate startet jetzt..."
open /Applications/NeuraDictate.app
echo ""
echo "  Du findest die App jetzt im Launchpad und in /Applications"
echo "  Das N-Icon erscheint oben rechts in der Menu Bar"
echo ""
sleep 2
exit 0
