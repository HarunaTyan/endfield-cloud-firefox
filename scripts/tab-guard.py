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
        directory = os.path.dirname(path) or "."
        os.makedirs(directory, mode=0o700, exist_ok=True)
        temp = "%s.tmp-%d" % (path, os.getpid())
        # 文件里有全部标签的 URL 与标题，等同浏览历史；只留属主可读
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
        os.replace(temp, path)
        return True
    except OSError:
        return False


def format_status(status):
    """标签状态的一行摘要。

    占位符与参数必须一一对应：这里曾经少一个 %s，导致守护第一轮就抛
    TypeError（not all arguments converted）并退出，标签锁定静默失效。
    tests/status-log.py 会把这个对应关系钉住。
    """
    return "守护中：标签 %d 个，云游戏标签%s%s，当前第 %d 个，累计拦截误关 %d 次%s%s" % (
        status.get("count", 0),
        "在线" if status.get("gameFound") else "缺失→重建",
        "，折叠重复页 %d 个" % status.get("collapsed") if status.get("collapsed") else "",
        (status.get("activeIndex") or 0) + 1,
        status.get("blocked", 0),
        "，已尊重用户取消固定" if status.get("respectUser") else "",
        "，注意：存在同名云游戏页，未自动固定" if status.get("ambiguous") else "",
    )


def pid_alive(pid):
    """只看进程在不在；权限不足也当作活着（那是别人的进程，不该抢会话）。"""
    try:
        os.kill(int(pid), 0)
        return True
    except PermissionError:
        return True
    except (OSError, ValueError, TypeError):
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

    def __init__(self, host="127.0.0.1", port=DEFAULT_PORT, timeout=30.0, verbose=False):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.verbose = verbose
        self._sock = None
        self._buf = b""
        self._mid = 0
        self.protocol = 0

    # ---- 底层收发 ----------------------------------------------------
    MAX_MESSAGE = 16 * 1024 * 1024

    def _fill(self, need):
        while len(self._buf) < need:
            try:
                chunk = self._sock.recv(65536)
            except socket.timeout:
                raise MarionetteError("读取超时（%.0fs）" % self.timeout)
            except OSError as exc:
                raise MarionetteError("连接中断: %s" % exc)
            if not chunk:
                raise MarionetteError("连接已断开")
            self._buf += chunk
            if len(self._buf) > self.MAX_MESSAGE:
                raise MarionetteError("对端发送的消息超过 16MB，断开")

    def _read_message(self):
        sep = self._buf.find(b":")
        while sep < 0:
            self._fill(len(self._buf) + 1)
            sep = self._buf.find(b":")
        head = self._buf[:sep]
        # 长度头只可能是十进制数字；超过 10 位（>9GB）直接判非法，避免 int() 抛 ValueError
        if len(head) > 10 or not head.isdigit():
            raise MarionetteError("协议头异常: %r" % head[:32])
        length = int(head)
        if length > self.MAX_MESSAGE:
            raise MarionetteError("协议头声明 %d 字节，超过 16MB 上限" % length)
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
            # 走到这里说明 system-access 没生效：不同版本叫 -remote-allow-system-access /
            # --remote-enable-system-access，新版改看 MOZ_REMOTE_ALLOW_SYSTEM_ACCESS。
            raise MarionetteError(
                "无法切到 chrome 上下文（%s）。Firefox 需要以 system-access 启动："
                "-remote-allow-system-access 或环境变量 MOZ_REMOTE_ALLOW_SYSTEM_ACCESS=1"
                % last
            )

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
const BLOCKED_KEYS = %(blocked_keys)s;
const GAME_URL = %(url)s;
const MODE_ACTION = %(action)s;
const COLLAPSE = %(collapse)s;
const DEDUPE = %(dedupe)s;
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
  protectedTab: null,
  respectUser: false,
  patched: false,
});
if (!Array.isArray(ST.hosts) || ST.hosts.join(",") !== HOSTS.join(",")) ST.hosts = HOSTS;

// ---- 键盘：屏蔽一批「能把这台机器搞坏」的浏览器快捷键（幂等）----
// 装在 chrome 窗口的捕获阶段：浏览器自己的快捷键命令（建窗口、开附加组件、开开发者工具）
// 都走这里，先一步 preventDefault 就轮不到它们。
// 被拦：Ctrl+N、Ctrl+Shift+P/A/I/K/C/O、Ctrl+U/J/P/S/O、F12。
// 要放行就设 ENDFIELD_KEY_BLOCK=0（此时整段不装）。
if (!ONLY_LIST && !ST.keyFilter && BLOCKED_KEYS.length) {
  ST.keyFilter = function (ev) {
    try {
      if (ev.defaultPrevented || ev.isComposing) return;
      const key = String(ev.key || "").toLowerCase();
      for (const spec of BLOCKED_KEYS) {
        if (key !== spec.key) continue;
        if (!!ev.ctrlKey !== !!spec.ctrl) continue;
        if (!!ev.shiftKey !== !!spec.shift) continue;
        if (!!ev.altKey !== !!spec.alt) continue;
        if (!!ev.metaKey !== !!spec.meta) continue;
        ev.preventDefault();
        ev.stopPropagation();
        ST.blockedKeys = (ST.blockedKeys || 0) + 1;
        return;
      }
    } catch (e) {}
  };
  win.addEventListener("keydown", ST.keyFilter, true);
}

// ---- 打补丁：云游戏标签关不掉（幂等）----
// 注意：Firefox 原生 pinned 页本来就拦 Ctrl+W，所以这个补丁主要兜「标签栏关闭按钮 /
// 中键 / 其它扩展调 removeTab」这些路径；blocked 计数不涨不代表补丁没生效。
if (!ONLY_LIST && !ST.patched) {
  const origRemoveTab = gB.removeTab.bind(gB);
  const origRemoveCurrentTab = gB.removeCurrentTab.bind(gB);
  ST.origRemoveTab = origRemoveTab;
  // 只拦「当前这一页」的关闭请求。旧实现按 URL 拦，导致同名的登录页与游戏页
  // 全都关不掉；现在只保护 ST.protectedTab 这一个 tab 对象。
  gB.removeTab = function (tab, opts) {
    try {
      if (tab && tab === ST.protectedTab) { ST.blocked += 1; return; }
    } catch (e) {}
    return origRemoveTab(tab, opts);
  };
  gB.removeCurrentTab = function (opts) {
    try {
      if (gB.selectedTab && gB.selectedTab === ST.protectedTab) { ST.blocked += 1; return; }
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
let deduped = 0;
let dedupeReason = "";
let created = false;
let game = clouds.length ? clouds[clouds.length - 1] : null;
// 首轮快照：进来时就多于一个 /cloud 页（多半是上次会话恢复 + 本次主页各一页）
const ambiguous = clouds.length > 1;

if (MODE_ACTION === "close-strays") {
  // 手动清场：留最新的云游戏标签，其余全关
  for (const t of Array.from(gB.tabs)) {
    if (t === game) continue;
    if (hardRemove(t)) collapsed += 1;
  }
  clouds = cloudTabs();
  game = clouds.length ? clouds[clouds.length - 1] : null;
}

// 重复的 /cloud 页只留一页。登录页与游戏页同 URL 同标题，凭 URL 分不出谁是谁，
// 只能按时序判断：最新打开的那一页才是这次要玩的（绕过本文件的关闭拦截）。
// 这一条同时修「第二次启动 = 固定页 + 新页」与「两页都关不掉」。
// 判断这一页是不是真在出画面：游戏页里会有一个正在解码的 <video>，登录页没有。
// 读不到 contentDocument（跨进程、页面还没加载）时按「没有视频」处理，不影响兜底。
function hasLiveVideo(tab) {
  try {
    const b = tab && tab.linkedBrowser;
    const doc = b && (b.contentDocument || (b.contentWindow && b.contentWindow.document));
    if (!doc || !doc.querySelectorAll) return false;
    for (const v of doc.querySelectorAll("video")) {
      if (v.readyState >= 2 || v.currentTime > 0 || v.videoWidth > 0) return true;
    }
  } catch (e) {
    return false;
  }
  return false;
}

if (!ONLY_LIST && DEDUPE && MODE_ACTION !== "list" && clouds.length > 1) {
  // 选择顺序：正在出画面的 > 最新打开的。
  // 只按时序判断会误伤「游戏页在前、登录页后开」；只看活动页会误伤后台打开的游戏页。
  let keep = null;
  for (const t of clouds) {
    if (!hasLiveVideo(t)) continue;
    if (!keep || gB.tabs.indexOf(t) > gB.tabs.indexOf(keep)) keep = t;
  }
  dedupeReason = keep ? "video" : "newest";
  if (!keep) {
    keep = clouds[0];
    for (const t of clouds) {
      if (gB.tabs.indexOf(t) > gB.tabs.indexOf(keep)) keep = t;
    }
  }
  for (const t of clouds) {
    if (t === keep) continue;
    if (hardRemove(t)) deduped += 1;
  }
  clouds = cloudTabs();
  if (clouds.indexOf(keep) < 0) keep = clouds.length ? clouds[clouds.length - 1] : null;
  game = keep;
  if (ST.protectedTab && clouds.indexOf(ST.protectedTab) < 0) ST.protectedTab = null;
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

function isBlankTab(tab) {
  const spec = tabSpec(tab);
  return spec === "" || spec === "about:blank" || spec === "about:newtab" || spec === "about:home";
}

// 建页/导航的 options 校验在各版本间变过：Firefox 158 上给 addTab 传 triggeringPrincipal
// 会抛 "TypeError: 'uri' member of CancelContentJSOptions is not an object"，
// 于是「关掉最后一个标签后自愈」直接失败。这里按能力逐级降级，能走通哪条都行。
function openGameTab(blank) {
  const p = Services.scriptSecurityManager.getSystemPrincipal();
  const nav = (b) => {
    if (!b) return false;
    for (const name of ["fixupAndLoadURIString", "loadURI"]) {
      try {
        if (typeof b[name] === "function") {
          b[name](GAME_URL, { triggeringPrincipal: p });
          return true;
        }
      } catch (e) {}
    }
    return false;
  };
  if (blank && nav(blank.linkedBrowser)) return blank;
  const tries = [
    // addTrustedTab 就是给 chrome 代码用的，不会走那套 CancelContentJSOptions 校验
    () => (typeof gB.addTrustedTab === "function" ? gB.addTrustedTab(GAME_URL) : null),
    () => gB.addTab(GAME_URL, { triggeringPrincipal: p }),
    () => gB.addTab(GAME_URL),
    () => {
      const t = gB.addTab("about:blank");
      nav(t.linkedBrowser);
      return t;
    },
    () => gB.addTab("about:blank")
  ];
  for (const f of tries) {
    try {
      const t = f();
      if (t) return t;
    } catch (e) {}
  }
  return null;
}

let reused = false;
if (!game && !ONLY_LIST) {
  // 会话恢复是懒加载：pending 的标签 URL 还是 about:blank，看起来「没有云游戏页」。
  // 这种情况下新建标签就会多出一页，所以先等它加载完。
  const pending = Array.from(gB.tabs).some(isPending);
  if (!pending) {
    const all = Array.from(gB.tabs);
    const blank = all.length === 1 && isBlankTab(all[0]) ? all[0] : null;
    let attempted = false;
    if (blank) {
      // 只剩一个空标签（关掉最后一个标签后会这样）⇒ 就地装回云游戏，不新增一页
      attempted = true;
      game = openGameTab(blank);
      reused = !!game && game === blank;
    } else if (all.length === 0) {
      attempted = true;
      game = openGameTab(null);
      created = !!game;
    }
    // 云游戏标签页被关掉了（不是被取消固定，是不存在了）：当作“要回到游戏”，
    // 连之前的手动取消固定一起作废 —— 否则重建出来也不钉，Ctrl+W 一下就没了。
    if (attempted && game) {
      ST.respectUser = false;
      ST.selfPinned = null;
    }
    // 只有真的去建页了才报错；只剩一个普通网页时 game 本来就该是 null（用户自己关掉了游戏）
    if (attempted && !game) {
      return { ok: false, err: "add-tab-failed", detail: "所有建页方式都失败（见 openGameTab）" };
    }
  }
}

clouds = cloudTabs();

if (game && MODE_ACTION !== "list") {
  if (!game.pinned && !ST.respectUser) {
    try { gB.pinTab(game); ST.selfPinned = game; } catch (e) {}
  }
  ST.protectedTab = (game.pinned && !ST.respectUser) ? game : null;
  if (MODE_ACTION === "focus-game" || (created && MODE_ACTION !== "close-strays")) {
    try { gB.selectedTab = game; } catch (e) {}
  }
}
if (ST.protectedTab && Array.from(gB.tabs).indexOf(ST.protectedTab) < 0) ST.protectedTab = null;

const tabs = Array.from(gB.tabs).map(function (t, i) {
  return {
    i: i,
    title: t.label || "",
    host: tabHost(t),
    url: tabSpec(t),
    pinned: !!t.pinned,
    active: t === gB.selectedTab,
    game: isGame(t),
    protected: t === ST.protectedTab,
    pending: isPending(t),
    // 只有云游戏页才查视频：这一位就是「这页在出画面」的证据
    video: isGame(t) ? hasLiveVideo(t) : false
  };
});

return {
  ok: true,
  gameFound: !!game,
  created: created,
  reused: reused,
  collapsed: collapsed,
  deduped: deduped,
  dedupeReason: dedupeReason,
  ambiguous: ambiguous,
  blocked: ST.blocked,
  blockedKeys: ST.blockedKeys || 0,
  respectUser: !!ST.respectUser,
  count: tabs.length,
  activeIndex: gB.tabContainer.selectedIndex,
  tabs: tabs
};
"""


BLOCKED_KEYS = [
    {"key": "n", "ctrl": True, "shift": False, "alt": False, "meta": False},
    {"key": "p", "ctrl": True, "shift": True, "alt": False, "meta": False},
    {"key": "a", "ctrl": True, "shift": True, "alt": False, "meta": False},
    {"key": "i", "ctrl": True, "shift": True, "alt": False, "meta": False},
    {"key": "k", "ctrl": True, "shift": True, "alt": False, "meta": False},
    {"key": "c", "ctrl": True, "shift": True, "alt": False, "meta": False},
    {"key": "o", "ctrl": True, "shift": True, "alt": False, "meta": False},
    {"key": "u", "ctrl": True, "shift": False, "alt": False, "meta": False},
    {"key": "j", "ctrl": True, "shift": False, "alt": False, "meta": False},
    {"key": "p", "ctrl": True, "shift": False, "alt": False, "meta": False},
    {"key": "s", "ctrl": True, "shift": False, "alt": False, "meta": False},
    {"key": "o", "ctrl": True, "shift": False, "alt": False, "meta": False},
    {"key": "f12", "ctrl": False, "shift": False, "alt": False, "meta": False},
]


def build_script(hosts, url, action, collapse=False, block_keys=True, dedupe=True):
    return JS_TEMPLATE % {
        "hosts": json.dumps(hosts),
        "url": json.dumps(url),
        "action": json.dumps(action),
        "collapse": "true" if collapse else "false",
        "dedupe": "true" if dedupe else "false",
        "blocked_keys": json.dumps(BLOCKED_KEYS if block_keys else []),
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
    ap.add_argument("--collapse", action="store_true",
                    help="已废弃：默认就会把重复的云游戏页收敛成一页（ENDFIELD_TAB_DEDUPE=0 关闭）")
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

    collapse = bool(args.collapse) or os.environ.get("ENDFIELD_TAB_GUARD_COLLAPSE", "").strip() == "1"
    block_keys = os.environ.get("ENDFIELD_KEY_BLOCK", "1").strip() != "0"
    dedupe = os.environ.get("ENDFIELD_TAB_DEDUPE", "1").strip() != "0"
    script = build_script(hosts, args.url, "list" if action == "list" else action, collapse, block_keys, dedupe)

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

    if action == "once":
        # 守护在跑时再 NewSession 会把它踢掉：只在这份 state 是活的守护写的才让位
        recent = read_json(sfile) or {}
        if recent.get("pid") and pid_alive(recent.get("pid")) and state_fresh(
            sfile, max(10.0, args.interval * 3)
        ):
            print("[tab-guard] 守护正在运行，--once 已跳过（用 --list 查看状态）", file=sys.stderr)
            return 0

    client = MarionetteClient(port=args.port, verbose=args.verbose)
    try:
        client.connect(wait_seconds=args.wait)
        client.new_session("chrome")
    except (MarionetteError, OSError) as exc:
        print("[tab-guard] 无法接管浏览器：%s" % exc, file=sys.stderr, flush=True)
        print(
            "[tab-guard] 警告：标签页守护未生效。云游戏仍可正常游玩，"
            "但 Ctrl+W 不再被拦截、标签页也不会自动固定。",
            file=sys.stderr,
            flush=True,
        )
        return 2

    if action in ("list", "once", "close-strays", "focus-game"):
        try:
            status = parse_status(client.execute(script))
        except (MarionetteError, OSError) as exc:
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
    # 先落一次状态：CLI 靠文件 mtime 判活在，晚写会有一段“看起来守护不在”的窗口
    write_json(sfile, {"ts": time.time(), "pid": os.getpid(), "starting": True})
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
            # 上次会话遗留的命令（例如崩溃前写的）不重放：超过 60 秒一律丢弃
            age = time.time() - float(pending_cmd.get("ts") or 0)
            if age > 60.0:
                log("丢弃陈旧的命令文件（%.0f 秒前写入）" % age)
                try:
                    os.remove(cfile)
                except OSError:
                    pass
                continue
            want = pending_cmd.get("cmd")
            if want in ("close-strays", "focus-game"):
                try:
                    result = parse_status(client.execute(build_script(hosts, args.url, want, collapse, block_keys)))
                    last_cmd = {"id": cmd_id, "cmd": want, "result": result}
                    log(
                        "外部命令 %s 完成：标签 %d 个%s"
                        % (want, result.get("count", 0), "，已切回云游戏" if want == "focus-game" else "")
                    )
                except (MarionetteError, OSError) as exc:
                    last_cmd = {"id": cmd_id, "cmd": want, "result": {"ok": False, "err": str(exc)}}
                    log("外部命令 %s 失败：%s" % (want, exc))
                try:
                    os.remove(cfile)
                except OSError:
                    pass
        try:
            status = parse_status(client.execute(script))
        except (MarionetteError, OSError) as exc:
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
            status.get("ambiguous"),
        )
        if state != last_state:
            last_state = state
            log(format_status(status))
        time.sleep(args.interval)

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
