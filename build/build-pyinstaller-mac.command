#!/bin/zsh
# Build a fully self-contained NeuraDictate.app using PyInstaller
# User needs ZERO dependencies — Python + all packages are bundled.

set -e
BUILD_DIR="$(cd "$(dirname "$0")" && pwd -P)"
DIR="$(cd "$BUILD_DIR/.." && pwd -P)"
cd "$DIR"

echo ""
echo "  ================================"
echo "    Build NeuraDictate.app"
echo "  ================================"
echo ""

# 1. Ensure we have Python with pip
PY="$(command -v python3)"
if [ -z "$PY" ]; then
    echo "  [X] Python3 nicht gefunden"
    exit 1
fi
echo "  [+] Using Python: $PY ($($PY --version))"

# 2. Install build dependencies (locally for this build session)
echo ""
echo "  [1/5] Installing build dependencies..."
"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install --quiet \
    pyinstaller \
    faster-whisper \
    sounddevice \
    numpy \
    rumps \
    pyobjc-framework-Quartz \
    pyobjc-framework-Cocoa
echo "  [+] Build deps ready"

# 3. Create .icns from icon.png
echo ""
echo "  [2/5] Creating icon.icns..."
ICONSET=/tmp/NeuraDictate.iconset
rm -rf "$ICONSET"
mkdir -p "$ICONSET"
for size in 16 32 64 128 256 512; do
    sips -z $size $size "$DIR/icon.png" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null 2>&1
    sips -z $((size*2)) $((size*2)) "$DIR/icon.png" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null 2>&1
done
iconutil -c icns "$ICONSET" -o "$DIR/icon.icns"
rm -rf "$ICONSET"
echo "  [+] icon.icns created"

# 4. Clean previous build
echo ""
echo "  [3/5] Cleaning previous build..."
rm -rf "$DIR/build_pyinstaller" "$DIR/dist"
echo "  [+] Clean"

# 5. Run PyInstaller
echo ""
echo "  [4/5] Running PyInstaller (this takes 1-3 minutes)..."
"$PY" -m PyInstaller "$DIR/NeuraDictate.spec" \
    --clean --noconfirm \
    --distpath "$DIR/dist" \
    --workpath "$DIR/build_pyinstaller" \
    2>&1 | tail -20

if [ ! -d "$DIR/dist/NeuraDictate.app" ]; then
    echo "  [X] Build failed — .app not created"
    exit 1
fi
echo "  [+] NeuraDictate.app built ($(du -sh "$DIR/dist/NeuraDictate.app" | cut -f1))"

# 6. Create DMG with professional drag-to-Applications layout
echo ""
echo "  [5/5] Creating styled DMG..."

# Ensure background exists
if [ ! -f "$BUILD_DIR/dmg-background.png" ]; then
    "$PY" "$BUILD_DIR/dmg-background.py"
fi

DMG_STAGE=/tmp/NeuraDictate-dmg-stage
rm -rf "$DMG_STAGE"
mkdir -p "$DMG_STAGE/.background"
cp "$BUILD_DIR/dmg-background.png" "$DMG_STAGE/.background/background.png"
cp -R "$DIR/dist/NeuraDictate.app" "$DMG_STAGE/"
ln -s /Applications "$DMG_STAGE/Applications"

# Create writable DMG
TMP_DMG=/tmp/NeuraDictate-tmp.dmg
rm -f "$TMP_DMG" "$DIR/NeuraDictate.dmg"
hdiutil create -volname "NeuraDictate" \
    -srcfolder "$DMG_STAGE" \
    -ov -format UDRW \
    "$TMP_DMG" >/dev/null

# Mount it
MOUNT_DIR="/Volumes/NeuraDictate"
hdiutil attach "$TMP_DMG" -readwrite -noautoopen >/dev/null

# Apply layout via AppleScript
osascript <<APPLESCRIPT
tell application "Finder"
    tell disk "NeuraDictate"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set the bounds of container window to {200, 120, 800, 500}
        set viewOptions to the icon view options of container window
        set arrangement of viewOptions to not arranged
        set icon size of viewOptions to 96
        set background picture of viewOptions to file ".background:background.png"
        set position of item "NeuraDictate.app" of container window to {150, 230}
        set position of item "Applications" of container window to {450, 230}
        update without registering applications
        delay 1
        close
    end tell
end tell
APPLESCRIPT

# Hide .background folder
chmod -Rf go-w "$MOUNT_DIR" 2>/dev/null || true
sync
hdiutil detach "$MOUNT_DIR" >/dev/null 2>&1

# Convert to compressed read-only
hdiutil convert "$TMP_DMG" -format UDZO -imagekey zlib-level=9 \
    -o "$DIR/NeuraDictate.dmg" >/dev/null
rm -f "$TMP_DMG"
rm -rf "$DMG_STAGE"

echo ""
echo "  ================================"
echo "    Build Complete"
echo "  ================================"
echo ""
echo "  NeuraDictate.app   → $DIR/dist/NeuraDictate.app ($(du -sh "$DIR/dist/NeuraDictate.app" | cut -f1))"
echo "  NeuraDictate.dmg   → $DIR/NeuraDictate.dmg ($(du -h "$DIR/NeuraDictate.dmg" | cut -f1))"
echo ""
echo "  User downloads DMG → drags app to /Applications → done."
echo "  No Python or dependencies required on user's machine."
echo ""
