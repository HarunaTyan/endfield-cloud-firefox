# Gecko（本项目）与 Electron 的差别

一句话：**本项目只是「启动系统里的 Firefox，打开一个网址」，Electron 方案是「自带一整个 Chromium
内核的应用」。** 差别不在理念，在重量、更新方式和能碰到的浏览器能力。

## 对照表

| 维度 | 本项目（Gecko / Firefox） | Electron 方案（Chromium） |
|---|---|---|
| 安装包体积 | 约 1 MB（不含浏览器） | 通常 100 MB+（Chromium 打进包里） |
| 浏览器从哪来 | 系统 Flatpak `org.mozilla.firefox` | 自己打包，随应用分发 |
| 安全更新 | `flatpak update` 一条命令，Mozilla 直接发 | 作者重新打包发版，用户重下 |
| 硬件解码 | 复用 Firefox 现成实现（H264 走 WebRTC） | 可自选 Chromium 编译开关，H265/AV1 也能开 |
| 低延迟通道 | 页面按 UA 把 Firefox 排除，只有 WebRTC H264 | 可用 WebCodecs / WebTransport（WLRTC） |
| 注入页面脚本（F12 面板之类） | 没有钩子，做不到 | 可以 |
| 登录态 | 用户自己的 Firefox profile，二维码/手机号都走官方流程 | 应用自己的 profile，需要自行处理持久化 |
| 手柄 | Flatpak `devices=all` + 标准 Gamepad API | 同左，但要自己接 Chromium 的开关 |
| 攻击面 | 网页跑在 Firefox 内容进程 + Flatpak 沙箱 | 网页跑在 Chromium 沙箱，但主进程带 Node 集成，配置不当更危险 |
| 签名与分发 | Linux 上无需签名，AppImage 直接跑 | Windows/macOS 需要证书，分发链条更长 |
| 版本漂移风险 | 吃 Flatpak Firefox 的大版本变化（pref 名、Marionette 协议） | 吃 Electron 大版本变化，但版本由自己钉死 |

## 本项目的具体短板（已知、可接受）

1. **拿不到 WLRTC**：云游戏页面检测到 UA 含 `firefox` 就不走 WebTransport + WebCodecs 主通道，
   退到 WebRTC H264，`powerEfficient=false`，1080p60 有软解发热。这是画面质量的天花板。
2. **没有页面注入点**：像 F12 那种「把手柄静音按钮塞进游戏内菜单」的做法在 Firefox 里没有对应钩子。
3. **依赖具体 Firefox 版本**：prefs 会改名（例如 `media.ffmpeg.vaapi.enabled` 已被移除），
   标签页守护依赖的 Marionette 协议也可能随大版本调整。
4. **站点只测过 Chrome**：个别网页控件在 Gecko 下表现不同，需要自己兜。

## 什么时候该换 Electron / Chromium

- 需要 H.265/AV1 硬解，或者必须吃到 WebCodecs 低延迟主通道；
- 需要在页面里注入脚本（改 UI、加手柄层、抓面数据）；
- 需要在 Windows/macOS 也发一份（虽然 Electron 也要签名，但生态更顺）。

只要目标还是「在 Deck 游戏模式里把官方云游戏页打开、手柄能用」，Gecko 路线在体积、
更新链路和账号安全上更省事，这也是本项目选它的原因。
