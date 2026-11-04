// 内容世界脚本（指针锁定 / 手柄）单测：不依赖 Firefox，用假 document 跑真脚本
//
// 用法: node tests/pointer-content.mjs
// 为什么单独一个文件: 这段脚本跑在页面世界（content 上下文），
// chrome 侧脚本的测试覆盖不到它；而它正是「光标回不来」的修复点。

import fs from "node:fs";

const py = fs.readFileSync(new URL("../scripts/tab-guard.py", import.meta.url), "utf8");
const MARK = 'CONTENT_TEMPLATE = r"""';
const start = py.indexOf(MARK);
if (start < 0) throw new Error("tab-guard.py 里找不到 CONTENT_TEMPLATE");
const body = start + MARK.length;
const end = py.indexOf('"""', body);
if (end < 0) throw new Error("CONTENT_TEMPLATE 没有结束标记");
const template = py.slice(body, end);

function build(mode) {
  return template.replace("%(mode)s", JSON.stringify(mode));
}

function run(mode, { locked = false, pads = 0, pressed = false, cursor = "auto", broken = false } = {}) {
  const page = { exited: 0 };
  const gamepads = [];
  for (let i = 0; i < pads; i++) {
    gamepads.push({ buttons: [{ pressed, value: pressed ? 1 : 0 }] });
  }
  page.document = {
    pointerLockElement: locked ? { id: "canvas" } : null,
    exitPointerLock() { page.exited += 1; },
    elementFromPoint() { return { nodeName: "CANVAS" }; },
  };
  globalThis.document = page.document;
  // Node 24 起 globalThis.navigator 是只读 getter，得用 defineProperty 覆盖
  Object.defineProperty(globalThis, "navigator", {
    value: { getGamepads: () => (broken ? null : gamepads) },
    configurable: true,
    writable: true,
  });
  globalThis.innerWidth = 1280;
  globalThis.innerHeight = 800;
  globalThis.getComputedStyle = () => ({ cursor });
  const out = new Function("return " + build(mode))();
  return { out, page };
}

let pass = 0;
let fail = 0;
function check(name, cond, detail = "") {
  if (cond) { pass++; console.log("PASS " + name); }
  else { fail++; console.log("FAIL " + name + " " + detail); }
}

// 1) always：锁住就立刻放
{
  const { out, page } = run("always", { locked: true, pads: 1, cursor: "none" });
  check("always.released", page.exited === 1, "exited=" + page.exited);
  check("always.flag", out.released === true);
  check("always.locked-before", out.locked === true);
  check("always.pads", out.pads === 1, "pads=" + out.pads);
  check("always.cursor", out.cursor === "none", "cursor=" + out.cursor);
}

// 2) always 但没锁：什么都不做（不能每轮都调 exitPointerLock）
{
  const { out, page } = run("always", { locked: false, pads: 1 });
  check("always.idle-no-release", page.exited === 0);
  check("always.idle-flag", out.released === false);
}

// 3) off：锁着也不动，如实上报
{
  const { out, page } = run("off", { locked: true, pads: 1, pressed: true });
  check("off.no-release", page.exited === 0);
  check("off.report-locked", out.locked === true);
}

// 4) press：只有按下手柄才放
{
  const idle = run("press", { locked: true, pads: 1, pressed: false });
  check("press.idle-keeps", idle.page.exited === 0);
  const hit = run("press", { locked: true, pads: 1, pressed: true });
  check("press.pressed-releases", hit.page.exited === 1);
}

// 5) 没手柄时报 0，不影响判定
{
  const { out } = run("always", { locked: false, pads: 0 });
  check("pads.zero", out.pads === 0);
}

// 6) getGamepads 抛/返回 null 也不崩
{
  const { out } = run("always", { locked: false, broken: true });
  check("pads.null-safe", out.ok === true && out.pads === 0);
}

// 7) 脚本本身抛错时返回 ok:false，不把守护带崩
{
  const { out } = run("always", { locked: true });
  globalThis.document.exitPointerLock = () => { throw new Error("boom"); };
  const out2 = new Function("return " + build("always"))();
  check("error.captured", out2.ok === false || out2.released === false, JSON.stringify(out2));
  check("baseline.ok", out.ok === true);
}

console.log("");
console.log("== " + pass + " passed, " + fail + " failed ==");
process.exit(fail ? 1 : 0);
