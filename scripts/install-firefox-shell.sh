#!/bin/sh
# 云·终末地 · 环境体检（只读，不做任何改动）
# 检查: flatpak / Firefox 版本 / devices=all 权限 / runtime profile 可写 / python3 / Marionette 端口

FLATPAK_ID="org.mozilla.firefox"
RUNTIME_BASE="$HOME/.var/app/$FLATPAK_ID/endfield-cloud"
MARIONETTE_PORT="${ENDFIELD_MARIONETTE_PORT:-2828}"
FAIL=0

echo "== 云·终末地 · Firefox 外壳环境体检 =="

# 1. flatpak 命令
if command -v flatpak >/dev/null 2>&1; then
  echo "[OK] flatpak: $(flatpak --version 2>/dev/null)"
else
  echo "[MISS] flatpak 命令不存在"; FAIL=1
fi

# 2. native firefox（可选，有则优先）
if command -v firefox >/dev/null 2>&1; then
  echo "[OK] native firefox: $(command -v firefox)"
else
  echo "[INFO] 无 native firefox（将走 Flatpak）"
fi

# 3. Flatpak Firefox
if flatpak info "$FLATPAK_ID" >/dev/null 2>&1; then
  VER=$(flatpak info "$FLATPAK_ID" 2>/dev/null | grep -E "^版本|Version:" | head -1)
  echo "[OK] Flatpak $FLATPAK_ID $VER"
else
  echo "[MISS] Flatpak $FLATPAK_ID 未安装"; exit 1
fi

# 4. 手柄权限
if flatpak info --show-permissions "$FLATPAK_ID" 2>/dev/null | grep -q "^devices=all"; then
  echo "[OK] devices=all 已开启（手柄可用）"
else
  echo "[WARN] 缺 devices=all —— 手柄在游戏模式可能不可用"
  echo "       修复（手动执行，本脚本不会替你改）:"
  echo "       flatpak override --user --device=all $FLATPAK_ID"
fi

# 5. wayland/x11 socket
if [ -S "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/wayland-0" ]; then
  echo "[OK] 桌面 Wayland socket (wayland-0) 存在"
else
  echo "[INFO] 未发现 wayland-0（游戏模式下正常，会自动找 gamescope-*）"
fi

# 6. runtime profile 目录
if mkdir -p "$RUNTIME_BASE/profile" 2>/dev/null && [ -w "$RUNTIME_BASE" ]; then
  echo "[OK] runtime profile 目录可用: $RUNTIME_BASE/profile"
else
  echo "[MISS] 无法创建/写入 $RUNTIME_BASE"; FAIL=1
fi

# 7. python3（标签页守护需要）
if command -v python3 >/dev/null 2>&1; then
  echo "[OK] python3: $(command -v python3)（标签页守护可用）"
else
  echo "[WARN] 无 python3 —— 标签页守护不会启动；Ctrl+Tab / Ctrl+1 / Ctrl+W 仍可用"
  echo "       SteamOS 通常自带；没有就装一个，或接受没有「云游戏标签关不掉」这层保护"
fi

# 8. Marionette 端口
if command -v ss >/dev/null 2>&1; then
  if ss -ltn 2>/dev/null | grep -qE "[:.]$MARIONETTE_PORT[[:space:]]"; then
    echo "[WARN] 端口 $MARIONETTE_PORT 已被占用（geckodriver？）——启动器会跳过标签页守护"
  else
    echo "[OK] 端口 $MARIONETTE_PORT 空闲（标签页守护可用）"
  fi
fi

echo "== 结论 =="
if [ "$FAIL" = 0 ]; then
  echo "环境满足，可直接运行 scripts/launch-firefox.sh（或 Steam 里的 AppImage）"
else
  echo "存在缺项，按上面提示处理后重试"
fi
exit "$FAIL"
