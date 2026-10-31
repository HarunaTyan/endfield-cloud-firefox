# 云·终末地 · Steam Deck Firefox 外壳

一个面向 Steam Deck 的 **Firefox/Gecko 云游戏外壳**：极小的 AppImage 启动 Flatpak Firefox 并加载《明日方舟：终末地》官方云游戏页。实现参考了 [RoderickEzreal/endfield-cloud-steamdeck](https://github.com/RoderickEzreal/endfield-cloud-steamdeck) 的思路，但本项目只维护 Firefox 路线。

> 本项目只包含 Firefox 路线：不含 Electron 源码、构建产物、Steam 快捷方式或游戏资源。AppImage 仅负责启动本机 Flatpak Firefox；发布包不包含 Firefox 本体。

## 产物

| 文件 | 说明 |
|---|---|
| `dist/endfield-cloud-firefox-1.0.11.AppImage` | **Steam 直接选这个**（约 963 KB） |
| `firefox/profile/` | Firefox prefs + userChrome.css |
| `scripts/launch-firefox.sh` | 调试用启动器；Steam UI 不要选 `.sh` |
| `scripts/build-firefox-appimage.sh` | 重新打包 AppImage |
| `firefox/README.md` | Firefox 外壳细节、验证记录、已知缺口 |

Firefox 本体不在 AppImage 里，依赖 Flatpak `org.mozilla.firefox`（测试版本 158.x）。

从 GitHub Releases 下载 AppImage 后先 `chmod +x <file>.AppImage`（Release 资产不带可执行位）；也可以直接运行 `scripts/build-firefox-appimage.sh` 本地构建。

## 前置检查

```sh
flatpak info org.mozilla.firefox >/dev/null && echo firefox-ok
flatpak info --show-permissions org.mozilla.firefox | grep -q '^devices=all' || \
  flatpak override --user --device=all org.mozilla.firefox
```

`devices=all` 是手柄可见的前提；没有它页面仍能开，但 `navigator.getGamepads()` 可能一直是 0。

## 加进 Steam（桌面模式）

1. Steam → 库 → **添加游戏 → 添加非 Steam 游戏 → 浏览**。
2. 选 AppImage（**不是** `launch-firefox.sh`）：

   ```text
   <repo>/dist/endfield-cloud-firefox-1.0.11.AppImage
   ```

3. 名称随意（例如 `Endfield Cloud (Firefox)`）；**启动选项留空**。
   AppRun 自动判断：`gamescope-*` → XWayland + `--kiosk`；桌面 → Wayland + 窗口 1280×800。
4. 该快捷方式 → 控制器 → 布局选 **Gamepad with Joystick Trackpad**。
5. 切游戏模式启动。

命令行兜底（必须先完全退出 Steam；会备份 `shortcuts.vdf`）：

```sh
cd endfield-cloud-firefox
python3 scripts/steam-shortcut.py \
  --name "云·终末地" \
  --exe "$PWD/dist/endfield-cloud-firefox-1.0.11.AppImage" \
  --start-dir "$PWD/dist"
```

## 游戏模式下“有时看不到”

这不是随机丢失，最常见是 **Steam 记住了上次的库标签/筛选**，而不是快捷方式被删：

1. **上次停在「原声带」标签。** 如果 `gamepadui_last_library_tab_and_collection` 的 `strActiveTab` 是 `Soundtracks`，非 Steam 条目会藏在 **游戏** 标签里，切回 Games 即可。
2. **上次选中的条目已不存在。** 若 `UIStoreLocalSteamUIState.currentSelection.nAppId` 指向一个已删除的 appid，Steam 会显示空详情页，看起来像条目消失；把它改成当前 Firefox 条目的 appid。
   在桌面模式点一次 `云·终末地`，再正常退出 Steam，也能让选中状态刷新。
3. **筛选器残留。** Gamepad 库的筛选是 `rgOptions:[1,2,8192]`；在游戏模式按筛选键（Y）→ 清除筛选/选“全部”，确认不是只看“已安装/准备就绪”。
4. **刚添加/改过名字**：退出 Steam 再开；Steam 的非 Steam 库缓存不是每次都热更新。
5. 确认没有被隐藏：桌面库右键该条目 → 管理 → 不应勾选“隐藏此游戏”。

> 改 `localconfig.vdf` 前必须完全退出 Steam，并先备份该文件。

如果 **启动失败**（不是看不见），看日志：

```sh
tail -n 50 ~/.var/app/org.mozilla.firefox/endfield-cloud/launch-firefox.log
```

X11 后端必须带 `--socket=x11`；只写 `--env=DISPLAY` 时 Flatpak 不会给沙箱 X11 窗口（启动器已内置这个参数）。

> Steam 或 Wine 报 “Unable to open a connection to X” 时，先确认 `DISPLAY` 和 `XAUTHORITY` 指向当前图形会话；旧 cookie 会导致 X11 连接失败。

## 为什么其他电脑能看到

**Steam 的非 Steam 快捷方式是本地文件，不是账号云同步。** [Valve 文档](https://developer.valvesoftware.com/wiki/Steam_Library_Shortcuts) 明确 `shortcuts.vdf` 在
`userdata/<SteamID>/config/shortcuts.vdf`，自定义图在 `config/grid/`；账号的 `cloudstorage/` 里没有 shortcuts 记录。

所以“另一台电脑的 Steam 里也显示这两个游戏、状态还是准备就绪”只可能是：

- 那台机器也有自己的一份 `shortcuts.vdf`（手动添加/复制过 userdata/恢复过备份）；
- 或者看到的是同一台机器的另一个 Steam 用户目录/另一次会话，不是真正的另一台机器。

“准备就绪”对非 Steam 条目只表示 **Steam 有一条本地快捷方式**，并不代表云同步、也不代表目标文件在另一台机器上存在。跨机使用要在每台机器上各自添加一次（路径要指向那台机器上真实存在的 AppImage）。如果只复制了 `shortcuts.vdf`、没复制 AppImage，条目仍会显示“准备就绪”，但启动时才报找不到文件。

## 目录结构

```text
endfield-cloud-steamdeck/
├── dist/endfield-cloud-firefox-1.0.11.AppImage
├── firefox/
│   ├── profile/{user.js,chrome/userChrome.css}
│   ├── appimage/{AppRun,*.desktop}
│   └── README.md
├── scripts/
│   ├── launch-firefox.sh
│   ├── build-firefox-appimage.sh
│   ├── install-firefox-shell.sh
│   └── steam-shortcut.py
└── resources/icons/          # AppImage 图标
```

## 重新打包

```sh
cd endfield-cloud-firefox
sh scripts/build-firefox-appimage.sh
```

不再依赖 `package.json`/Node：版本固定为 `1.0.11`（可用 `ENDFIELD_VERSION=...` 覆盖）。首次构建会下载 `appimagetool` 到 `~/.cache/endfield-appimage/`。

## 已知限制

- 页面 UA 检测把 Firefox 排除在 WLRTC（WebTransport+WebCodecs）主通道外，只能走 **WebRTC H264**；H264 可用但 `powerEfficient=false`，1080p60 有软解/发热风险。
- 没有 F12 手柄静音注入点；用系统音量/耳机线控。
- 登录用官方二维码/手机号；本项目不绕过官方登录流程。
- 旧的原生 `Arknights Endfield`（`Launcher.exe` + Proton）与本项目无关；它报 `Unable to open a connection to X` 是 Proton/显示环境问题，直接用新的 `云·终末地` 条目即可。

## 文档与证据

- [firefox/README.md](firefox/README.md) — prefs、运行方式、X11/Flatpak 细节
- [docs/PUBLISHING.md](docs/PUBLISHING.md) — 公开发布检查清单

## 安全与合规

只做外壳：不抓包、不逆向、不修改/绕过登录或协议，不模拟输入。所有游戏数据与登录校验都由官方网页处理。若认为不符合官方用户协议，请不要使用。

## 许可

本项目原创代码使用 MIT（见 `LICENSE`）。`NOTICE` 说明第三方商标、Firefox/Flatpak 运行时与游戏素材的边界；本仓库不包含官方游戏美术、游戏客户端或账号凭据。
