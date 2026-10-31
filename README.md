# 云·终末地 · Steam Deck 浏览器外壳（Firefox / Gecko）

面向 **Steam Deck 游戏模式**的《明日方舟：终末地》云游戏外壳：一个约 1 MB 的 AppImage，
启动本机 Flatpak Firefox 并直接进入官方云游戏页，手柄即开即玩。

> 非官方项目，与 Hypergryph / Gryphline 无关。本仓库不含游戏客户端、游戏资源、账号凭据或官方美术；
> 只做「把官方网页用合适的浏览器参数打开」这一件事。

## 这个外壳做了什么

- **只走浏览器路线**：AppImage 里只有启动器和一份 Firefox profile，不含游戏客户端或渲染进程。
- **游戏模式 / 桌面模式自动判定**：检测到 gamescope 就 XWayland + `--kiosk`，否则 Wayland + 1280×800 窗口。
- **profile 单向同步**：仓库里的 `user.js` / `userChrome.css` 覆盖到 Flatpak 可写目录，
  不碰 `prefs.js`、cookie 和登录态。
- **单实例**：重复点 Steam 快捷方式不会开出第二个 Firefox。
- **标签页守护**（见下方「标签页」）：误触打开的网页不会把云游戏困在后台，云游戏标签页关不掉。
- **附带 Steam 非 Steam 快捷方式写入器**：带备份与 `--dry-run`，不用手动改 `shortcuts.vdf`。

## 产物

| 文件 | 说明 |
|---|---|
| `dist/endfield-cloud-firefox-<版本>.AppImage` | **Steam 里直接选这个**（约 1 MB） |
| `firefox/profile/` | Firefox prefs + `userChrome.css` |
| `scripts/launch-firefox.sh` | 启动器本体（调试用；Steam UI 里不要选 `.sh`） |
| `scripts/tab-guard.py` | 标签页守护（锁定云游戏标签页、清理误开的标签） |
| `scripts/build-firefox-appimage.sh` | 重新打包 AppImage |
| `firefox/README.md` | Firefox 外壳细节、验证记录、已知缺口 |

Firefox 本体不在 AppImage 里，依赖 Flatpak `org.mozilla.firefox`。

从 GitHub Releases 下载 AppImage 后先 `chmod +x`（Release 资产不带可执行位），
再 `sha256sum -c SHA256SUMS.txt` 校验；也可以直接 `sh scripts/build-firefox-appimage.sh` 本地构建。

## 前置检查

```sh
flatpak info org.mozilla.firefox >/dev/null && echo firefox-ok
flatpak info --show-permissions org.mozilla.firefox | grep -q '^devices=all' || \
  flatpak override --user --device=all org.mozilla.firefox
sh scripts/install-firefox-shell.sh   # 一次性体检：flatpak / 版本 / 权限 / profile 目录 / python3
```

`devices=all` 是手柄可见的前提；没有它页面仍能开，但 `navigator.getGamepads()` 可能一直是 0。

## 加进 Steam（桌面模式）

1. Steam → 库 → **添加游戏 → 添加非 Steam 游戏 → 浏览**。
2. 选 AppImage（**不是** `launch-firefox.sh`）：

   ```text
   <repo>/dist/endfield-cloud-firefox-<版本>.AppImage
   ```

3. 名称随意（例如 `云·终末地`）；**启动选项留空**。
   AppRun 自动判断：`gamescope-*` → XWayland + `--kiosk`；桌面 → Wayland + 窗口 1280×800。
4. 该快捷方式 → 控制器 → 布局选 **Gamepad with Joystick Trackpad**。
5. 切游戏模式启动。

命令行兜底（必须先完全退出 Steam；会自动备份 `shortcuts.vdf`）：

```sh
python3 scripts/steam-shortcut.py \
  --name "云·终末地" \
  --exe "$PWD/dist/endfield-cloud-firefox-<版本>.AppImage" \
  --start-dir "$PWD/dist"
```

## 标签页：切换、关闭、防误关

游戏里误触手柄/触控板打开别的网页后，云游戏会被挤到后台标签页；本外壳用两层机制处理：
**Firefox 原生快捷键 + 一个守护进程**（不装扩展、不改 Firefox 本体）。

| 快捷键 | 作用 |
|---|---|
| `Ctrl+Tab` / `Ctrl+Shift+Tab` | 下一个 / 上一个标签页 |
| `Ctrl+1` | 直接回到第 1 个标签页（云游戏标签页被固定在第一位） |
| `Ctrl+W` | 关闭当前标签页；**当前是云游戏标签页时会被守护拦下，关不掉** |
| `Ctrl+Shift+T` | 恢复刚关掉的标签页 |

守护做三件事：把云游戏标签页**固定（pinned）在第一位**、**拦截**对它的 `removeTab` / `removeCurrentTab`、
万一带外因消失就**自动重建并切回**。原理与排错见 [docs/tabs-and-gamepad.md](docs/tabs-and-gamepad.md)，
手柄键位怎么改见同一篇的「Steam 手柄映射」一节。

手动查询 / 清理：

```sh
python3 scripts/tab-guard.py --list           # 列出当前标签页（JSON）
python3 scripts/tab-guard.py --close-strays   # 关掉除云游戏外的标签，并切回云游戏
python3 scripts/tab-guard.py --focus-game     # 只切回云游戏标签
```

守护由启动器自动拉起；不想要可以 `ENDFIELD_TAB_GUARD=0` 启动 AppImage（此时也不会开 Marionette 端口）。
守护起不来（没装 `python3`、端口被占等）**不影响云游戏本身**，只是少了「关不掉」这层保险。

## 游戏模式下「有时看不到」

这不是随机丢失，最常见是 **Steam 记住了上次的库标签/筛选**，而不是快捷方式被删：

1. **上次停在「原声带」标签。** 如果 `gamepadui_last_library_tab_and_collection` 的 `strActiveTab` 是
   `Soundtracks`，非 Steam 条目会藏在 **游戏** 标签里，切回 Games 即可。
2. **上次选中的条目已不存在。** 若 `UIStoreLocalSteamUIState.currentSelection.nAppId` 指向一个已删除的
   appid，Steam 会显示空详情页，看起来像条目消失；把它改成当前条目的 appid。
   在桌面模式点一次 `云·终末地`，再正常退出 Steam，也能让选中状态刷新。
3. **筛选器残留。** Gamepad 库的筛选是 `rgOptions:[1,2,8192]`；在游戏模式按筛选键（Y）→ 清除筛选/选「全部」，
   确认不是只看「已安装/准备就绪」。
4. **刚添加/改过名字**：退出 Steam 再开；Steam 的非 Steam 库缓存不是每次都热更新。
5. 确认没有被隐藏：桌面库右键该条目 → 管理 → 不应勾选「隐藏此游戏」。

> 改 `localconfig.vdf` 前必须完全退出 Steam，并先备份该文件。

如果 **启动失败**（不是看不见），看日志：

```sh
tail -n 50 ~/.var/app/org.mozilla.firefox/endfield-cloud/launch-firefox.log
```

日志里 `[tab-guard]` 开头的是守护，`exec: …` 是真正的 Firefox 命令行。

X11 后端必须带 `--socket=x11`；只写 `--env=DISPLAY` 时 Flatpak 不会给沙箱 X11 窗口（启动器已内置这个参数）。

> Steam 或 Wine 报 “Unable to open a connection to X” 时，先确认 `DISPLAY` 和 `XAUTHORITY` 指向当前图形会话；
> 旧 cookie 会导致 X11 连接失败。

## 其他电脑为什么也能看到这个条目

**Steam 的非 Steam 快捷方式是本地文件，不是账号云同步。**
[Valve 文档](https://developer.valvesoftware.com/wiki/Steam_Library_Shortcuts) 明确 `shortcuts.vdf` 在
`userdata/<SteamID>/config/shortcuts.vdf`，自定义图在 `config/grid/`；账号的 `cloudstorage/` 里没有 shortcuts 记录。

所以「另一台电脑的 Steam 里也显示这个游戏、状态还是准备就绪」只可能是：

- 那台机器也有自己的一份 `shortcuts.vdf`（手动添加/复制过 userdata/恢复过备份）；
- 或者看到的是同一台机器的另一个 Steam 用户目录/另一次会话，不是真正的另一台机器。

「准备就绪」对非 Steam 条目只表示 **Steam 有一条本地快捷方式**，并不代表云同步、也不代表目标文件在别的机器上存在。
跨机使用要在每台机器上各自添加一次（路径要指向那台机器上真实存在的 AppImage）。如果只复制了 `shortcuts.vdf`、
没复制 AppImage，条目仍会显示「准备就绪」，但启动时才报找不到文件。

## 目录结构

```text
endfield-cloud-firefox/
├── firefox/
│   ├── profile/{user.js,chrome/userChrome.css}
│   ├── appimage/{AppRun,*.desktop}
│   └── README.md
├── scripts/
│   ├── launch-firefox.sh
│   ├── tab-guard.py
│   ├── build-firefox-appimage.sh
│   ├── install-firefox-shell.sh
│   └── steam-shortcut.py
├── resources/{icon.svg,icons/}      # AppImage 图标
└── docs/                            # 标签页与手柄、发布检查清单
```

`dist/` 与 `build/` 是本地构建产物，不进仓库。

## 重新打包

```sh
sh scripts/build-firefox-appimage.sh
```

不依赖 `package.json`/Node：版本号在脚本里（`ENDFIELD_VERSION` 可覆盖）。
首次构建会把 `appimagetool` 下载到 `~/.cache/endfield-appimage/`。

## 已知限制

- 页面 UA 检测把 Firefox 排除在 WLRTC（WebTransport+WebCodecs）主通道外，只能走 **WebRTC H264**；
  H264 可用但 `powerEfficient=false`，1080p60 有软解/发热风险。
- 没有 F12 手柄静音注入点；用系统音量/耳机线控。
- 登录用官方二维码/手机号；本项目不绕过官方登录流程。
- 旧的原生 `Arknights Endfield`（`Launcher.exe` + Proton）与本项目无关；它报
  `Unable to open a connection to X` 是 Proton/显示环境问题，直接用新的 `云·终末地` 条目即可。
- 守护依赖 Firefox 内置的 Marionette 远程协议；Firefox 大版本改动协议时要跟着更新 `scripts/tab-guard.py`。

## 文档

- [firefox/README.md](firefox/README.md) — prefs、运行方式、X11/Flatpak 细节
- [docs/tabs-and-gamepad.md](docs/tabs-and-gamepad.md) — 标签页守护原理、Steam 手柄映射、排错
- [docs/PUBLISHING.md](docs/PUBLISHING.md) — 公开发布检查清单
- [CHANGELOG.md](CHANGELOG.md) — 版本变更（中文）

## 安全与合规

只做外壳：不抓包、不逆向、不修改/绕过登录或协议，不模拟输入。所有游戏数据与登录校验都由官方网页处理。
守护进程只在启动期间监听 `127.0.0.1` 的 Marionette 端口，Firefox 退出即结束；`ENDFIELD_TAB_GUARD=0` 可完全关闭。
若认为不符合官方用户协议，请不要使用。

## 许可

本项目原创代码使用 MIT（见 `LICENSE`）。`NOTICE` 说明第三方商标、Firefox/Flatpak 运行时与游戏素材的边界；
本仓库不包含官方游戏美术、游戏客户端或账号凭据。
