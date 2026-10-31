#!/usr/bin/env python3
"""云·终末地 · 标签页守护（tab guard）

作用
----
1. 锁定云游戏标签页：Ctrl+W / Ctrl+F4 / 标签上的关闭按钮都关不掉它。
2. 切换标签页：Ctrl+Tab / Ctrl+Shift+Tab / Ctrl+1 由 Firefox 原生处理，
   本脚本不拦截；误触别的网页后按 Ctrl+1（或 Ctrl+Tab 循环）即可回到云游戏。
3. 自愈：万一云游戏标签页因其他路径消失（崩溃恢复、外部脚本等），自动重建并选中。
4. 清理：`--close-strays` 关掉除云游戏以外的所有标签并切回云游戏。

实现
----
通过 Firefox 内置的 Marionette 远程协议连到浏览器（默认 127.0.0.1:2828，
只监听本机回环），在 chrome 权限上下文里给 gBrowser.removeTab /
removeCurrentTab 打补丁，只拦截云游戏标签，其他标签照常关闭。

注意：这里的 "chrome" 是 Mozilla 的叫法（浏览器界面层：标签栏/工具栏/gBrowser），
与 Google Chrome 无关；网页所在的 content 上下文碰不到这些接口。

不依赖任何第三方 Python 包（SteamOS 自带 python3 即可）。

用法
----
    python3 tab-guard.py --watch              # 由启动器在后台拉起，持续守护
    python3 tab-guard.py --once               # 只做一次锁定/自愈
    python3 tab-guard.py --list               # 列出所有标签页（JSON）
    python3 tab-guard.py --close-strays       # 关掉除云游戏以外的标签并切回
    python3 tab-guard.py --focus-game         # 切到云游戏标签

环境变量
--------
    ENDFIELD_MARIONETTE_PORT   Marionette 端口，默认 2828
    ENDFIELD_GAME_HOST         额外认可的云游戏域名（逗号分隔）
    ENDFIELD_GAME_URL          云游戏入口 URL（自愈时用来重建标签）

退出码
------
    0  成功（或浏览器已退出、无需再守护）
    2  连不上 Marionette（Firefox 未带 --marionette 启动，或版本不支持）
    3  执行脚本失败
"""

import argparse
import json
import os
import socket
import sys
import time

DEFAULT_PORT = 2828
DEFAULT_HOSTS = ["endfield.hypergryph.com"]
DEFAULT_URL = "https://endfield.hypergryph.com/cloud"


DEFAULT_STATE_DIR = os.path.join(os.path.expanduser("~"), ".var", "app", "org.mozilla.firefox", "endfield-cloud")


def state_path(explicit=None):
    if explicit:
        return explicit
    env = os.environ.get("ENDFIELD_STATE_FILE", "").strip()
    if env:
        return env
    return os.path.join(DEFAULT_STATE_DIR, "tab-guard-state.json")


def command_path(explicit=None):
    return os.path.splitext(state_path(explicit))[0] + "-cmd.json"


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def write_json(path, payload):
    """原子替换：写临时文件再 rename，读的一方永远看不到半截 JSON。"""
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        temp = "%s.tmp-%d" % (path, os.getpid())
        with open(temp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
        os.replace(temp, path)
        return True
    except OSError:
        return False


def state_fresh(path, seconds):
    try:
        return (time.time() - os.path.getmtime(path)) <= seconds
    except OSError:
        return False


class MarionetteError(Exception):
    """Marionette 协议层错误。"""


class MarionetteClient:
    """极简 Marionette 客户端：只实现本脚本用到的三条命令。"""

    def __init__(self, host="127.0.0.1", port=DEFAULT_PORT, timeout=15.0, verbose=False):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.verbose = verbose
        self._sock = None
        self._buf = b""
        self._mid = 0
        self.protocol = 0

    # ---- 底层收发 ----------------------------------------------------
    def _fill(self, need):
        while len(self._buf) < need:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise MarionetteError("连接已断开")
            self._buf += chunk

    def _read_message(self):
        sep = self._buf.find(b":")
        while sep < 0:
            self._fill(len(self._buf) + 1)
            sep = self._buf.find(b":")
        head = self._buf[:sep]
        if not head.isdigit():
            raise MarionetteError("协议头异常: %r" % head[:32])
        length = int(head)
        self._fill(sep + 1 + length)
        payload = self._buf[sep + 1 : sep + 1 + length]
        self._buf = self._buf[sep + 1 + length :]
        return json.loads(payload.decode("utf-8", "replace"))

    def connect(self, wait_seconds=120.0):
        """连接并完成握手；浏览器还没起来时按 0.5s 重试。"""
        deadline = time.time() + wait_seconds
        last = None
        while time.time() < deadline:
            try:
                self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
            except OSError as exc:  # Firefox 尚未监听
                last = exc
                time.sleep(0.5)
                continue
            self._sock.settimeout(self.timeout)
            hello = self._read_message()
            self.protocol = int(hello.get("marionetteProtocol", 0))
            if self.protocol < 3:
                raise MarionetteError("Marionette 协议版本过低: %s" % self.protocol)
            if self.verbose:
                print("[tab-guard] 已连接 %s:%s protocol=%d" % (self.host, self.port, self.protocol))
            return
        raise MarionetteError("连接超时：%s:%s（%s）" % (self.host, self.port, last))

    def command(self, name, params=None):
        if self._sock is None:
            raise MarionetteError("未连接")
        self._mid += 1
        mid = self._mid
        payload = json.dumps([0, mid, name, params or {}]).encode("utf-8")
        self._sock.sendall(("%d:" % len(payload)).encode("ascii") + payload)
        while True:
            msg = self._read_message()
            if not isinstance(msg, list) or len(msg) < 3:
                continue
            if msg[1] != mid:
                continue  # 非本次请求的响应/事件，丢弃
            err = msg[2]
            result = msg[3] if len(msg) > 3 else None
            if err:
                raise MarionetteError("%s 失败: %s" % (name, err))
            return result

    def close(self):
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    # ---- 业务封装 ----------------------------------------------------
    def new_session(self, context="chrome"):
        self.command("WebDriver:NewSession", {"capabilities": {}})
        # 切到 chrome 上下文，才能拿到 gBrowser 等浏览器内部对象。
        # 命令名随版本变过：Firefox 138 之后是 Marionette:SetContext（并且要求启动参数
        # -remote-allow-system-access），更早的版本才叫 WebDriver:SetContext。两个都试。
        last = None
        for name in ("Marionette:SetContext", "WebDriver:SetContext"):
            try:
                self.command(name, {"value": context})
                return
            except MarionetteError as exc:
                last = exc
        if context == "chrome":
            raise last

    def execute(self, script):
        """在 chrome 上下文执行脚本，返回脚本的 JS 返回值。"""
        res = self.command(
            "WebDriver:ExecuteScript",
            {
                "script": script,
                "args": [],
                "scriptTimeout": 20000,
                "newSandbox": True,
                "sandbox": "system",
            },
        )
        if isinstance(res, dict) and "value" in res and len(res) == 1:
            res = res["value"]
        return res


JS_TEMPLATE = r"""const HOSTS = %(hosts)s;
const GAME_URL = %(url)s;
const MODE_ACTION = %(action)s;
const ONLY_LIST = MODE_ACTION === "list";

let win = null;
try {
  if (typeof Services !== "undefined" && Services.wm) {
    win = Services.wm.getMostRecentWindow("navigator:browser");
  }
} catch (e) {}
if (!win) {
  try { win = window; } catch (e) {}
}
if (!win || !win.gBrowser) {
  return { ok: false, err: "no-browser-window" };
}

const gB = win.gBrowser;

function tabHost(tab) {
  try {
    const b = tab.linkedBrowser;
    if (!b) return "";
    const uri = b.currentURI;
    return uri ? (uri.host || "") : "";
  } catch (e) {
    return "";
  }
}

function tabSpec(tab) {
  try {
    const b = tab.linkedBrowser;
    const uri = b && b.currentURI;
    return uri ? (uri.spec || "") : "";
  } catch (e) {
    return "";
  }
}

function isPending(tab) {
  try {
    return !!(tab.hasAttribute && tab.hasAttribute("pending"));
  } catch (e) {
    return false;
  }
}

function isGame(tab) {
  const h = tabHost(tab);
  if (!h) return false;
  for (const host of HOSTS) {
    if (h === host || h.endsWith("." + host)) return true;
  }
  return false;
}

function cloudTabs() {
  const out = [];
  for (const t of gB.tabs) {
    if (isGame(t)) out.push(t);
  }
  return out;
}

// 状态挂在 window 上：跨调用存活，浏览器关掉就自然没了。
//   blocked      被拦下的关闭次数
//   selfPinned   我们自己 pin 的那一页（用户取消钉住后就不再抢回）
//   respectUser  用户手动取消过钉住 ⇒ 本次会话不再自动 pin
//   patched      补丁是否已打
//   collapsed    折叠掉的重复云游戏标签数
const ST = (win.__endfieldTabGuard = win.__endfieldTabGuard || {
  blocked: 0,
  since: Date.now(),
  hosts: HOSTS,
  selfPinned: null,
  respectUser: false,
  patched: false,
});
if (!Array.isArray(ST.hosts) || ST.hosts.join(",") !== HOSTS.join(",")) ST.hosts = HOSTS;

// ---- 打补丁：云游戏标签关不掉（幂等）----
// 注意：Firefox 原生 pinned 页本来就拦 Ctrl+W，所以这个补丁主要兜「标签栏关闭按钮 /
// 中键 / 其它扩展调 removeTab」这些路径；blocked 计数不涨不代表补丁没生效。
if (!ONLY_LIST && !ST.patched) {
  const origRemoveTab = gB.removeTab.bind(gB);
  const origRemoveCurrentTab = gB.removeCurrentTab.bind(gB);
  ST.origRemoveTab = origRemoveTab;
  gB.removeTab = function (tab, opts) {
    try {
      if (tab && isGame(tab)) { ST.blocked += 1; return; }
    } catch (e) {}
    return origRemoveTab(tab, opts);
  };
  gB.removeCurrentTab = function (opts) {
    try {
      if (gB.selectedTab && isGame(gB.selectedTab)) { ST.blocked += 1; return; }
    } catch (e) {}
    return origRemoveCurrentTab(opts);
  };
  ST.patched = true;
}

// 关标签时绕过自己的补丁（折叠重复页 / 清场要靠它）
function hardRemove(tab) {
  try {
    (ST.origRemoveTab || gB.removeTab).call(gB, tab, { animate: false });
    return true;
  } catch (e) {
    return false;
  }
}

let clouds = cloudTabs();
let collapsed = 0;
let created = false;
let game = clouds.length ? clouds[clouds.length - 1] : null;

if (MODE_ACTION === "close-strays") {
  // 手动清场：留最新的云游戏标签，其余全关
  for (const t of Array.from(gB.tabs)) {
    if (t === game) continue;
    if (hardRemove(t)) collapsed += 1;
  }
  clouds = cloudTabs();
  game = clouds.length ? clouds[clouds.length - 1] : null;
}

if (!ONLY_LIST && MODE_ACTION !== "close-strays" && clouds.length >= 2) {
  // 页面点「开始游戏」时自己会新开一个同名 /cloud 页，旧的那个是登录页。
  // 只保留最新的一页，其余折叠掉 —— 用户在标签栏里就不会看到两个一样的网页。
  const keep = clouds[clouds.length - 1];
  for (const t of clouds) {
    if (t === keep) continue;
    if (hardRemove(t)) collapsed += 1;
  }
  game = keep;
}

// 用户手动取消过钉住：把「自己 pin 的」这个身份清掉，别再抢回去
if (ST.selfPinned) {
  const still = Array.from(gB.tabs).indexOf(ST.selfPinned) >= 0;
  if (!still) {
    ST.selfPinned = null;
  } else if (!ST.selfPinned.pinned) {
    ST.respectUser = true;
    ST.selfPinned = null;
  }
}

if (!game && !ONLY_LIST) {
  // 会话恢复是懒加载：pending 的标签 URL 还是 about:blank，看起来「没有云游戏页」。
  // 这种情况下新建标签就会多出一页，所以先等它加载完。
  const pending = Array.from(gB.tabs).some(isPending);
  if (!pending) {
    try {
      const p = Services.scriptSecurityManager.getSystemPrincipal();
      game = gB.addTab(GAME_URL, { triggeringPrincipal: p, index: 0 });
      created = true;
    } catch (e) {
      return { ok: false, err: "add-tab-failed", detail: String(e) };
    }
  }
}

if (game && MODE_ACTION !== "list") {
  if (!game.pinned && !ST.respectUser) {
    try { gB.pinTab(game); ST.selfPinned = game; } catch (e) {}
  }
  if (MODE_ACTION === "focus-game" || (created && MODE_ACTION !== "close-strays")) {
    try { gB.selectedTab = game; } catch (e) {}
  }
}

const tabs = Array.from(gB.tabs).map(function (t, i) {
  return {
    i: i,
    title: t.label || "",
    host: tabHost(t),
    url: tabSpec(t),
    pinned: !!t.pinned,
    active: t === gB.selectedTab,
    game: isGame(t),
    pending: isPending(t)
  };
});

return {
  ok: true,
  gameFound: !!game,
  created: created,
  collapsed: collapsed,
  blocked: ST.blocked,
  respectUser: !!ST.respectUser,
  count: tabs.length,
  activeIndex: gB.tabContainer.selectedIndex,
  tabs: tabs
};
"""


def build_script(hosts, url, action):
    return JS_TEMPLATE % {
        "hosts": json.dumps(hosts),
        "url": json.dumps(url),
        "action": json.dumps(action),
    }


def parse_status(result):
    if not isinstance(result, dict):
        raise MarionetteError("脚本返回值异常: %r" % (result,))
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description="云·终末地 标签页守护")
    ap.add_argument("--port", type=int, default=int(os.environ.get("ENDFIELD_MARIONETTE_PORT", DEFAULT_PORT)))
    ap.add_argument("--url", default=os.environ.get("ENDFIELD_GAME_URL", DEFAULT_URL))
    ap.add_argument("--host", action="append", default=None, help="云游戏域名，可重复")
    ap.add_argument("--watch", action="store_true", help="持续守护（启动器用）")
    ap.add_argument("--state-file", default=None,
                    help="守护把状态写到这个文件；--list 在守护运行时直接读它")
    ap.add_argument("--interval", type=float, default=3.0, help="守护轮询间隔秒，默认 3")
    ap.add_argument("--once", action="store_true", help="只执行一次")
    ap.add_argument("--list", action="store_true", help="列出标签页")
    ap.add_argument("--close-strays", action="store_true", help="关闭除云游戏外的标签")
    ap.add_argument("--focus-game", action="store_true", help="切到云游戏标签")
    ap.add_argument("--quiet", action="store_true", help="安静模式（仅错误输出）")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--wait", type=float, default=120.0, help="等待浏览器出现的秒数，默认 120")
    args = ap.parse_args(argv)

    hosts = list(DEFAULT_HOSTS)
    extra = os.environ.get("ENDFIELD_GAME_HOST", "")
    hosts += [h.strip() for h in extra.split(",") if h.strip()]
    if args.host:
        hosts = args.host + hosts

    if args.close_strays:
        action = "close-strays"
    elif args.focus_game:
        action = "focus-game"
    elif args.list:
        action = "list"
    elif args.watch:
        action = "watch"
    else:
        action = "once"

    script = build_script(hosts, args.url, "list" if action == "list" else action)

    def log(msg):
        if not args.quiet:
            print("[tab-guard] " + msg, flush=True)

    sfile = state_path(args.state_file)
    cfile = command_path(args.state_file)
    # 守护进程每轮都会刷新状态文件。它活着的时候绝对不能自己再 NewSession：
    # Firefox 只允许一个 Marionette 会话，抢过来会把正在守护的那条连接踢掉。
    guard_alive = action in ("list", "close-strays", "focus-game") and state_fresh(
        sfile, max(10.0, args.interval * 3)
    )
    if guard_alive:
        cached = read_json(sfile) or {}
        if action == "list":
            print(json.dumps(cached, ensure_ascii=False, indent=2))
            return 0
        seq = "%d-%d" % (int(time.time()), os.getpid())
        if not write_json(cfile, {"cmd": action, "id": seq, "ts": time.time()}):
            print("[tab-guard] 守护在运行，但写不进命令文件：%s" % cfile, file=sys.stderr)
            return 3
        deadline = time.time() + 8.0
        while time.time() < deadline:
            now = read_json(sfile) or {}
            done = now.get("lastCommand") or {}
            if done.get("id") == seq:
                print(json.dumps(done.get("result") or now, ensure_ascii=False, indent=2))
                return 0 if (done.get("result") or {}).get("ok") else 3
            time.sleep(0.25)
        print("[tab-guard] 守护没有在 8 秒内响应命令；它可能正忙着或已退出", file=sys.stderr)
        return 3

    client = MarionetteClient(port=args.port, verbose=args.verbose)
    try:
        client.connect(wait_seconds=args.wait)
        client.new_session("chrome")
    except MarionetteError as exc:
        print("[tab-guard] 无法接管浏览器：%s" % exc, file=sys.stderr, flush=True)
        return 2

    if action in ("list", "once", "close-strays", "focus-game"):
        try:
            status = parse_status(client.execute(script))
        except MarionetteError as exc:
            print("[tab-guard] 执行失败：%s" % exc, file=sys.stderr, flush=True)
            return 3
        finally:
            client.close()

        if not status.get("ok"):
            print("[tab-guard] 浏览器侧返回失败：%s" % json.dumps(status, ensure_ascii=False), file=sys.stderr, flush=True)
            return 3
        if action == "list" or args.verbose:
            print(json.dumps(status, ensure_ascii=False, indent=2))
        else:
            log(
                "标签 %d 个，云游戏标签%s，已拦截误关 %d 次"
                % (
                    status.get("count", 0),
                    "已锁定" if status.get("gameFound") else "缺失（已重建）",
                    status.get("blocked", 0),
                )
            )
        return 0

    # ---- 守护循环 ----
    last_state = None
    failures = 0
    handled_cmd = None
    last_cmd = None
    while True:
        # 外部命令（--close-strays / --focus-game）：命令行那边写命令文件，这里用现有
        # 会话执行，避免第二个 Marionette 连接把守护踢掉。
        pending_cmd = read_json(cfile) or {}
        cmd_id = pending_cmd.get("id")
        if cmd_id and cmd_id != handled_cmd:
            handled_cmd = cmd_id
            want = pending_cmd.get("cmd")
            if want in ("close-strays", "focus-game"):
                try:
                    result = parse_status(client.execute(build_script(hosts, args.url, want)))
                    last_cmd = {"id": cmd_id, "cmd": want, "result": result}
                    log(
                        "外部命令 %s 完成：标签 %d 个%s"
                        % (want, result.get("count", 0), "，已切回云游戏" if want == "focus-game" else "")
                    )
                except MarionetteError as exc:
                    last_cmd = {"id": cmd_id, "cmd": want, "result": {"ok": False, "err": str(exc)}}
                    log("外部命令 %s 失败：%s" % (want, exc))
        try:
            status = parse_status(client.execute(script))
        except MarionetteError as exc:
            failures += 1
            if failures >= 3:
                log("浏览器已退出或失联，守护结束：%s" % exc)
                client.close()
                return 0
            time.sleep(args.interval)
            continue
        failures = 0
        if not status.get("ok"):
            log("浏览器侧返回失败：%s" % json.dumps(status, ensure_ascii=False))
            time.sleep(args.interval)
            continue
        payload = dict(status)
        payload["ts"] = time.time()
        payload["pid"] = os.getpid()
        payload["interval"] = args.interval
        if last_cmd is not None:
            payload["lastCommand"] = last_cmd
        write_json(sfile, payload)
        state = (
            status.get("count"),
            status.get("gameFound"),
            status.get("created"),
            status.get("collapsed"),
            status.get("activeIndex"),
            status.get("blocked"),
            status.get("respectUser"),
        )
        if state != last_state:
            last_state = state
            log(
                "守护中：标签 %d 个，云游戏标签%s%s，当前第 %d 个，累计拦截误关 %d 次%s"
                % (
                    status.get("count", 0),
                    "在线" if status.get("gameFound") else "缺失→重建",
                    "，折叠重复页 %d 个" % status.get("collapsed") if status.get("collapsed") else "",
                    (status.get("activeIndex") or 0) + 1,
                    status.get("blocked", 0),
                    "，已尊重用户取消固定" if status.get("respectUser") else "",
                )
            )
        time.sleep(args.interval)

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
