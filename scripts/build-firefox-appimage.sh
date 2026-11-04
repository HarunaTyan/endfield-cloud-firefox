#!/bin/sh
# 构建云·终末地外壳的 AppImage。
# 它不打包 Firefox：Flatpak org.mozilla.firefox 才是运行时。
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
VERSION="${ENDFIELD_VERSION:-1.3.5}"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/endfield-appimage"
TOOL="$CACHE/appimagetool-x86_64.AppImage"
BUILD="$ROOT/build/firefox-appimage"
APPDIR="$BUILD/EndfieldCloudFirefox.AppDir"
# 文件名不带版本号：Steam 按「路径 + 名字」认游戏，带版本号的名字每升一级就变成
# 一个新游戏，手柄布局要重配。版本号只出现在压缩包名与 tag 上。
OUT="$ROOT/dist/EndfieldCloud.AppImage"

mkdir -p "$CACHE" "$ROOT/dist"
if [ ! -x "$TOOL" ]; then
  echo "[build-firefox-appimage] 下载 appimagetool 1.9.1…"
  # 固定 tag 与 SHA-256：不能用 continuous，那是滚动分支，内容随时变，
  # 且没有哈希校验就等于每次构建都在执行未知二进制。
  AIT_TAG="1.9.1"
  AIT_SHA256="ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0"
  curl -fL --retry 2 --connect-timeout 15 \
    -o "$TOOL.tmp" \
    "https://github.com/AppImage/appimagetool/releases/download/$AIT_TAG/appimagetool-x86_64.AppImage"
  GOT="$(sha256sum "$TOOL.tmp" | cut -d' ' -f1)"
  if [ "$GOT" != "$AIT_SHA256" ]; then
    rm -f "$TOOL.tmp"
    echo "[build-firefox-appimage] appimagetool 校验失败: $GOT" >&2
    exit 1
  fi
  mv "$TOOL.tmp" "$TOOL"
  chmod 755 "$TOOL"
elif [ "$(sha256sum "$TOOL" | cut -d' ' -f1)" != "ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0" ]; then
  echo "[build-firefox-appimage] 缓存里的 appimagetool 校验失败，重新下载" >&2
  rm -f "$TOOL"
  exec "$0" "$@"
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

# GitHub Release 的资产下载回来后是 644：可执行位不在 HTTP 里。
# 用 tar.gz 把 mode 一起带走，用户解压即得 755，不必再 chmod。
TARBALL="$ROOT/dist/EndfieldCloud-$VERSION.AppImage.tar.gz"
rm -f "$TARBALL"
tar -C "$ROOT/dist" -czf "$TARBALL" "$(basename "$OUT")"
chmod 644 "$TARBALL"

echo
echo "[build-firefox-appimage] 产物: $OUT"
ls -lh "$OUT" "$TARBALL"
sha256sum "$OUT" "$TARBALL"
