#!/bin/sh
# 构建云·终末地外壳的 AppImage。
# 它不打包 Firefox：Flatpak org.mozilla.firefox 才是运行时。
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
VERSION="${ENDFIELD_VERSION:-1.0.13}"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/endfield-appimage"
TOOL="$CACHE/appimagetool-x86_64.AppImage"
BUILD="$ROOT/build/firefox-appimage"
APPDIR="$BUILD/EndfieldCloudFirefox.AppDir"
OUT="$ROOT/dist/endfield-cloud-firefox-$VERSION.AppImage"

mkdir -p "$CACHE" "$ROOT/dist"
if [ ! -x "$TOOL" ]; then
  echo "[build-firefox-appimage] 下载 appimagetool…"
  curl -fL --retry 2 --connect-timeout 15 \
    -o "$TOOL" \
    https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
  chmod 755 "$TOOL"
fi

rm -rf "$BUILD"
mkdir -p "$APPDIR/usr/share/endfield-firefox/profile"
cp -a "$ROOT/firefox/profile/." "$APPDIR/usr/share/endfield-firefox/profile/"
cp -a "$ROOT/scripts/launch-firefox.sh" "$APPDIR/usr/share/endfield-firefox/launch-firefox.sh"
cp -a "$ROOT/scripts/tab-guard.py" "$APPDIR/usr/share/endfield-firefox/tab-guard.py"
# 打包前清掉 Python 字节码缓存，别让 __pycache__ 混进 AppImage
find "$APPDIR" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
cp -a "$ROOT/firefox/appimage/AppRun" "$APPDIR/AppRun"
cp -a "$ROOT/firefox/appimage/endfield-cloud-firefox.desktop" "$APPDIR/endfield-cloud-firefox.desktop"
cp -a "$ROOT/resources/icons/512x512.png" "$APPDIR/endfield-cloud-firefox.png"
chmod 755 "$APPDIR/AppRun" \
          "$APPDIR/usr/share/endfield-firefox/launch-firefox.sh" \
          "$APPDIR/usr/share/endfield-firefox/tab-guard.py"

# appimagetool 本身也是 AppImage；extract-and-run 免掉 FUSE 依赖。
rm -f "$OUT"
ARCH=x86_64 "$TOOL" --appimage-extract-and-run "$APPDIR" "$OUT"
chmod 755 "$OUT"

echo
echo "[build-firefox-appimage] 产物: $OUT"
ls -lh "$OUT"
sha256sum "$OUT"
