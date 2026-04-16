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

# Find a REAL python3 (not Xcode stub, which has no pip and no tkinter)
# Priority: Homebrew > miniforge/conda > pyenv > python.org > /usr/bin (fallback)
PY=""
for p in /opt/homebrew/bin/python3 /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.11 \
         /usr/local/bin/python3 /usr/local/bin/python3.12 /usr/local/bin/python3.11 \
         "$HOME/miniforge3/bin/python3" "$HOME/miniconda3/bin/python3" "$HOME/anaconda3/bin/python3" \
         "$HOME/.pyenv/shims/python3" \
         /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 \
         /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
         /Library/Frameworks/Python.framework/Versions/3.11/bin/python3; do
    if [ -x "$p" ]; then
        # Verify it has pip (Xcode stub doesn't)
        if "$p" -m pip --version >/dev/null 2>&1; then
            PY="$p"
            break
        fi
    fi
done
# Last resort: check PATH (avoid Xcode stub)
if [ -z "$PY" ]; then
    PATH_PY="$(command -v python3 2>/dev/null || echo '')"
    if [ -n "$PATH_PY" ] && [[ "$PATH_PY" != *"Xcode"* ]] && "$PATH_PY" -m pip --version >/dev/null 2>&1; then
        PY="$PATH_PY"
    fi
fi
if [ -z "$PY" ]; then
    osascript -e 'display dialog "Python 3 mit pip wird benoetigt.\n\nInstalliere es von python.org oder via Homebrew:\nbrew install python" buttons {"OK"} default button 1 with icon caution with title "NeuraDictate"' 2>/dev/null
    exit 1
fi
echo "Using Python: $PY" >> "$LOG"

# First run: install deps
MARKER="$HOME/.cache/voice-input/.deps-installed"
if [ ! -f "$MARKER" ]; then
    osascript -e 'display notification "Installiere Dependencies... (dauert 1-2 Min)" with title "NeuraDictate"' &
    # Try --user first, fallback to --break-system-packages for managed envs
    "$PY" -m pip install --quiet --user faster-whisper sounddevice numpy rumps \
        pyobjc-framework-Quartz pyobjc-framework-Cocoa >> "$LOG" 2>&1 \
    || "$PY" -m pip install --quiet --break-system-packages faster-whisper sounddevice numpy rumps \
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
