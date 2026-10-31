# 云·终末地（Steam Deck）

在 Steam Deck 上玩《明日方舟：终末地》云游戏的小外壳：装好就能在**游戏模式**里开玩，
不用装浏览器插件，也不用外接键盘鼠标。

> 非官方项目，与鹰角 / Gryphline 无关；不含游戏客户端、账号数据或官方美术。

## 三步开始（只做一次）

**1. 装 Firefox**　桌面模式 → Konsole，粘贴两行：

```sh
flatpak install -y flathub org.mozilla.firefox
flatpak override --user --device=all org.mozilla.firefox
```

第二条是给 Firefox 手柄权限，没有它云游戏看不到手柄。

**2. 下载**　到 [Releases](https://github.com/HarunaTyan/endfield-cloud-firefox/releases/latest)
下最新的 `.AppImage` 和 `SHA256SUMS.txt`，放同一个文件夹，然后给它执行权限：

```sh
chmod +x endfield-cloud-firefox-*.AppImage
```

**3. 加进 Steam**　桌面模式 → 库 → 添加游戏 → 添加非 Steam 游戏 → 浏览 → 选那个 `.AppImage`
（**不是** `.sh`）→ 名字随便写 → 打开它的「控制器」→ 布局选 **Gamepad with Joystick Trackpad**。
之后切回游戏模式，库里就有这条，点开即玩。

启动选项**留空**：外壳会自己判断是游戏模式还是桌面模式。

## 打开之后

等网页加载完，云游戏就直接认手柄。唯一会出岔子的情况是**误触打开了别的网页**，
云游戏被挤到后台标签页——这时候按 **L4** 就能回到游戏（它发的是 `Ctrl+1`，永远指向云游戏那页）。

只想配一个键的话，配 L4 就够；想再顺手一点，另外两个也是空的：

| 手柄键 | 作用 | 要配吗 |
|---|---|---|
| **L4** | 一键回云游戏（`Ctrl+1`） | 建议配，一个就够 |
| **L5** | 下一个标签页（`Ctrl+Tab`） | 可选 |
| **R4** | 关掉当前标签页（`Ctrl+W`，云游戏本身关不掉） | 可选 |

这三个键是 GAMEPAD 集里默认空着的后拨片，加绑定只要一分钟：
[docs/tabs-and-gamepad.md](docs/tabs-and-gamepad.md)。

`≡` 键在两套操作集之间切换（现在就是），DESKTOP 集是留着当鼠标/打字用的，不用改。

## 没有键盘也能做的事

- **打字**（登录、搜索）：按 **STEAM + X** 呼出屏幕键盘，用触控板点。
- **复制粘贴**：先在 DESKTOP 集里（`≡` 切过去），屏幕键盘上点 Ctrl+C / Ctrl+V；
  `L1` 本来就是 Ctrl、`L4` 是 Shift，配合屏幕键盘可以凑出常用组合。
- **关掉误开的网页**：`R4` 一次一个；不想一个个关就在桌面模式跑
  `python3 scripts/tab-guard.py --close-strays`。
- **静音 / 调音量**：按 **STEAM** 键的菜单，或机身音量键。手柄静音在浏览器路线里做不了
  （需要往页面注入脚本），见 [docs/steamdeck-troubleshooting.md](docs/steamdeck-troubleshooting.md)。

## 出问题先看这三条

1. **游戏模式里找不到这条游戏**：多半是 Steam 库停在别的标签或筛了筛选，切回「游戏」标签再看
   （细节见下方文档）。
2. **点了没反应 / 黑屏**：看日志，一行就够：
   ```sh
   tail -n 20 ~/.var/app/org.mozilla.firefox/endfield-cloud/launch-firefox.log
   ```
3. **手柄在游戏里没反应**：多半是第 1 步第二条命令没跑，重跑一次再启动。

更多排错：[docs/steamdeck-troubleshooting.md](docs/steamdeck-troubleshooting.md)（库条目消失、跨机显示、画面/发热）。

## 为什么是 Firefox，不是 Electron

外壳本身只有一个启动器加一份 Firefox 配置（约 1 MB），浏览器用你系统里的 Firefox，
跟着 `flatpak update` 一起升级；Electron 方案要自带一整个 Chromium，体积上百 MB、
安全更新要等作者重新发版。代价是 Firefox 拿不到 WebCodecs 低延迟通道，只能走 WebRTC H264，
1080p60 有软解发热的风险。

完整对比与「什么情况该换 Electron」：[docs/gecko-vs-electron.md](docs/gecko-vs-electron.md)。

## 想改代码 / 自己打包

- 构建、参数、X11/gamescope 细节：[firefox/README.md](firefox/README.md)
- 发版与公开发布检查：[docs/PUBLISHING.md](docs/PUBLISHING.md)
- 变更记录：[CHANGELOG.md](CHANGELOG.md)
- 离线性回归测试（不需要 Deck）：[tests/](tests/)

## 许可

原创代码 MIT（见 `LICENSE`）；`NOTICE` 说明商标与素材边界。
