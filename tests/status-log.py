# 状态日志格式串回归：守护每次状态变化都会打这一行，
# 占位符与参数个数不匹配会让守护在首轮就 TypeError 退出（v1.0.14–v1.2.0 的真实故障）。
#
# 用法: python3 tests/status-log.py
# 依赖: 只用标准库；从 scripts/tab-guard.py 里 import format_status()

import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
TARGET = HERE.parent / "scripts" / "tab-guard.py"

spec = importlib.util.spec_from_file_location("tab_guard", TARGET)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

failed = 0


def check(name, cond, detail=""):
    global failed
    if cond:
        print("PASS " + name)
    else:
        failed += 1
        print("FAIL " + name + ((" :: " + detail) if detail else ""))


cases = [
    ("最小集合", {"count": 1, "gameFound": True, "activeIndex": 0, "blocked": 0}),
    ("空字典", {}),
    ("折叠页", {"count": 1, "gameFound": True, "collapsed": 2, "activeIndex": 0, "blocked": 3}),
    ("同名页", {"count": 2, "gameFound": True, "ambiguous": 2, "activeIndex": 1, "blocked": 0}),
    ("用户取消固定", {"count": 1, "gameFound": True, "respectUser": True, "activeIndex": 0, "blocked": 1}),
    ("全开", {
        "count": 3, "gameFound": False, "collapsed": 1, "ambiguous": 2,
        "respectUser": True, "activeIndex": 2, "blocked": 9,
    }),
]

for name, status in cases:
    try:
        line = mod.format_status(status)
    except Exception as exc:  # noqa: BLE001 - 这里就是要抓任何格式化异常
        check("format." + name, False, "%s: %s" % (type(exc).__name__, exc))
        continue
    check("format." + name, "守护中：标签" in line, line)

# 关键字必须真的出现在输出里，否则日志会误导
line = mod.format_status({"count": 2, "gameFound": True, "ambiguous": 2, "activeIndex": 0, "blocked": 0})
check("text.ambiguous", "同名云游戏页" in line, line)
line = mod.format_status({"count": 1, "gameFound": False, "activeIndex": 0, "blocked": 0})
check("text.rebuild", "缺失→重建" in line, line)
line = mod.format_status({"count": 1, "gameFound": True, "collapsed": 2, "activeIndex": 0, "blocked": 0})
check("text.collapsed", "折叠重复页 2 个" in line, line)

print("== %d passed, %d failed ==" % (len(cases) + 3 - failed, failed))
sys.exit(1 if failed else 0)
