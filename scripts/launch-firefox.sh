#!/bin/sh
# 云·终末地 · Firefox/Gecko 外壳启动器（Flatpak 或 native Firefox）
#
# 用途: 作为 Steam「非 Steam 游戏」快捷方式的 Target（游戏模式 gamescope 可用），
#       也可在桌面模式直接运行。
#
# 用法:
#   launch-firefox.sh [--url=URL] [--window-size=WxH] [--fullscreen] [--windowed]
#                     [--window-mode=auto|fullscreen|windowed]
#   环境变量:
#     DRY_RUN=1                 只打印最终命令，不执行
#     ENDFIELD_FIREFOX_BACKEND=wayland|x11   强制指定渲染后端
#     ENDFIELD_TAB_GUARD=0      关闭标签页守护（同时不给 Firefox 加 --marionette）
#     ENDFIELD_MARIONETTE_PORT  守护连接的端口，默认 2828
#     ENDFIELD_LOG=1            写日志（默认: 游戏模式(gamescope)下自动写，桌面模式不打）
#
# 日志: 固定路径 $HOME/.var/app/org.mozilla.firefox/endfield-cloud/launch-firefox.log
#       (放在 Flatpak 可见的目录；gamescope 下无终端，靠它排查)

set -u

# ---------- 固定路径 ----------
# AppImage 版会把 profile 放进只读挂载里，用这两个环境变量指向包内副本，
# 并强制同步到可写的运行时目录；仓库直接运行时保持原行为。
REPO_PROFILE_DIR="${ENDFIELD_FIREFOX_PROFILE_DIR:-$(cd "$(dirname "$0")/../firefox/profile" && pwd)}"
FLATPAK_ID="org.mozilla.firefox"
RUNTIME_BASE="$HOME/.var/app/$FLATPAK_ID/endfield-cloud"
RUNTIME_PROFILE="${ENDFIELD_FIREFOX_RUNTIME_PROFILE:-$RUNTIME_BASE/profile}"
FORCE_PROFILE_SYNC="${ENDFIELD_FIREFOX_FORCE_PROFILE_SYNC:-0}"
LOG_FILE="$RUNTIME_BASE/launch-firefox.log"
DEFAULT_URL="https://endfield.hypergryph.com/cloud"
EXIT_OK=0; EXIT_NO_FIREFOX=2; EXIT_PROFILE=3; EXIT_RUNNING=4

mkdir -p "$RUNTIME_BASE" 2>/dev/null || true
log() { [ "${ENDFIELD_LOG:-}" = "1" ] || [ -n "${IN_GAMESCOPE:-}" ] || return 0; echo "$@" >> "$LOG_FILE" 2>/dev/null; }
die() { code=$1; shift; echo "[launch-firefox] $*" >&2; log "FATAL($code): $*"; exit "$code"; }

# ---------- 参数解析 ----------
URL="$DEFAULT_URL"; WIDTH=1280; HEIGHT=800; WINDOW_MODE="auto"
for arg in "$@"; do
  case "$arg" in
    --url=*)           URL="${arg#--url=}" ;;
    --window-size=*)   WxH="${arg#--window-size=}"; WIDTH="${WxH%%x*}"; HEIGHT="${WxH##*x}" ;;
    --fullscreen)      WINDOW_MODE="fullscreen" ;;
    --windowed)        WINDOW_MODE="windowed" ;;
    --window-mode=*)   WINDOW_MODE="${arg#--window-mode=}" ;;
    *) echo "[launch-firefox] 忽略未知参数: $arg" >&2 ;;
  esac
done
case "$WINDOW_MODE" in auto|fullscreen|windowed) ;; *) die "$EXIT_PROFILE" "无效 --window-mode: $WINDOW_MODE";; esac

# ---------- Steam 游戏模式环境兜底（必须在 auto 判定之前）----------
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
# 会话继承的 XAUTHORITY 可能是已消失的旧 cookie(Steam 启动器常见)。
# 只在使用 X11 后端时才有意义，但先在这里纠正，日志里能看出用的是哪个文件。
if [ -n "${XAUTHORITY:-}" ] && [ ! -r "$XAUTHORITY" ]; then
  for candidate in "$XDG_RUNTIME_DIR"/xauth_*; do
    [ -r "$candidate" ] || continue
    export XAUTHORITY="$candidate"
    break
  done
fi
if [ -z "${WAYLAND_DISPLAY:-}" ]; then
  # gamescope socket 优先(游戏模式),其次 wayland(桌面),兜底 wayland-0
  for sock in "$XDG_RUNTIME_DIR"/gamescope-* "$XDG_RUNTIME_DIR"/wayland-*; do
    [ -S "$sock" ] || continue
    c="$(basename "$sock")"; case "$c" in *.lock|*-ei) continue;; esac
    export WAYLAND_DISPLAY="$c"; break
  done
  export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
fi
if [ -n "${GAMESCOPE_WAYLAND_DISPLAY:-}" ]; then IN_GAMESCOPE=1; fi
case "$WAYLAND_DISPLAY" in gamescope-*) IN_GAMESCOPE=1;; esac

# auto: gamescope=全屏 kiosk；桌面 KWin=窗口化 1280x800（方便调试，不锁屏）
if [ "$WINDOW_MODE" = "auto" ]; then
  if [ -n "${IN_GAMESCOPE:-}" ]; then WINDOW_MODE="fullscreen"; else WINDOW_MODE="windowed"; fi
fi

# ---------- Firefox 探测: native 或 flatpak ----------
FIREFOX_KIND=""; FIREFOX_BIN=""
if command -v firefox >/dev/null 2>&1; then
  FIREFOX_KIND="native"; FIREFOX_BIN="firefox"
elif command -v flatpak >/dev/null 2>&1 && flatpak info "$FLATPAK_ID" >/dev/null 2>&1; then
  FIREFOX_KIND="flatpak"
else
  die "$EXIT_NO_FIREFOX" "找不到 native firefox 或 Flatpak $FLATPAK_ID"
fi

# ---------- 手柄权限检查(只提示,不自动改) ----------
if [ "$FIREFOX_KIND" = "flatpak" ]; then
  if ! flatpak info --show-permissions "$FLATPAK_ID" 2>/dev/null | grep -q "^devices=all"; then
    echo "[launch-firefox] 警告: $FLATPAK_ID 缺少 devices=all 权限,游戏模式手柄可能不可用。" >&2
    echo "[launch-firefox] 如需开启,请在桌面模式执行:" >&2
    echo "    flatpak override --user --device=all $FLATPAK_ID" >&2
    log "WARN: flatpak missing devices=all (gamepad may fail)"
  fi
fi

# ---------- profile 同步到 Flatpak 可见目录 ----------
# native firefox 直接用 repo 里的 profile(只读复制到临时亦可);
# flatpak 不挂 $HOME,必须放 ~/.var/app/org.mozilla.firefox/ 下。
sync_profile() {
  if [ ! -f "$REPO_PROFILE_DIR/user.js" ]; then die "$EXIT_PROFILE" "repo profile 缺失: $REPO_PROFILE_DIR/user.js"; fi
  mkdir -p "$RUNTIME_PROFILE/chrome" || die "$EXIT_PROFILE" "无法创建 $RUNTIME_PROFILE"
  # 只覆盖 user.js 与 chrome/;prefs.js(运行时状态)与 cookies.sqlite 等永不触碰
  cp "$REPO_PROFILE_DIR/user.js" "$RUNTIME_PROFILE/user.js" || die "$EXIT_PROFILE" "复制 user.js 失败"
  # chrome/ 内容按文件覆盖(删除 repo 已移除的旧文件不在本脚本职责内,文件集很小)
  for f in "$REPO_PROFILE_DIR"/chrome/*; do
    [ -f "$f" ] || continue
    cp "$f" "$RUNTIME_PROFILE/chrome/" || die "$EXIT_PROFILE" "复制 chrome/$(basename "$f") 失败"
  done
}
if [ "$FIREFOX_KIND" = "flatpak" ] || [ "$FORCE_PROFILE_SYNC" = "1" ]; then
  sync_profile
else
  RUNTIME_PROFILE="$REPO_PROFILE_DIR"
fi

# ---------- 单实例 ----------
# Firefox 自身 --new-instance 会绕过单实例;因此先查锁。游戏模式下重复点击
# 快捷方式是常见操作。检查 pgrep + profile 目录锁文件。
LOCK_CANDIDATES=$(pgrep -f "$FLATPAK_ID.*endfield-cloud/profile" 2>/dev/null || true)
if [ -z "$LOCK_CANDIDATES" ] && command -v pgrep >/dev/null 2>&1; then
  LOCK_CANDIDATES=$(pgrep -f "firefox.*$RUNTIME_PROFILE" 2>/dev/null || true)
fi
if [ -n "$LOCK_CANDIDATES" ]; then
  echo "[launch-firefox] 已有实例在运行 (pid: $(echo $LOCK_CANDIDATES | tr '\n' ' '));不再启动新实例。" >&2
  echo "[launch-firefox] 游戏模式下请先退出当前窗口(手柄: 菜单/快捷键),桌面模式可点击其窗口 focus。" >&2
  log "single-instance: already running, exit $EXIT_RUNNING"
  exit "$EXIT_RUNNING"
fi

# ---------- Wayland / X11 后端选择 ----------
# 桌面 KWin: MOZ_ENABLE_WAYLAND=1(原生 Wayland,输入/分数缩放更好)
# Gamescope(项目实测只显示 X11 窗口): 默认 XWayland
BACKEND="${ENDFIELD_FIREFOX_BACKEND:-}"
if [ -z "$BACKEND" ]; then
  if [ -n "${IN_GAMESCOPE:-}" ] || [ -n "${GAMESCOPE_WAYLAND_DISPLAY:-}" ] \
     || [ "${WAYLAND_DISPLAY#gamescope-}" != "$WAYLAND_DISPLAY" ]; then
    BACKEND="x11"
  else
    BACKEND="wayland"
  fi
fi
case "$BACKEND" in wayland|x11) ;; *) BACKEND="wayland";; esac

# XWayland 后端需要 DISPLAY；游戏模式下 Steam 一般已注入 :0，缺了兜底。
if [ "$BACKEND" = "x11" ]; then export DISPLAY="${DISPLAY:-:0}"; fi

# ---------- 标签页守护（锁定云游戏标签页；详见 docs/tabs-and-gamepad.md）----------
# 只有守护真的能跑，才给 Firefox 加 --marionette；关掉守护就不开端口。
GUARD_ENABLED="${ENDFIELD_TAB_GUARD:-1}"
MARIONETTE_PORT="${ENDFIELD_MARIONETTE_PORT:-2828}"
GUARD_SCRIPT="${ENDFIELD_GUARD_SCRIPT:-$(cd "$(dirname "$0")" && pwd)/tab-guard.py}"
GUARD_ACTIVE=0

port_busy() {
  if command -v ss >/dev/null 2>&1; then
    ss -ltn 2>/dev/null | grep -qE "[:.]$1[[:space:]]"
  elif command -v netstat >/dev/null 2>&1; then
    netstat -ltn 2>/dev/null | grep -qE "[:.]$1[[:space:]]"
  else
    return 1
  fi
}

start_tab_guard() {
  [ "$GUARD_ENABLED" = "1" ] || { log "tab-guard: disabled (ENDFIELD_TAB_GUARD=0)"; return 0; }
  if [ ! -f "$GUARD_SCRIPT" ]; then
    echo "[launch-firefox] 未找到 $GUARD_SCRIPT，跳过标签页守护（Ctrl+Tab / Ctrl+1 仍可用）。" >&2
    log "WARN: tab-guard script missing: $GUARD_SCRIPT"
    return 0
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "[launch-firefox] 未找到 python3，跳过标签页守护（Ctrl+Tab / Ctrl+1 仍可用）。" >&2
    log "WARN: python3 missing, tab guard skipped"
    return 0
  fi
  if port_busy "$MARIONETTE_PORT"; then
    echo "[launch-firefox] 端口 $MARIONETTE_PORT 已被占用，跳过标签页守护（可能是 geckodriver）。" >&2
    log "WARN: port $MARIONETTE_PORT busy, tab guard skipped"
    return 0
  fi
  # 后台守护：与 Firefox 的连接断开（浏览器退出）后自行结束。
  python3 "$GUARD_SCRIPT" --watch --port "$MARIONETTE_PORT" --url "$URL" >>"$LOG_FILE" 2>&1 &
  GUARD_ACTIVE=1
  log "tab-guard: started (pid $!, port $MARIONETTE_PORT)"
  return 0
}

[ "${DRY_RUN:-0}" = "1" ] || start_tab_guard

# ---------- 组装命令 ----------
# 注意顺序：--marionette 必须在 --profile 之前，否则会被 --profile 当成参数值吃掉。
FF_ARGS="--no-remote --new-instance"
[ "$GUARD_ACTIVE" = "1" ] && FF_ARGS="$FF_ARGS --marionette"
FF_ARGS="$FF_ARGS --profile"
case "$FIREFOX_KIND" in
  flatpak)
    CMD_PREFIX="flatpak run"
    if [ "$BACKEND" = "x11" ]; then
      # Flatpak 默认只转发 Wayland socket，不把 DISPLAY 传给沙箱；必须显式 --env。
      # --socket=x11 是让 Flatpak 真正挂载 X11 并注入 DISPLAY 的关键，
      # 只写 --env=DISPLAY 会被 Flatpak 的 Wayland 默认路径吃掉。
      ENV_ARGS="--socket=x11 --env=MOZ_ENABLE_WAYLAND=0 --env=DISPLAY=${DISPLAY:-:0}"
      [ -n "${XAUTHORITY:-}" ] && ENV_ARGS="$ENV_ARGS --env=XAUTHORITY=$XAUTHORITY"
    else
      ENV_ARGS="--env=MOZ_ENABLE_WAYLAND=1"
    fi
    ;;
  native)
    CMD_PREFIX=""; ENV_ARGS=""
    if [ "$BACKEND" = "x11" ]; then export MOZ_ENABLE_WAYLAND=0; export DISPLAY="${DISPLAY:-:0}"; else export MOZ_ENABLE_WAYLAND=1; fi
    ;;
esac

if [ "$WINDOW_MODE" = "fullscreen" ]; then
  MODE_ARGS="--kiosk"
else
  # Firefox 传统 CLI 用的开关是 -width/-height(单横线);--width 在 158 被接受但会告警
  MODE_ARGS="-width $WIDTH -height $HEIGHT"
fi

RUN_URL="$URL"
[ -n "$RUN_URL" ] && [ "${RUN_URL#http}" = "$RUN_URL" ] && [ "${RUN_URL#--}" = "$RUN_URL" ] && RUN_URL="https://$RUN_URL"

# ---------- 打印 & 执行 ----------
if [ "$FIREFOX_KIND" = "flatpak" ]; then
  FINAL_CMD="$CMD_PREFIX $ENV_ARGS $FLATPAK_ID $FF_ARGS \"$RUNTIME_PROFILE\" $MODE_ARGS \"$RUN_URL\""
else
  FINAL_CMD="${FIREFOX_BIN} $FF_ARGS \"$RUNTIME_PROFILE\" $MODE_ARGS \"$RUN_URL\""
fi
echo "[launch-firefox] backend=$BACKEND mode=$WINDOW_MODE kind=$FIREFOX_KIND guard=$GUARD_ACTIVE"
echo "[launch-firefox] profile=$RUNTIME_PROFILE"
echo "[launch-firefox] exec: $FINAL_CMD"
log "exec: $FINAL_CMD"
[ "${DRY_RUN:-0}" = "1" ] && exit "$EXIT_OK"

# exec: 让 Firefox 成为 Steam 快捷方式的直接子进程(退出码直接回传给 Steam)
if [ "$FIREFOX_KIND" = "flatpak" ]; then
  # shellcheck disable=SC2086
  exec flatpak run $ENV_ARGS "$FLATPAK_ID" $FF_ARGS "$RUNTIME_PROFILE" $MODE_ARGS "$RUN_URL"
else
  # shellcheck disable=SC2086
  exec "$FIREFOX_BIN" $FF_ARGS "$RUNTIME_PROFILE" $MODE_ARGS "$RUN_URL"
fi
