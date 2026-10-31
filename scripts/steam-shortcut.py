#!/usr/bin/env python3
# ============================================================
# Steam 非 Steam 快捷方式管理（shortcuts.vdf 二进制 VDF）
# ============================================================
# 现代 Steam 把非 Steam 快捷方式存在：
#   <Steam>/userdata/<steamid>/config/shortcuts.vdf
# 而不是 localconfig.vdf（旧教程的写法已经过时）。
#
# 用法：
#   steam-shortcut.py --list
#   steam-shortcut.py --name "Endfield Cloud" \
#       --exe "/path/to/launch-firefox.sh" --dry-run
#   steam-shortcut.py --name "Endfield Cloud" \
#       --exe "/path/to/launch-firefox.sh"
#   steam-shortcut.py --remove "Endfield Cloud"
#
# 安全约束：
#   - 默认拒绝在 Steam 运行时写入（Steam 退出时会覆盖 shortcuts.vdf）
#   - 写前自动备份 shortcuts.vdf.bak-<时间戳>
#   - 原子替换，失败不留半截文件
#   - 写完立刻重新解析校验
# ============================================================

import argparse
import glob
import os
import shutil
import struct
import subprocess
import sys
import time
import zlib

TYPE_OBJECT = 0x00
TYPE_STRING = 0x01
TYPE_INT32 = 0x02
TYPE_FLOAT32 = 0x03
TYPE_UINT64 = 0x07
TYPE_END = 0x08
TYPE_INT64 = 0x0A

# 字段顺序与 Steam 自己写出的条目保持一致，避免无谓 diff。
FIELD_ORDER = [
    "appid", "AppName", "Exe", "StartDir", "icon", "ShortcutPath",
    "LaunchOptions", "IsHidden", "AllowDesktopConfig", "AllowOverlay",
    "OpenVR", "Devkit", "DevkitGameID", "DevkitOverrideAppID",
    "LastPlayTime", "FlatpakAppID", "sortas", "tags",
]


class VdfError(Exception):
    pass


class Reader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def read_name(self):
        end = self.data.index(b"\x00", self.pos)
        s = self.data[self.pos:end].decode("utf-8", "replace")
        self.pos = end + 1
        return s

    def read_node(self):
        if self.pos >= len(self.data):
            raise VdfError("unexpected end of file")
        t = self.data[self.pos]
        self.pos += 1
        if t == TYPE_END:
            return ("END", None)
        name = self.read_name()
        if t == TYPE_OBJECT:
            kids = []
            while True:
                node = self.read_node()
                if node[0] == "END":
                    break
                kids.append(node)
            return (name, kids)
        if t == TYPE_STRING:
            return (name, self.read_name())
        if t == TYPE_INT32:
            v = struct.unpack("<i", self.data[self.pos:self.pos + 4])[0]
            self.pos += 4
            return (name, v)
        if t == TYPE_FLOAT32:
            v = struct.unpack("<f", self.data[self.pos:self.pos + 4])[0]
            self.pos += 4
            return (name, v)
        if t == TYPE_UINT64:
            v = struct.unpack("<Q", self.data[self.pos:self.pos + 8])[0]
            self.pos += 8
            return (name, v)
        if t == TYPE_INT64:
            v = struct.unpack("<q", self.data[self.pos:self.pos + 8])[0]
            self.pos += 8
            return (name, v)
        raise VdfError("unknown VDF type 0x%02x for %r at offset %d" % (t, name, self.pos - 1))


def parse_vdf(data):
    r = Reader(data)
    root = r.read_node()
    if root[0] != "shortcuts":
        raise VdfError("root is %r, expected 'shortcuts'" % (root[0],))
    return root


def encode_name(s):
    return s.encode("utf-8") + b"\x00"


def encode_node(name, value):
    out = bytearray()
    if isinstance(value, list):
        out += bytes([TYPE_OBJECT]) + encode_name(name)
        for k, v in value:
            out += encode_node(k, v)
        out += bytes([TYPE_END])
    elif isinstance(value, bool):
        out += bytes([TYPE_INT32]) + encode_name(name) + struct.pack("<i", int(value))
    elif isinstance(value, int):
        out += bytes([TYPE_INT32]) + encode_name(name) + struct.pack("<i", value)
    elif isinstance(value, float):
        out += bytes([TYPE_FLOAT32]) + encode_name(name) + struct.pack("<f", value)
    elif isinstance(value, str):
        out += bytes([TYPE_STRING]) + encode_name(name) + encode_name(value)
    else:
        raise VdfError("cannot encode %r" % (type(value),))
    return bytes(out)


def encode_vdf(root):
    # Steam 自己的文件在根对象结束后还有一个 0x08 结尾标记；
    # 追加它可让文件尾与 Steam 写出的形状一致。
    return encode_node(root[0], root[1]) + bytes([TYPE_END])


def entry_dict(entry):
    return {k: v for k, v in entry[1]}


def find_vdf(explicit=None):
    if explicit:
        return explicit
    candidates = []
    for base in (
        os.path.expanduser("~/.steam/steam/userdata"),
        os.path.expanduser("~/.local/share/Steam/userdata"),
    ):
        for p in glob.glob(os.path.join(base, "*", "config", "shortcuts.vdf")):
            if os.path.isfile(p):
                candidates.append(os.path.realpath(p))
    candidates = sorted(set(candidates))
    if not candidates:
        raise SystemExit("找不到 shortcuts.vdf；请先在 Steam 里登录并添加过一个非 Steam 游戏，或用 --vdf 指定")
    if len(candidates) > 1:
        raise SystemExit(
            "发现多个 Steam 用户的 shortcuts.vdf，请用 --vdf 指定：\n  " + "\n  ".join(candidates)
        )
    return candidates[0]


def steam_running():
    try:
        subprocess.run(["pgrep", "-x", "steam"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def quote_exe(path):
    path = os.path.abspath(os.path.expanduser(path))
    if path.startswith('"') and path.endswith('"'):
        return path
    if " " in path:
        return '"%s"' % path
    return path


def make_appid(exe, name, used):
    base = zlib.crc32((exe + name).encode("utf-8")) & 0x7FFFFFFF
    candidate = base | 0x80000000
    while candidate in used:
        base = (base + 1) & 0x7FFFFFFF
        candidate = base | 0x80000000
    return candidate - 0x100000000 if candidate >= 0x80000000 else candidate


def new_entry(index, exe, name, start_dir, launch_options, icon, flatpak_app_id, used):
    appid = make_appid(exe, name, used)
    fields = {
        "appid": appid,
        "AppName": name,
        "Exe": quote_exe(exe),
        "StartDir": os.path.abspath(os.path.expanduser(start_dir)) + "/",
        "icon": icon or "",
        "ShortcutPath": "",
        "LaunchOptions": launch_options or "",
        "IsHidden": 0,
        "AllowDesktopConfig": 1,
        "AllowOverlay": 1,
        "OpenVR": 0,
        "Devkit": 0,
        "DevkitGameID": "",
        "DevkitOverrideAppID": 0,
        "LastPlayTime": 0,
        "FlatpakAppID": flatpak_app_id or "",
        "sortas": "",
        "tags": [],
    }
    return (str(index), [(k, fields[k]) for k in FIELD_ORDER])


def load(path):
    with open(path, "rb") as f:
        return parse_vdf(f.read())


def save(path, root):
    data = encode_vdf(root)
    # 自校验：写盘前先解析一遍
    parse_vdf(data)
    tmp = path + ".tmp-%d" % os.getpid()
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser(description="管理 Steam 非 Steam 快捷方式（shortcuts.vdf）")
    ap.add_argument("--vdf", help="shortcuts.vdf 路径（默认自动查找）")
    ap.add_argument("--list", action="store_true", help="列出当前快捷方式")
    ap.add_argument("--name", help="快捷方式显示名")
    ap.add_argument("--exe", help="启动目标（可执行文件/脚本的绝对路径）")
    ap.add_argument("--start-dir", help="工作目录（默认 exe 所在目录）")
    ap.add_argument("--launch-options", default="", help="Steam 启动选项")
    ap.add_argument("--icon", default="", help="图标路径（可空）")
    ap.add_argument("--flatpak-app-id", default="", help="Flatpak 应用 ID（可空）")
    ap.add_argument("--remove", metavar="NAME", help="按显示名删除")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不写盘")
    ap.add_argument("--force", action="store_true", help="Steam 运行时也写入（不推荐）")
    args = ap.parse_args()

    path = find_vdf(args.vdf)
    root = load(path)
    entries = root[1]

    if args.list:
        print("VDF: %s" % path)
        for entry in entries:
            d = entry_dict(entry)
            print("  [%s] appid=%s  %s  ->  %s" % (
                entry[0], d.get("appid"), d.get("AppName"), d.get("Exe")))
        return 0

    if args.remove:
        kept = [e for e in entries if entry_dict(e).get("AppName") != args.remove]
        if len(kept) == len(entries):
            raise SystemExit("没有找到名为 %r 的快捷方式" % args.remove)
        if not args.force and steam_running():
            raise SystemExit("Steam 正在运行：先完全退出 Steam（含托盘），否则退出时会被覆盖")
        backup = "%s.bak-%s" % (path, time.strftime("%Y%m%d-%H%M%S"))
        shutil.copy2(path, backup)
        root = ("shortcuts", [(str(i), e[1]) for i, e in enumerate(kept)])
        if args.dry_run:
            print("[dry-run] 将删除 %r，备份到 %s" % (args.remove, backup))
            return 0
        save(path, root)
        print("已删除 %r；备份：%s" % (args.remove, backup))
        return 0

    if not args.name or not args.exe:
        ap.error("添加需要 --name 和 --exe（或用 --list / --remove）")
    if not os.path.exists(os.path.expanduser(args.exe)):
        raise SystemExit("目标不存在：%s" % args.exe)

    used = {entry_dict(e).get("appid") for e in entries}
    for entry in entries:
        if entry_dict(entry).get("AppName") == args.name:
            raise SystemExit("已存在同名快捷方式 %r；先 --remove 或换名字" % args.name)

    idx = max([int(e[0]) for e in entries if str(e[0]).isdigit()], default=-1) + 1
    start_dir = args.start_dir or os.path.dirname(os.path.abspath(os.path.expanduser(args.exe)))
    entry = new_entry(idx, args.exe, args.name, start_dir,
                      args.launch_options, args.icon, args.flatpak_app_id, used)

    print("将添加：")
    for k, v in entry[1]:
        print("  %-20s %r" % (k, v))
    print("VDF: %s" % path)

    if args.dry_run:
        print("[dry-run] 未写盘")
        return 0
    if not args.force and steam_running():
        raise SystemExit("Steam 正在运行：先完全退出 Steam（含托盘），否则退出时会被覆盖；"
                         "确认无风险可用 --force")

    backup = "%s.bak-%s" % (path, time.strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(path, backup)
    root = ("shortcuts", entries + [entry])
    save(path, root)
    check = load(path)
    names = [entry_dict(e).get("AppName") for e in check[1]]
    if args.name not in names:
        raise SystemExit("写入后校验失败：%r 不在 shortcuts.vdf 中（备份在 %s）" % (args.name, backup))
    print("已写入并校验通过；备份：%s" % backup)
    return 0


if __name__ == "__main__":
    sys.exit(main())
