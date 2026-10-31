#!/bin/sh
# Endfield Cloud — Firefox shell 环境体检（只读，不做任何改动）
# 检查: flatpak 存在性 / Firefox 版本 / devices=all 权限 / runtime profile 可写

FLATPAK_ID="org.mozilla.firefox"
RUNTIME_BASE="$HOME/.var/app/$FLATPAK_ID/endfield-cloud"
FAIL=0

echo "== Firefox shell 环境体检 =="

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

echo "== 结论 =="
[ "$FAIL" = 0 ] && echo "环境满足，可直接运行 scripts/launch-firefox.sh" || echo "存在缺项，按上面提示处理后重试"
exit "$FAIL"
