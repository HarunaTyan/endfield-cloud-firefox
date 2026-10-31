# Steam Deck 上的常见问题

README 只留三句话，细节都在这里。

## 1. 游戏模式里找不到这条游戏

不是随机丢失，最常见是 **Steam 记住了上次的库标签/筛选**，而不是快捷方式被删：

1. **上次停在「原声带」标签。** 若 `gamepadui_last_library_tab_and_collection` 的 `strActiveTab`
   是 `Soundtracks`，非 Steam 条目会藏在 **游戏** 标签里，切回 Games 即可。
2. **上次选中的条目已不存在。** 若 `UIStoreLocalSteamUIState.currentSelection.nAppId` 指向一个已删除的
   appid，Steam 会显示空详情页，看起来像条目消失；把它改成当前条目的 appid。
   在桌面模式点一次条目，再正常退出 Steam，也能让选中状态刷新。
3. **筛选器残留。** Gamepad 库的筛选是 `rgOptions:[1,2,8192]`；在游戏模式按筛选键（Y）→ 清除筛选，
   确认不是只看「已安装/准备就绪」。
4. **刚添加/改过名字**：退出 Steam 再开；非 Steam 库缓存不是每次都热更新。
5. **被隐藏了**：桌面库右键该条目 → 管理 → 不应勾选「隐藏此游戏」。

> 改 `localconfig.vdf` 前必须完全退出 Steam，并先备份。

## 2. 启动失败怎么查

```sh
tail -n 20 ~/.var/app/org.mozilla.firefox/endfield-cloud/launch-firefox.log
```

日志里 `exec: …` 是真正的 Firefox 命令行，`[tab-guard]` 开头的是标签页守护。
常见原因：

- **X11 连不上**：`X11 后端必须带 --socket=x11`（启动器已内置）。
  Steam 或 Wine 报 `Unable to open a connection to X` 时，先确认 `DISPLAY`、`XAUTHORITY` 指向当前图形会话，
  旧 cookie 会导致连接失败。
- **Flatpak 没装 Firefox**：`flatpak install flathub org.mozilla.firefox`。
- **重复点击退出早**：已有实例在跑时启动器直接返回（退出码 4），这是设计行为。

## 3. 手柄在云游戏里没反应

`navigator.getGamepads()` 一直是 0，九成是 Flatpak 没给设备权限：

```sh
flatpak info --show-permissions org.mozilla.firefox | grep devices   # 应有 devices=all
flatpak override --user --device=all org.mozilla.firefox
```

刚加载页面、还没按过手柄时也可能先读到 0 个手柄，按一下键再读即可。

## 4. 「另一台电脑也能看到这条游戏」是怎么回事

**Steam 的非 Steam 快捷方式是本地文件，不是账号云同步。**
[Valve 文档](https://developer.valvesoftware.com/wiki/Steam_Library_Shortcuts) 明确 `shortcuts.vdf` 在
`userdata/<SteamID>/config/shortcuts.vdf`，自定义图在 `config/grid/`；账号的 `cloudstorage/` 里没有它。

所以跨机看到同一条目只可能是：那台机器也有自己的一份 `shortcuts.vdf`（手动加过/复制过 userdata），
或者你看到的是同一台机器的另一个 Steam 用户目录。

「准备就绪」对非 Steam 条目只表示 **Steam 有一条本地快捷方式**，不代表云同步、也不代表目标文件存在。
跨机使用要在每台机器上各自添加一次，路径指向那台机器上真实的 AppImage；只复制 `shortcuts.vdf`
不复制 AppImage 的话，条目还显示「准备就绪」，启动时才报找不到文件。

## 5. 画质 / 发热

Firefox 走的是 **WebRTC H264** 软解（页面按 UA 把 Firefox 排除在 WebCodecs 通道外，
而 WebRTC 里 Firefox 不实现 H265），1080p60 在 Deck 上会有发热与掉帧。
缓解办法：云游戏页里把画质/帧率降到 720p60 或 1080p30。

注意：Firefox 的 H.265 支持是 `<video>` 播放那套（134/136/137 起按平台陆续开），
跟云游戏的串流通道不是一回事；把 UA 冒充成 Chrome 也只会走进解不了的 WebCodecs。
详见 [gecko-vs-electron.md](gecko-vs-electron.md)「为什么拿不到 H.265」。

## 6. 声音：手柄静音 / 调音量为什么没有

**这是路由决定的，不是没做好**：Electron 方案可以在页面里注入脚本，把「手柄某个键」接到游戏内的
静音/音量逻辑上（所谓 F12 注入点）；本项目是纯浏览器外壳，**不往页面里注入任何脚本**，
也就没有这个接缝。云游戏页本身不认手柄的音量键。

现成可用的做法（都走系统层，管用且不需要改任何东西）：

- 按 **STEAM** 键呼出 Steam 菜单，里面有音量滑块与输出设备切换；
- 直接用 Deck 机身上的 **音量 +/− / 静音** 按钮；
- 用耳机线控。

Steam Input 的按键绑定里如果版本提供「多媒体键/音量」选项，也可以把后拨片绑成音量 +/−，
但这依赖 Steam 客户端版本，不保证每个版本都有 —— 上面三条才是稳的。

