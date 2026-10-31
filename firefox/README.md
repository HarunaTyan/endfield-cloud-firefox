# 云·终末地 · Firefox/Gecko 外壳

用 Flatpak `org.mozilla.firefox` 加载《明日方舟：终末地》官方云游戏页的轻量外壳。
面向 **Steam Deck 游戏模式（gamescope，无桌面）**：作为 Steam「非 Steam 游戏」启动，手柄直接操作。

> 非官方项目，与 Hypergryph / Gryphline 无关；不包含游戏客户端、游戏数据或官方美术资源。请遵守游戏官方用户协议。

## 文件

| 文件 | 作用 |
|---|---|
| `firefox/profile/user.js` | 云游戏 prefs（硬件解码、WebRTC、手柄、自动播放、标签页、去 UI、去遥测） |
| `firefox/profile/chrome/userChrome.css` | 窗口化时隐藏标签栏/导航栏/书签栏/标题栏，黑底，隐藏滚动条，放大 Ctrl+Tab 面板 |
| `firefox/appimage/AppRun` | AppImage 入口；把内置 profile 同步到 Flatpak 可写目录后调用启动器 |
| `scripts/launch-firefox.sh` | 终端启动器；Steam UI 不能直接选 `.sh` |
| `scripts/tab-guard.py` | 标签页守护：锁定云游戏标签页、清场、自愈（由启动器自动拉起） |
| `scripts/build-firefox-appimage.sh` | 重新生成 `dist/endfield-cloud-firefox-<version>.AppImage` |
| `scripts/install-firefox-shell.sh` | 只读环境体检（flatpak/版本/权限/profile/python3/端口） |
| `scripts/steam-shortcut.py` | 可选：写入/列出/删除 Steam 非 Steam 快捷方式（带备份与 dry-run） |

## 运行

```sh
# 需要先安装 Flatpak Firefox，并给手柄权限：
flatpak install flathub org.mozilla.firefox
flatpak override --user --device=all org.mozilla.firefox

# 桌面窗口化（默认 auto：桌面窗口化，检测到 gamescope 时全屏 kiosk）
sh scripts/launch-firefox.sh --windowed

# 只打印命令，不执行
DRY_RUN=1 sh scripts/launch-firefox.sh --windowed

# 强制后端
ENDFIELD_FIREFOX_BACKEND=x11 sh scripts/launch-firefox.sh
```

参数：`--url=URL`、`--window-size=WxH`、`--fullscreen`、`--windowed`、`--window-mode=auto|fullscreen|windowed`。

`--window-mode=auto`：检测到 gamescope（`GAMESCOPE_WAYLAND_DISPLAY` 或 `WAYLAND_DISPLAY=gamescope-*`）
→ XWayland + `--kiosk`；否则 → Wayland + 1280×800 窗口。

## 加进 Steam

1. 在桌面模式运行 `sh scripts/install-firefox-shell.sh`，确认 Flatpak Firefox 与 `devices=all` 正常。
2. 构建 AppImage：`sh scripts/build-firefox-appimage.sh`。
3. Steam → 库 → 添加非 Steam 游戏 → 浏览，选择 `dist/endfield-cloud-firefox-<version>.AppImage`
   （**不要选 `.sh`**），名称例如 `云·终末地`。
4. 启动选项留空。AppRun 会按环境选择 X11/Wayland 与窗口/全屏。
5. 该快捷方式 → 控制器，布局选 **Gamepad with Joystick Trackpad**；切游戏模式启动。

命令行添加（先完全退出 Steam）：

```sh
python3 scripts/steam-shortcut.py \
  --name "云·终末地" \
  --exe "$PWD/dist/endfield-cloud-firefox-<version>.AppImage" \
  --start-dir "$PWD/dist"
```

## 标签页

标签栏被 `userChrome.css` 隐藏，但 `Ctrl+Tab` / `Ctrl+Shift+Tab` / `Ctrl+1` / `Ctrl+W` / `Ctrl+Shift+T`
照常工作。启动器额外拉起 `scripts/tab-guard.py`：把云游戏标签页固定在第一位，并拦截对它的关闭请求
（`Ctrl+W` 在云游戏标签上无效），消失后自动重建。

`ENDFIELD_TAB_GUARD=0` 可关闭守护；此时启动器也不会给 Firefox 加 `--marionette`。
原理、Steam 手柄键位与排错见 [../docs/tabs-and-gamepad.md](../docs/tabs-and-gamepad.md)。

## X11 与手柄

- **游戏模式必须走 XWayland**：启动器在 x11 后端起 `flatpak run --socket=x11 --env=MOZ_ENABLE_WAYLAND=0 --env=DISPLAY=…`。
  只写 `--env=DISPLAY` 不够，Flatpak 默认 Wayland 路径会吃掉 DISPLAY，导致没有 X11 窗口。
- Flatpak 的 `devices=all` 是 `navigator.getGamepads()` 能看到 Steam Input 虚拟手柄的前提。
- 刚加载页面、未按手柄时可能先返回 0 个 gamepad；按一下键后再读即可。
- 日志：`$HOME/.var/app/org.mozilla.firefox/endfield-cloud/launch-firefox.log`（`ENDFIELD_LOG=1` 时保留）。

## 已知限制

- 页面源码对 UA 含 `firefox` 的浏览器禁用 WLRTC（WebTransport + WebCodecs），Firefox 只能走 **WebRTC H264**；
  H264 可用，但 `powerEfficient=false`，1080p60 有软解/发热风险。
- 没有 F12 手柄静音注入点；用系统音量/耳机线控。
- 登录使用官方二维码/手机号，本项目不做绕过。
- Firefox 版本升级后个别 prefs 可能改名；启动前用 `about:support` 或 `prefs.js` 核对。
- 标签页守护走 Firefox 内置的 Marionette 协议；Firefox 大版本改动协议时要同步更新 `scripts/tab-guard.py`。

## 验证

```sh
sh -n scripts/launch-firefox.sh
sh -n scripts/build-firefox-appimage.sh
sh -n firefox/appimage/AppRun
python3 -m py_compile scripts/tab-guard.py
DRY_RUN=1 sh scripts/launch-firefox.sh --windowed
sh scripts/build-firefox-appimage.sh
```

AppImage 只用 `--appimage-extract-and-run` 兼容无 FUSE 环境；在 Steam Deck 上直接双击/FUSE 也可用。
