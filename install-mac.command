#!/bin/zsh
# NeuraDictate macOS Installer — robust, self-contained install.
# Finds a native Python 3.10+, installs dependencies, and creates
# a launcher .app in /Applications that runs under the correct architecture.

set -e
DIR="$(cd "$(dirname "$0")" && pwd -P)"
cd "$DIR"

echo ""
echo "  ================================"
echo "    NeuraDictate - Installation"
echo "  ================================"
echo ""

SYS_ARCH="$(uname -m)"
echo "  [+] System arch: $SYS_ARCH"

# ---- 1. Find a suitable Python 3.10+ that runs native to the system arch ----
# Priority: Homebrew (native), miniforge, python.org frameworks, system.
CANDIDATES=(
    /opt/homebrew/bin/python3.13
    /opt/homebrew/bin/python3.12
    /opt/homebrew/bin/python3.11
    /opt/homebrew/bin/python3.10
    /opt/homebrew/bin/python3
    /usr/local/bin/python3.13
    /usr/local/bin/python3.12
    /usr/local/bin/python3.11
    /usr/local/bin/python3.10
    /usr/local/bin/python3
    "$HOME/miniforge3/bin/python3"
    /Library/Frameworks/Python.framework/Versions/3.13/bin/python3
    /Library/Frameworks/Python.framework/Versions/3.12/bin/python3
    /Library/Frameworks/Python.framework/Versions/3.11/bin/python3
    /Library/Frameworks/Python.framework/Versions/3.10/bin/python3
    /usr/bin/python3
)

PY=""
for p in $CANDIDATES; do
    [ -x "$p" ] || continue
    # Must be Python 3.10+
    "$p" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >/dev/null 2>&1 || continue
    # Must run native to system arch (force arch to be sure)
    py_arch="$(arch -$SYS_ARCH "$p" -c "import platform; print(platform.machine())" 2>/dev/null || true)"
    if [ "$py_arch" = "$SYS_ARCH" ]; then
        PY="$p"
        break
    fi
done

# Fallback: try installing Python via Homebrew if available
if [ -z "$PY" ] && [ -x "/opt/homebrew/bin/brew" ]; then
    echo "  [!] No suitable Python 3.10+ found. Installing via Homebrew..."
    /opt/homebrew/bin/brew install python@3.12 || true
    if [ -x "/opt/homebrew/bin/python3.12" ]; then
        PY="/opt/homebrew/bin/python3.12"
    fi
fi

# If Python came from Homebrew, ensure Tk is installed (settings window needs tkinter)
if [ -n "$PY" ] && [[ "$PY" == /opt/homebrew/* || "$PY" == /usr/local/* ]]; then
    if ! "$PY" -c "import tkinter" >/dev/null 2>&1; then
        echo "  [!] Homebrew Python missing Tk. Installing python-tk..."
        PY_MINOR="$("$PY" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
        if [ -x "/opt/homebrew/bin/brew" ]; then
            /opt/homebrew/bin/brew install "python-tk@$PY_MINOR" 2>/dev/null || \
                /opt/homebrew/bin/brew install python-tk || true
        elif [ -x "/usr/local/bin/brew" ]; then
            /usr/local/bin/brew install "python-tk@$PY_MINOR" 2>/dev/null || \
                /usr/local/bin/brew install python-tk || true
        fi
    fi
fi

if [ -z "$PY" ]; then
    osascript -e 'display dialog "Python 3.10+ nicht gefunden.\n\nBitte installiere Python von python.org (empfohlen) oder via Homebrew:\n  brew install python\n\nStarte den Installer danach erneut." buttons {"OK"} default button 1 with icon caution with title "NeuraDictate"' 2>/dev/null
    open https://www.python.org/downloads/
    exit 1
fi

echo "  [+] Python: $PY"
"$PY" --version

# Ensure pip exists
"$PY" -m ensurepip --upgrade >/dev/null 2>&1 || true

# ---- 2. App directory ----
echo ""
echo "  [1/4] Installing app files..."
INSTALL_DIR="$HOME/Library/Application Support/NeuraDictate"
rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -R "$DIR/voice_input" "$INSTALL_DIR/"
cp "$DIR/start.py" "$INSTALL_DIR/"
cp "$DIR/icon.png" "$INSTALL_DIR/"
cp "$DIR/logo.png" "$INSTALL_DIR/" 2>/dev/null || true
echo "  [+] Files in $INSTALL_DIR"

# ---- 3. Clean up any stale arch-mismatched site-packages from prior runs ----
# Previous installer runs may have left wheels built for the wrong Python/arch.
setopt +o nomatch 2>/dev/null || true
for stale in "$HOME/Library/Python"/*/lib/python/site-packages/_cffi_backend*.so(N) \
             "$HOME/Library/Python"/*/lib/python/site-packages/_sounddevice*.so(N); do
    [ -f "$stale" ] && rm -f "$stale" 2>/dev/null || true
done

# ---- 4. Install dependencies (forcing native arch) ----
echo ""
echo "  [2/4] Installing dependencies (takes 1-2 min)..."
arch -$SYS_ARCH "$PY" -m pip install --quiet --upgrade pip >/dev/null 2>&1 || true
# Try --user first, fall back to --break-system-packages
arch -$SYS_ARCH "$PY" -m pip install --quiet --user --upgrade --force-reinstall \
    faster-whisper sounddevice numpy rumps cffi \
    pyobjc-framework-Quartz pyobjc-framework-Cocoa 2>/dev/null \
|| arch -$SYS_ARCH "$PY" -m pip install --quiet --break-system-packages --upgrade --force-reinstall \
    faster-whisper sounddevice numpy rumps cffi \
    pyobjc-framework-Quartz pyobjc-framework-Cocoa
echo "  [+] Dependencies installed"

# ---- 5. Download default model ----
echo ""
echo "  [3/4] Downloading Whisper model (466 MB, one-time)..."
arch -$SYS_ARCH "$PY" -c "import sys; sys.path.insert(0, '$INSTALL_DIR'); from voice_input.transcriber import download_model; download_model('small')" || {
    echo "  [!] Model download failed — will retry on first launch"
}
echo "  [+] Model ready"

# ---- 6. Create launcher .app in /Applications ----
echo ""
echo "  [4/4] Creating NeuraDictate.app in /Applications..."
APP="/Applications/NeuraDictate.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

# Icon
ICONSET=/tmp/nd.iconset
rm -rf "$ICONSET"
mkdir -p "$ICONSET"
for size in 16 32 64 128 256 512; do
    sips -z $size $size "$DIR/icon.png" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null 2>&1
    sips -z $((size*2)) $((size*2)) "$DIR/icon.png" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null 2>&1
done
iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/NeuraDictate.icns"
rm -rf "$ICONSET"

cat > "$APP/Contents/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>NeuraDictate</string>
    <key>CFBundleDisplayName</key><string>NeuraDictate</string>
    <key>CFBundleIdentifier</key><string>com.neura.dictate</string>
    <key>CFBundleVersion</key><string>1.1</string>
    <key>CFBundleShortVersionString</key><string>1.1</string>
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

# Launcher — forces native arch so Python never falls into Rosetta.
cat > "$APP/Contents/MacOS/NeuraDictate" << LAUNCHER
#!/bin/zsh
cd "$INSTALL_DIR"
export NEURADICTATE_HEADLESS=1
exec arch -$SYS_ARCH "$PY" start.py
LAUNCHER
chmod +x "$APP/Contents/MacOS/NeuraDictate"
xattr -dr com.apple.quarantine "$APP" 2>/dev/null || true

echo "  [+] /Applications/NeuraDictate.app created"

# ---- 7. Launch ----
echo ""
echo "  ================================"
echo "    Installation complete!"
echo "  ================================"
echo ""
echo "  App is in /Applications/NeuraDictate.app"
echo "  Launching now..."
echo ""
open "$APP"

osascript -e 'tell application "Terminal" to close front window' >/dev/null 2>&1 &
sleep 2
exit 0
