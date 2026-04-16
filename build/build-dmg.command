#!/bin/zsh
# Builds a DMG installer with drag-to-Applications UI

set -e
BUILD_SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
DIR="$(cd "$BUILD_SCRIPT_DIR/.." && pwd -P)"
cd "$DIR"

echo "Building NeuraDictate.dmg..."

# 1. Always build fresh app bundle (no caching)
echo "Building app bundle..."
if true; then
    BUILD=/tmp/NeuraDictate-build
    rm -rf "$BUILD"
    mkdir -p "$BUILD/NeuraDictate.app/Contents/MacOS"
    mkdir -p "$BUILD/NeuraDictate.app/Contents/Resources/app"

    cp -R "$DIR/voice_input" "$BUILD/NeuraDictate.app/Contents/Resources/app/"
    cp "$DIR/start.py" "$BUILD/NeuraDictate.app/Contents/Resources/app/"
    cp "$DIR/icon.png" "$BUILD/NeuraDictate.app/Contents/Resources/app/"
    cp "$DIR/logo.png" "$BUILD/NeuraDictate.app/Contents/Resources/app/"

    # Create ICNS
    ICONSET=/tmp/NeuraDictate.iconset
    rm -rf "$ICONSET"
    mkdir -p "$ICONSET"
    for size in 16 32 64 128 256 512; do
        sips -z $size $size "$DIR/icon.png" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null 2>&1
        sips -z $((size*2)) $((size*2)) "$DIR/icon.png" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null 2>&1
    done
    iconutil -c icns "$ICONSET" -o "$BUILD/NeuraDictate.app/Contents/Resources/NeuraDictate.icns"
    rm -rf "$ICONSET"

    # Info.plist
    cat > "$BUILD/NeuraDictate.app/Contents/Info.plist" << 'PLIST'
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

    # Launcher - first run installs deps, subsequent runs just launch
    cat > "$BUILD/NeuraDictate.app/Contents/MacOS/NeuraDictate" << 'LAUNCHER'
#!/bin/zsh
BUNDLE_DIR="$(cd "$(dirname "$0")/../Resources/app" && pwd -P)"
cd "$BUNDLE_DIR"

LOG="$HOME/.cache/voice-input/app-launch.log"
mkdir -p "$(dirname "$LOG")"

# Use isolated venv — no conflicts with system/Homebrew/miniforge
VENV="$HOME/.cache/voice-input/venv"
VENV_PY="$VENV/bin/python3"

# Find any Python3 to bootstrap the venv
BOOTSTRAP_PY=""
for p in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3 \
         "$HOME/miniforge3/bin/python3" "$HOME/.pyenv/shims/python3" \
         /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 \
         /Library/Frameworks/Python.framework/Versions/3.12/bin/python3; do
    if [ -x "$p" ] && "$p" -c "import venv" >/dev/null 2>&1; then
        BOOTSTRAP_PY="$p"
        break
    fi
done
if [ -z "$BOOTSTRAP_PY" ]; then
    BOOTSTRAP_PY="$(command -v python3 2>/dev/null || echo '')"
fi
if [ -z "$BOOTSTRAP_PY" ]; then
    osascript -e 'display dialog "Python 3 wird benoetigt.\n\nBitte von python.org installieren." buttons {"OK"} default button 1 with icon caution with title "NeuraDictate"' 2>/dev/null
    exit 1
fi

# Create venv on first run
if [ ! -x "$VENV_PY" ]; then
    osascript -e 'display notification "Erstelle Python Umgebung..." with title "NeuraDictate"' &
    "$BOOTSTRAP_PY" -m venv "$VENV" >> "$LOG" 2>&1 || {
        # venv module might not include pip — use --without-pip + ensurepip
        "$BOOTSTRAP_PY" -m venv --without-pip "$VENV" >> "$LOG" 2>&1
        "$VENV_PY" -m ensurepip >> "$LOG" 2>&1
    }
fi
PY="$VENV_PY"
echo "Using venv Python: $PY" >> "$LOG"

# First run: install deps
MARKER="$HOME/.cache/voice-input/.deps-installed"
if [ ! -f "$MARKER" ]; then
    osascript -e 'display notification "Installiere Dependencies... (dauert 1-2 Min)" with title "NeuraDictate"' &
    # venv has no PEP 668 issues, just install
    "$PY" -m pip install --quiet --upgrade pip >> "$LOG" 2>&1
    "$PY" -m pip install --quiet faster-whisper sounddevice numpy rumps \
        pyobjc-framework-Quartz pyobjc-framework-Cocoa >> "$LOG" 2>&1
    if [ $? -eq 0 ]; then
        touch "$MARKER"
        osascript -e 'display notification "Bereit!" with title "NeuraDictate"' &
    fi
fi

export NEURADICTATE_HEADLESS=1
exec "$PY" start.py >> "$LOG" 2>&1
LAUNCHER
    chmod +x "$BUILD/NeuraDictate.app/Contents/MacOS/NeuraDictate"
fi

# 2. Create DMG with drag-and-drop layout
DMG_TMP="/tmp/NeuraDictate-dmg-src"
rm -rf "$DMG_TMP"
mkdir -p "$DMG_TMP"

# Copy app bundle
cp -R "/tmp/NeuraDictate-build/NeuraDictate.app" "$DMG_TMP/"

# Create /Applications symlink for drag target
ln -s /Applications "$DMG_TMP/Applications"

# 3. Build the DMG
rm -f "$DIR/NeuraDictate.dmg"
hdiutil create -volname "NeuraDictate" \
    -srcfolder "$DMG_TMP" \
    -ov -format UDZO \
    "$DIR/NeuraDictate.dmg"

rm -rf "$DMG_TMP"

echo ""
echo "  [+] NeuraDictate.dmg erstellt"
echo "  Groesse: $(du -h "$DIR/NeuraDictate.dmg" | cut -f1)"
echo ""
