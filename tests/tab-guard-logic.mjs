// 标签页守护的浏览器侧逻辑单测（不依赖 Firefox，用假的 gBrowser 跑真脚本）
//
// 用法: node tests/tab-guard-logic.mjs
// 作用: 直接从 scripts/tab-guard.py 里取出注入浏览器的 JS，注入一个假 tabbrowser 运行，
//       断言「固定、拦截关闭、清理、自愈、list 无副作用」这些行为。
//       Firefox 本体升级 Marionette 协议时，这条测试仍能保证脚本逻辑没坏。

import fs from "node:fs";

const GAME = "https://endfield.hypergryph.com/cloud";
const STRAY = "https://example.com/";
const HOSTS = ["endfield.hypergryph.com"];

const py = fs.readFileSync(new URL("../scripts/tab-guard.py", import.meta.url), "utf8");
const MARK = 'JS_TEMPLATE = r"""';
const start = py.indexOf(MARK);
if (start < 0) throw new Error("tab-guard.py 里找不到 JS_TEMPLATE");
const body = start + MARK.length;
const end = py.indexOf('"""', body);
if (end < 0) throw new Error("JS_TEMPLATE 没有结束标记");

const template = py.slice(body, end);

const KEYS = [
  { key: "n", ctrl: true, shift: false, alt: false, meta: false },
  { key: "p", ctrl: true, shift: true, alt: false, meta: false },
  { key: "a", ctrl: true, shift: true, alt: false, meta: false },
  { key: "i", ctrl: true, shift: true, alt: false, meta: false },
  { key: "k", ctrl: true, shift: true, alt: false, meta: false },
  { key: "c", ctrl: true, shift: true, alt: false, meta: false },
  { key: "o", ctrl: true, shift: true, alt: false, meta: false },
  { key: "u", ctrl: true, shift: false, alt: false, meta: false },
  { key: "j", ctrl: true, shift: false, alt: false, meta: false },
  { key: "p", ctrl: true, shift: false, alt: false, meta: false },
  { key: "s", ctrl: true, shift: false, alt: false, meta: false },
  { key: "o", ctrl: true, shift: false, alt: false, meta: false },
  { key: "f12", ctrl: false, shift: false, alt: false, meta: false },
];

function buildScript(action, { dedupe = true, blockKeys = true, collapse = false } = {}) {
  return template
    .replace("%(hosts)s", JSON.stringify(HOSTS))
    .replace("%(url)s", JSON.stringify(GAME))
    .replace("%(action)s", JSON.stringify(action))
    .replace("%(collapse)s", collapse ? "true" : "false")
    .replace("%(dedupe)s", dedupe ? "true" : "false")
    .replace("%(blocked_keys)s", JSON.stringify(blockKeys ? KEYS : []));
}

function mkTab(url, pinned = false, pending = false, video = false) {
  // video=true 模拟「这页正在出画面」：游戏页里有一个已解码的 <video>
  const doc = {
    querySelectorAll: (sel) =>
      sel === "video" && video ? [{ readyState: 4, currentTime: 12.5, videoWidth: 1280 }] : [],
  };
  const tab = {
    label: url,
    pinned,
    linkedBrowser: { currentURI: { spec: url, host: new URL(url).host }, contentDocument: doc },
  };
  tab.attrs = new Set(pending ? ["pending"] : []);
  tab.hasAttribute = (name) => tab.attrs.has(name);
  tab.removeAttribute = (name) => tab.attrs.delete(name);
  return tab;
}

function mkWin(gB) {
  const listeners = [];
  return {
    gBrowser: gB,
    addEventListener(type, fn, capture) { listeners.push({ type, fn, capture }); },
    removeEventListener() {},
    __listeners: listeners,
  };
}

function mkBrowser(tabs, selectedIdx = 0) {
  const gB = {
    tabs,
    selectedTab: tabs[selectedIdx],
    tabContainer: { get selectedIndex() { return gB.tabs.indexOf(gB.selectedTab); } },
    closed: 0,
    added: null,
    removeTab(tab) {
      const i = gB.tabs.indexOf(tab);
      if (i >= 0) { gB.tabs.splice(i, 1); gB.closed++; }
    },
    removeCurrentTab() { gB.removeTab(gB.selectedTab); },
    pinTab(t) { t.pinned = true; },
    addTab(url) {
      const t = mkTab(url);
      gB.tabs.unshift(t);
      gB.added = url;
      gB.selectedTab = t;
      return t;
    },
  };
  return gB;
}

function run(action, gB, reuse, opts) {
  const win = reuse || mkWin(gB);
  LAST_WIN = win;
  globalThis.Services = {
    wm: { getMostRecentWindow: () => win },
    scriptSecurityManager: { getSystemPrincipal: () => "SYSTEM" },
  };
  return new Function("window", buildScript(action, opts))(win);
}

let LAST_WIN = null;
let pass = 0;
let fail = 0;
function check(name, cond, detail = "") {
  if (cond) { pass++; console.log("PASS " + name); }
  else { fail++; console.log("FAIL " + name + " " + detail); }
}

// 1) once：固定云游戏标签、拦截关闭、其他标签照常关
{
  const gB = mkBrowser([mkTab(GAME), mkTab(STRAY)]);
  const st = run("once", gB);
  check("once.ok", st.ok === true);
  check("once.pinned", gB.tabs[0].pinned === true);
  check("once.gameFound", st.gameFound === true);
  check("once.no-add", gB.added === null);
  check("once.count", st.count === 2, "count=" + st.count);

  gB.removeTab(gB.tabs[0]);                       // 关云游戏标签 → 应被拦
  check("once.block-close-game", gB.tabs.length === 2 && gB.closed === 0,
    "tabs=" + gB.tabs.length + " closed=" + gB.closed);

  gB.selectedTab = gB.tabs[1];
  gB.removeCurrentTab();                          // 关误触标签 → 应成功
  check("once.close-stray-ok", gB.tabs.length === 1 && gB.closed === 1,
    "tabs=" + gB.tabs.length + " closed=" + gB.closed);

  const again = run("once", gB);                  // 幂等：不重复打补丁
  check("once.idempotent", typeof again.blocked === "number", JSON.stringify(again.blocked));
  gB.removeCurrentTab();                          // 当前是云游戏标签，仍应被拦
  check("once.still-blocked", gB.tabs.length === 1, "tabs=" + gB.tabs.length);
}

// 2a) 一个标签都没有 → 新建云游戏页、固定、切回
{
  const gB = mkBrowser([]);
  const st = run("once", gB);
  check("rebuild.added", gB.added === GAME, String(gB.added));
  check("rebuild.pinned", gB.tabs.find((t) => t.label === GAME)?.pinned === true);
  check("rebuild.created", st.created === true);
  check("rebuild.selected", gB.selectedTab.label === GAME);
}

// 2b) 只剩一个空标签（关掉最后一个标签后）→ 就地装回主页，不新增一页
{
  const blank = mkTab("about:blank");
  blank.loadedTo = null;
  blank.linkedBrowser.loadURI = (uri) => { blank.loadedTo = uri; blank.attrs.delete("pending"); };
  const gB = mkBrowser([blank]);
  const st = run("once", gB);
  check("reuse.loaded", blank.loadedTo === GAME, String(blank.loadedTo));
  check("reuse.no-add", gB.added === null, String(gB.added));
  check("reuse.one-tab", gB.tabs.length === 1, "tabs=" + gB.tabs.length);
  check("reuse.flag", st.reused === true);
  check("reuse.pinned", blank.pinned === true);
}

// 2b2) Firefox 158 现场：addTab 带 options 会抛 CancelContentJSOptions，
//      关掉最后一个标签后必须还能降级建页，不许直接失败
{
  const gB = mkBrowser([], 0);
  const realAdd = gB.addTab;
  let calls = 0;
  gB.addTab = function (url, opts) {
    calls += 1;
    if (opts) throw new TypeError("'uri' member of CancelContentJSOptions is not an object.");
    return realAdd.call(gB, url);
  };
  const st = run("once", gB);
  check("addtab.fallback-ok", st.ok === true, JSON.stringify(st));
  check("addtab.created", st.created === true);
  check("addtab.one-tab", gB.tabs.length === 1, "tabs=" + gB.tabs.length);
  check("addtab.retried", calls >= 2, "calls=" + calls);
}

// 2b3) 有 addTrustedTab 时优先用它（它不经过 CancelContentJSOptions 校验）
{
  const gB = mkBrowser([], 0);
  let trusted = 0;
  gB.addTrustedTab = (url) => {
    trusted += 1;
    const t = mkTab(url);
    gB.tabs.unshift(t);
    gB.added = url;
    gB.selectedTab = t;
    return t;
  };
  gB.addTab = () => { throw new TypeError("'uri' member of CancelContentJSOptions is not an object."); };
  const st = run("once", gB);
  check("trusted.used", trusted === 1, "trusted=" + trusted);
  check("trusted.ok", st.ok === true && st.created === true, JSON.stringify(st));
}

// 2c) 只剩一个普通网页 → 不硬塞云游戏页（用户自己关掉了游戏，别抢）
{
  const gB = mkBrowser([mkTab(STRAY)]);
  const st = run("once", gB);
  check("stray.no-add", gB.added === null, String(gB.added));
  check("stray.kept", gB.tabs.length === 1 && gB.tabs[0].label === STRAY);
  check("stray.gameFound", st.gameFound === false);
}

// 3) list：只读，不建标签、不打补丁、不动选中
{
  const gB = mkBrowser([mkTab(STRAY)], 0);
  const st = run("list", gB);
  check("list.no-add", gB.added === null);
  check("list.no-close", gB.closed === 0);
  check("list.json", Array.isArray(st.tabs) && st.tabs.length === 1 && st.tabs[0].host === "example.com",
    JSON.stringify(st.tabs));
  check("list.not-pinned", gB.tabs[0].pinned === false);
}

// 4) close-strays：只留云游戏标签
{
  const gB = mkBrowser([mkTab(GAME), mkTab(STRAY), mkTab("https://b.example.org/")], 1);
  const st = run("close-strays", gB);
  check("strays.only-game", gB.tabs.length === 1 && gB.tabs[0].label === GAME, "tabs=" + gB.tabs.length);
  check("strays.ok", st.ok === true);
}

// 5) focus-game：切回云游戏标签
{
  const gB = mkBrowser([mkTab(GAME), mkTab(STRAY)], 1);
  run("focus-game", gB);
  check("focus.selected", gB.selectedTab.label === GAME, gB.selectedTab.label);
}

// 6) 没有浏览器窗口时不要抛异常
{
  globalThis.Services = { wm: { getMostRecentWindow: () => null }, scriptSecurityManager: {} };
  const st = new Function("window", buildScript("once"))({});
  check("no-window", st.ok === false && st.err === "no-browser-window", JSON.stringify(st));
}

// 7a) 第二次启动的现场：上次固定的 /cloud + 本次启动打开的 /cloud（活动）
//     期望：只留活动那一页，并把它固定；别的标签不动
{
  const login = mkTab(GAME, true);            // 上次会话恢复的固定页
  const gameTab = mkTab(GAME);                // 本次启动打开的页（活动）
  const gB = mkBrowser([login, gameTab, mkTab(STRAY)], 1);
  const st = run("once", gB);
  check("dup.only-one-cloud", gB.tabs.filter((t) => t.label === GAME).length === 1,
    "cloud=" + gB.tabs.filter((t) => t.label === GAME).length);
  check("dup.kept-active", gB.tabs.includes(gameTab), "tabs=" + gB.tabs.map((t) => t.label).join("|"));
  check("dup.deduped", st.deduped === 1, "deduped=" + st.deduped);
  check("dup.kept-pinned", gameTab.pinned === true);
  check("dup.ambiguous-flag", st.ambiguous === true);
  check("dup.stray-kept", gB.tabs.some((t) => t.label === STRAY));
  check("dup.protected", st.tabs.some((t) => t.protected === true && t.game === true));
}

// 7c) 游戏页在后台打开（loadInBackground=true 的现场）：
//     活动页是登录页，新开的 /cloud 在后面。以「活动页」为准会误关游戏页，
//     所以必须留最新的那一页，而不是留活动页。
{
  const login = mkTab(GAME);                  // 旧的 /cloud，活动
  const gameTab = mkTab(GAME);                // 本次启动新开的 /cloud，在后台
  const gB = mkBrowser([login, gameTab], 0);
  const st = run("once", gB);
  check("dupbg.kept-newest", gB.tabs.includes(gameTab), "tabs=" + gB.tabs.map((t) => t.label).join("|"));
  check("dupbg.closed-old", !gB.tabs.includes(login));
  check("dupbg.pinned", gameTab.pinned === true);
  check("dupbg.deduped", st.deduped === 1, "deduped=" + st.deduped);
}

// 7d) 游戏页已经在出画面、登录页最后打开：
//     只按时序会留登录页，必须让「有视频」的那页赢
{
  const gameTab = mkTab(GAME, false, false, true);   // 早开，已有 <video>
  const login = mkTab(GAME);                          // 刚打开，无视频，最新
  const gB = mkBrowser([gameTab, login], 1);
  const st = run("once", gB);
  check("dupvid.flag-video", st.tabs.some((t) => t.video === true), JSON.stringify(st.tabs.map((t) => t.video)));
  check("dupvid.kept-video", gB.tabs.includes(gameTab), "tabs=" + gB.tabs.map((t) => t.label).join("|"));
  check("dupvid.closed-login", !gB.tabs.includes(login));
  check("dupvid.deduped", st.deduped === 1, "deduped=" + st.deduped);
  check("dupvid.reason", st.dedupeReason === "video", "reason=" + st.dedupeReason);
}

// 7e) 两页都没视频：退回「留最新那一页」（v1.2.0 行为不变）
{
  const oldTab = mkTab(GAME);
  const newTab = mkTab(GAME);
  const gB = mkBrowser([oldTab, newTab], 0);
  const st = run("once", gB);
  check("dupnone.kept-newest", gB.tabs.includes(newTab), "tabs=" + gB.tabs.map((t) => t.label).join("|"));
  check("dupnone.reason", st.dedupeReason === "newest", "reason=" + st.dedupeReason);
}

// 7b) ENDFIELD_TAB_DEDUPE=0：不收敛，两个 /cloud 页都留着，且都能关
{
  const gB = mkBrowser([mkTab(GAME, true), mkTab(GAME), mkTab(STRAY)], 1);
  const st = run("once", gB, null, { dedupe: false });
  check("nod.three-tabs", gB.tabs.length === 3, "tabs=" + gB.tabs.length);
  check("nod.deduped-zero", st.deduped === 0);
  const before = gB.tabs.length;
  gB.removeTab(gB.tabs[0]);                   // 非保护页：以前按 URL 会拦，现在应放行
  check("nod.close-other-cloud", gB.tabs.length === before - 1 && gB.closed === 1,
    "tabs=" + gB.tabs.length + " closed=" + gB.closed);
}

// 7c) 只保护当前页：非保护的同名 /cloud 页可以关，保护页关不掉
{
  const gB = mkBrowser([mkTab(GAME, true), mkTab(GAME), mkTab(STRAY)], 1);
  run("once", gB);
  const prot = gB.tabs.find((t) => t.pinned === true);
  check("prot.exists", !!prot);
  const other = gB.tabs.find((t) => t !== prot && t.label === STRAY);
  gB.removeTab(other);
  check("prot.close-stray", gB.tabs.includes(other) === false, "tabs=" + gB.tabs.length);
  gB.removeTab(prot);
  check("prot.block-self", gB.tabs.includes(prot) === true, "tabs=" + gB.tabs.length);
}

// 8) 会话恢复懒加载：pending 标签不会被当成「没有云游戏页」而再开一页
{
  const gB = mkBrowser([mkTab("about:blank", false, true)], 0);
  const st = run("once", gB);
  check("pending.no-add", gB.added === null, String(gB.added));
  check("pending.no-created", st.created === false);
}

// 9) 用户手动取消钉住后不再抢回去（同一 window 跑两轮）
{
  const gB = mkBrowser([mkTab(GAME)], 0);
  const win = mkWin(gB);
  run("once", gB, win);
  check("unpin.pinned-first", gB.tabs[0].pinned === true);
  gB.tabs[0].pinned = false;          // 用户手动取消固定
  run("once", gB, win);
  const st = run("once", gB, win);
  check("unpin.respected", st.respectUser === true && gB.tabs[0].pinned === false,
    "respectUser=" + st.respectUser + " pinned=" + gB.tabs[0].pinned);
}

// 9b) 取消固定之后又把游戏标签页关掉：必须重建并重新固定（作废 respectUser）
{
  const gB = mkBrowser([mkTab(GAME)], 0);
  const win = mkWin(gB);
  run("once", gB, win);
  gB.tabs[0].pinned = false;               // 用户取消固定
  run("once", gB, win);                    // 守护记下 respectUser
  gB.tabs.length = 0;                      // 用户把唯一的标签页关掉了
  const st = run("once", gB, win);
  check("reopen.created", st.created === true, JSON.stringify(st));
  check("reopen.one-tab", gB.tabs.length === 1, "tabs=" + gB.tabs.length);
  check("reopen.pinned", gB.tabs[0] && gB.tabs[0].pinned === true, "pinned=" + (gB.tabs[0] || {}).pinned);
  check("reopen.respect-cleared", st.respectUser === false, "respectUser=" + st.respectUser);
  check("reopen.protected", st.tabs.some((t) => t.protected === true), JSON.stringify(st.tabs));
  check("reopen.rebuilt-counter", st.rebuilt === 1 && st.lastRebuildAt > 0, "rebuilt=" + st.rebuilt);
}

// 10) list 不改任何东西：重复页不折叠、pending 不触发建页、不 pin
{
  const gB = mkBrowser([mkTab(GAME, true), mkTab(GAME), mkTab("about:blank", false, true)], 1);
  const st = run("list", gB);
  check("list.no-collapse", gB.tabs.length === 3, "tabs=" + gB.tabs.length);
  check("list.still-unpinned", gB.tabs[1].pinned === false);
  check("list.collapsed-zero", st.collapsed === 0);
}

// 11) 键盘拦截：命中清单吞掉，其余放行
{
  const gB = mkBrowser([mkTab(GAME)], 0);
  run("once", gB);
  const win = LAST_WIN;
  const keyFilter = win.__endfieldTabGuard.keyFilter;
  const mk = (key, mods = {}) => ({
    key,
    ctrlKey: !!mods.ctrl,
    shiftKey: !!mods.shift,
    altKey: !!mods.alt,
    metaKey: !!mods.meta,
    defaultPrevented: false,
    isComposing: false,
    _stopped: false,
    preventDefault() { this.defaultPrevented = true; },
    stopPropagation() { this._stopped = true; },
  });

  const blocked = [
    ["n", { ctrl: true }],
    ["N", { ctrl: true }],
    ["p", { ctrl: true, shift: true }],
    ["a", { ctrl: true, shift: true }],
    ["i", { ctrl: true, shift: true }],
    ["k", { ctrl: true, shift: true }],
    ["c", { ctrl: true, shift: true }],
    ["o", { ctrl: true, shift: true }],
    ["u", { ctrl: true }],
    ["j", { ctrl: true }],
    ["p", { ctrl: true }],
    ["s", { ctrl: true }],
    ["o", { ctrl: true }],
    ["F12", {}],
  ];
  let allBlocked = true;
  for (const [key, mods] of blocked) {
    const ev = mk(key, mods);
    keyFilter(ev);
    if (!ev.defaultPrevented) { allBlocked = false; console.log("  not blocked:", key, JSON.stringify(mods)); }
  }
  check("keys.blocked", allBlocked);

  const allowed = [
    ["c", { ctrl: true }],            // 复制
    ["v", { ctrl: true }],            // 粘贴
    ["t", { ctrl: true }],            // 新标签
    ["w", { ctrl: true }],            // 关标签
    ["1", { ctrl: true }],            // 回云游戏
    ["Tab", { ctrl: true }],          // 切标签
    ["l", { ctrl: true }],            // 地址栏
    ["f", { ctrl: true }],            // 查找
    ["s", { ctrl: false }],           // 裸 s
  ];
  let noFalsePositive = true;
  for (const [key, mods] of allowed) {
    const ev = mk(key, mods);
    keyFilter(ev);
    if (ev.defaultPrevented) { noFalsePositive = false; console.log("  wrongly blocked:", key, JSON.stringify(mods)); }
  }
  check("keys.allowed", noFalsePositive);
}

// 12) list 模式不装键盘拦截、不动状态
{
  const gB = mkBrowser([mkTab(GAME)], 0);
  const st = run("list", gB);
  check("keys.list-no-filter", globalThis.__noop === undefined && LAST_WIN.__endfieldTabGuard.keyFilter === undefined);
}

console.log("");
console.log("== " + pass + " passed, " + fail + " failed ==");
process.exit(fail ? 1 : 0);
