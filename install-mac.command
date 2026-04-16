#!/bin/zsh
# NeuraDictate macOS Installer - creates self-contained .app in /Applications

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
echo "  [1/5] Installiere Dependencies..."
python3 -m pip install --quiet --upgrade pip
python3 -m pip install --quiet faster-whisper sounddevice numpy rumps \
    pyobjc-framework-Quartz pyobjc-framework-Cocoa
echo "  [+] Dependencies installiert"

echo ""
echo "  [2/5] Lade Whisper Model herunter (ca. 466 MB)..."
python3 -c "import sys; sys.path.insert(0, '$DIR'); from voice_input.transcriber import download_model; download_model('small')"
echo "  [+] Model heruntergeladen"

echo ""
echo "  [3/5] Baue NeuraDictate.app..."
APP="/Applications/NeuraDictate.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"
mkdir -p "$APP/Contents/Resources/app"

# Copy all app files INTO the bundle (self-contained)
cp -R "$DIR/voice_input" "$APP/Contents/Resources/app/"
cp "$DIR/start.py" "$APP/Contents/Resources/app/"
cp "$DIR/icon.png" "$APP/Contents/Resources/app/"
cp "$DIR/logo.png" "$APP/Contents/Resources/app/"

# Create ICNS
ICONSET=/tmp/NeuraDictate.iconset
rm -rf "$ICONSET"
mkdir -p "$ICONSET"
for size in 16 32 64 128 256 512; do
    sips -z $size $size "$DIR/icon.png" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null 2>&1
    sips -z $((size*2)) $((size*2)) "$DIR/icon.png" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null 2>&1
done
iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/NeuraDictate.icns"
rm -rf "$ICONSET"

# Info.plist
cat > "$APP/Contents/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>NeuraDictate</string>
    <key>CFBundleDisplayName</key><string>NeuraDictate</string>
    <key>CFBundleIdentifier</key><string>com.neura.dictate</string>
    <key>CFBundleVersion</key><string>1.0</string>
    <key>CFBundleShortVersionString</key><string>1.0</string>
    <key>CFBundleExecutable</key><string>NeuraDictate</string>
    <key>CFBundleIconFile</key><string>NeuraDictate.icns</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>LSMinimumSystemVersion</key><string>10.13</string>
    <key>LSUIElement</key><true/>
    <key>NSHighResolutionCapable</key><true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>NeuraDictate needs microphone access to transcribe your speech.</string>
</dict>
</plist>
PLIST

# Get absolute path to the Python that has our dependencies installed
PYTHON_PATH="$(command -v python3)"
echo "  [+] Python Pfad: $PYTHON_PATH"

# Launcher - uses the exact Python that was used during install
cat > "$APP/Contents/MacOS/NeuraDictate" << LAUNCHER
#!/bin/zsh
BUNDLE_DIR="\$(cd "\$(dirname "\$0")/../Resources/app" && pwd -P)"
cd "\$BUNDLE_DIR"
export NEURADICTATE_HEADLESS=1
# Log any startup errors so user can diagnose
exec "$PYTHON_PATH" start.py >> "\$HOME/.cache/voice-input/app-launch.log" 2>&1
LAUNCHER
chmod +x "$APP/Contents/MacOS/NeuraDictate"

# Ensure log dir exists
mkdir -p "$HOME/.cache/voice-input"

echo "  [+] NeuraDictate.app in /Applications installiert"

echo ""
echo "  [4/5] Autostart einrichten..."
PLIST_PATH="$HOME/Library/LaunchAgents/com.neura.dictate.plist"
cat > "$PLIST_PATH" << 'PLISTEOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.neura.dictate</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/NeuraDictate.app/Contents/MacOS/NeuraDictate</string>
    </array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><false/>
</dict>
</plist>
PLISTEOF
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"
echo "  [+] Startet automatisch bei Login"

echo ""
echo "  [5/5] Starte NeuraDictate..."
open /Applications/NeuraDictate.app

echo ""
echo "  ================================"
echo "    Installation abgeschlossen!"
echo "  ================================"
echo ""
echo "  Die App liegt jetzt self-contained in /Applications"
echo "  Du kannst diesen Download-Ordner jetzt loeschen."
echo ""
echo "  Zu finden in:"
echo "    - /Applications/NeuraDictate.app"
echo "    - Launchpad"
echo "    - Menu Bar (N-Icon oben rechts)"
echo ""
sleep 2
exit 0
