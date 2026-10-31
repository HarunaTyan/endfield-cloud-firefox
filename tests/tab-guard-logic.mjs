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

function buildScript(action, collapse = false, blockKeys = true) {
  return template
    .replace("%(hosts)s", JSON.stringify(HOSTS))
    .replace("%(url)s", JSON.stringify(GAME))
    .replace("%(action)s", JSON.stringify(action))
    .replace("%(collapse)s", collapse ? "true" : "false")
    .replace("%(blocked_keys)s", JSON.stringify(blockKeys ? KEYS : []));
}

function mkTab(url, pinned = false, pending = false) {
  const tab = { label: url, pinned, linkedBrowser: { currentURI: { spec: url, host: new URL(url).host } } };
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

function run(action, gB, reuse, collapse = false) {
  const win = reuse || mkWin(gB);
  LAST_WIN = win;
  globalThis.Services = {
    wm: { getMostRecentWindow: () => win },
    scriptSecurityManager: { getSystemPrincipal: () => "SYSTEM" },
  };
  return new Function("window", buildScript(action, collapse))(win);
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

// 7a) 默认：两个同名 /cloud 页不折叠、不自动固定（分不清哪个是游戏）
{
  const gB = mkBrowser([mkTab(GAME, true), mkTab(GAME), mkTab(STRAY)], 1);
  const st = run("once", gB);
  check("ambig.no-collapse", gB.tabs.length === 3, "tabs=" + gB.tabs.length);
  check("ambig.flag", st.ambiguous === true, "ambiguous=" + st.ambiguous);
  check("ambig.untouched", gB.tabs[1].pinned === false);
}

// 7b) ENDFIELD_TAB_GUARD_COLLAPSE=1 时才折叠成最新那一页
{
  const gB = mkBrowser([mkTab(GAME, true), mkTab(GAME), mkTab(STRAY)], 1);
  const st = run("once", gB, null, true);
  check("dup.collapsed", st.collapsed === 1, "collapsed=" + st.collapsed);
  check("dup.only-one-cloud", gB.tabs.filter((t) => t.label === GAME).length === 1,
    "cloud=" + gB.tabs.filter((t) => t.label === GAME).length);
  check("dup.kept-newest-pinned", gB.tabs[0].label === GAME && gB.tabs[0].pinned === true,
    "tabs=" + gB.tabs.map((t) => t.label + (t.pinned ? "*" : "")).join("|"));
  check("dup.stray-kept", gB.tabs.some((t) => t.label === STRAY));
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
