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

function buildScript(action) {
  return template
    .replace("%(hosts)s", JSON.stringify(HOSTS))
    .replace("%(url)s", JSON.stringify(GAME))
    .replace("%(action)s", JSON.stringify(action));
}

function mkTab(url, pinned = false, pending = false) {
  const tab = { label: url, pinned, linkedBrowser: { currentURI: { spec: url, host: new URL(url).host } } };
  tab.attrs = new Set(pending ? ["pending"] : []);
  tab.hasAttribute = (name) => tab.attrs.has(name);
  tab.removeAttribute = (name) => tab.attrs.delete(name);
  return tab;
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

function run(action, gB, reuse) {
  const win = reuse || { gBrowser: gB };
  globalThis.Services = {
    wm: { getMostRecentWindow: () => win },
    scriptSecurityManager: { getSystemPrincipal: () => "SYSTEM" },
  };
  return new Function("window", buildScript(action))(win);
}

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

// 2) 云游戏标签缺失 → 自动重建、固定、切回
{
  const gB = mkBrowser([mkTab(STRAY)]);
  const st = run("once", gB);
  check("rebuild.added", gB.added === GAME, String(gB.added));
  check("rebuild.pinned", gB.tabs.find((t) => t.label === GAME)?.pinned === true);
  check("rebuild.created", st.created === true);
  check("rebuild.selected", gB.selectedTab.label === GAME);
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

// 7) 页面自己新开同名 /cloud 页（登录页 + 游戏页）→ 折叠成最新那一页
{
  const gB = mkBrowser([mkTab(GAME, true), mkTab(GAME), mkTab(STRAY)], 1);
  const st = run("once", gB);
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
  const win = { gBrowser: gB };
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

console.log("");
console.log("== " + pass + " passed, " + fail + " failed ==");
process.exit(fail ? 1 : 0);
