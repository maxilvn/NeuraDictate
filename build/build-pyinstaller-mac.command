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

# 6. Create DMG with drag-to-Applications UI
echo ""
echo "  [5/5] Creating DMG..."
DMG_STAGE=/tmp/NeuraDictate-dmg-stage
rm -rf "$DMG_STAGE"
mkdir -p "$DMG_STAGE"
cp -R "$DIR/dist/NeuraDictate.app" "$DMG_STAGE/"
ln -s /Applications "$DMG_STAGE/Applications"

rm -f "$DIR/NeuraDictate.dmg"
hdiutil create -volname "NeuraDictate" \
    -srcfolder "$DMG_STAGE" \
    -ov -format UDZO \
    "$DIR/NeuraDictate.dmg" >/dev/null
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
