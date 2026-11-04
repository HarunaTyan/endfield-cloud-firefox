# 变更记录

本文件是**中文**变更记录，Release 说明以这里的条目为准。版本号与 tag 一致（`vX.Y.Z`）。

## v1.2.21

- 模式名改回 `--focus`：它现在同时负责拦站外导航与关新标签，一个参数到位。
- `--strict` 移除。

## v1.2.20

- 状态里的 `navBlocked`、`focusClosed`、`focusReturned`、`navCancelFailed`、`closed` 改成累计值：以前每轮巡检清零，`--list` 读到的基本永远是 0，看不出有没有拦到东西。
- 与 `rebuilt` 的处理一致：计数写进守护自己的状态，重启浏览器前一直在。

## v1.2.19

- 恢复默认行为：游戏模式全屏 kiosk，桌面模式普通窗口 1280×800；窗口与否不再由参数决定。
- `--fullscreen` 保留，只用于桌面模式强制全屏；`--windowed` / `--window-mode` / `--window-size` 删除。
- `--tabs` 恢复（窗口模式下调试标签栏与地址栏用）。

## v1.2.18

- 删掉窗口模式：启动一律 kiosk 全屏，`--fullscreen`、`--window-size=` 一并移除（不传参数即全屏）。
- `--tabs` 随窗口模式一起移除：全屏 kiosk 下标签栏本来就不存在。
- 桌面模式启动时提示退出方式（没有 Steam 叠加层，用 `Alt+F4`）。

## v1.2.17

- 清掉遗留开关：`--collapse`（早被默认去重取代）、`--windowed`、`--window-mode=` 全部删除。
- 状态字段 `collapsed` 改名 `closed`，只统计 `--close-strays` 关掉几个标签；日志文案同步。

## v1.2.16

- 两种模式合并成 `--strict`：既拦站外导航（链接、刷新、地址栏），也关掉新出现的标签；`--stay` 移除。
- 严格模式下新标签由 `TabOpen` 事件即时关闭，不再等下一次巡检。

## v1.2.15

- `--stay` 补上新标签：页面里的外跳是 `window.open(..., "_blank")`，最终落在 `gBrowser.addTab` 上。现在在这一层拒绝站外地址，客服、反馈这类“新标签 + 切走”也会被原地拦掉。
- 页面 `window.open` 拿到 null 后会退回 `location.assign`，那一层同样被拦，所以不会因此跳走。

## v1.2.14

- 启动参数改名，按用户看到的结果取名：`--stay`（原 `--block-jumps`）、`--strict`（原 `--focus`）、`--unlock`（原 `--no-guard`）、`--tabs`（原 `--show-chrome`）、`--keys`（原 `--no-key-block`）、`--dupes`（原 `--keep-dupes`）。
- `--windowed` 不再出现在帮助里（行为保留，供调试）。

## v1.2.13

- 修 `--block-jumps` 拦不住工具栏「刷新」和地址栏：它们不走页面点击，而是直接调浏览器的加载接口。现在在 `loadURI` / `loadURIWithFlags` / `fixupAndLoadURIString` / `reload` / `reloadWithFlags` 上包一层，非云游戏地址直接吞掉。
- 取消导航失败时不再静默：计数 `navCancelFailed`，并立刻把页面拉回云游戏。
- 常量不再依赖 `Ci` / `Cr`（chrome 沙箱里不一定有），取不到时用数值兜底。
- 状态新增 `loadGuards`，为 0 说明加载接口没包上。

## v1.2.12

- 修 `--show-chrome` 不生效：原样式只把 `#TabsToolbar` 设为 `-moz-box`，但 `#titlebar` 仍被隐藏，且 `-moz-box` 在 Firefox 158 已不是合法值。改用 `display: revert`，同时恢复 `#titlebar`。

## v1.2.11

- 桌面模式用 `--fullscreen` 启动时提示退出方式：那里没有 Steam 叠加层，STEAM 菜单出不来，只能靠 `Alt+F4`。

## v1.2.10

- `--no-guard` 与 `--focus` / `--block-jumps` 同时给出时，启动日志会写明后两个不会生效：这三者都跑在标签页守护里。

## v1.2.9

- `--block-jumps` 改成在**导航开始时取消**，页面不再离开云游戏，也就不会掉登录态；v1.2.8 的「跳走再拉回」只是在掉线后重进，没有意义。
- 放行范围改为**游戏地址前缀**（`/cloud`），不再按域名放行：官方反馈、客服记录、问题查询都在同一域名下，按域名放行等于没拦。
- 需要额外放行时设 `ENDFIELD_NAV_ALLOW=/oauth,/callback` 之类。
- 状态里 `navBlocked` 是被拦下的导航次数，`jumpGuards` 字段移除。

## v1.2.8

- 新增 `--block-jumps`：拦掉页面里“点了会离开云游戏站”的链接点击，而不是取消导航。
  取消导航会把登录、支付这类流程做到一半掐断，所以只拦用户点击这一层。
- 默认放行 `hypergryph.com/.net` 与 `gryphline.com/.net` 及其子域；需要加别的域名用 `ENDFIELD_JUMP_ALLOW=a.com,b.com`。
- 状态里 `jumpGuards` 表示拦截器实际装到了几个标签上：为 0 说明这一版 Firefox 不支持这种注入，此时只剩“跳走再拉回”。

## v1.2.7

- 专注模式不再关闭「云游戏页自己打开的标签」：登录、支付这类由页面发起的流程会被保留，其余杂页照关。

## v1.2.6

- 新增专注模式 `--focus`（等价 `ENDFIELD_FOCUS=1`）：只允许云游戏页存在。
  被钉住的页跳去别的网站会就地拉回；其它标签页一律关掉；懒加载的页等它加载完再判，避免误关。
- 状态里新增 `focus` / `focusReturned` / `focusClosed`，便于确认它真的在工作。

## v1.2.5

- 新增与 `ENDFIELD_*` 环境变量等价的启动参数：`--no-guard`、`--show-chrome`、`--no-key-block`、`--keep-dupes`、`--port=N`。
  Steam 的启动选项里直接写 `--fullscreen --no-guard` 即可，不必再记 `%command%` 该放前还是放后。
- `--help` 同步列出这些参数。

## v1.2.4

- 状态里新增 `rebuilt` 与 `lastRebuildAt`：重建标签页的累计次数，巡检不会把它冲掉（`created`/`reused` 只反映当轮）。
- 右键菜单按文字兜住漏掉的项：选中文本时的「查看选中部分源代码」、打印项一并隐藏；截图保留。
- 新增 `ENDFIELD_SHOW_CHROME=1`：临时显示标签栏与地址栏，方便手动关标签、排查问题（只写运行 profile，不动仓库文件）。

## v1.2.3

- 云游戏标签页被关掉后重建并重新固定，同时作废之前的手动取消固定。
  以前只要取消过一次固定，守护就彻底放手，连游戏本体被关掉也不管。

## v1.2.2

- 修「关掉最后一个标签后自愈失败」：Firefox 158 上给 `addTab`/`loadURI` 传 `triggeringPrincipal`
  会抛 `CancelContentJSOptions` 类型错误，现在按能力逐级降级（addTab 带参 → 不带参 → about:blank 再导航）。
- 状态日志不再写「有 1 个同名云游戏页」这种误导文案（那是布尔值被当成数量打印）。
- 内容区右键菜单去掉残留的分隔线。

## v1.2.1

修一个存在了五个版本的静默故障：守护打印状态时格式串少一个占位符、参数多一个，
每轮都会抛 `TypeError` 后自行退出。浏览器里的锁定脚本仍在，但守护不再巡检，
于是标签页自愈、误关计数、去重全都停摆。

- 状态日志改为独立函数 `format_status()`，占位符与参数一一对应，并加回归测试 `tests/status-log.py`。
- 同名 `/cloud` 页去重改为「正在出画面的优先」：先看有没有在解码的 `<video>`，没有才退回「最新打开」。
- 右键菜单去掉「查看页面源代码 / 检查 / 另存为 / 保存图像 / 图片另开」这类改不了也退不出的入口，文本复制粘贴保留。

## v1.2.0

安全与稳定性整改（外部代码审查的 P1 / P2 项）。

- 标签页守护不再固定监听 2828：每次启动由系统分配空闲端口，并把端口写进运行 profile。
  需要固定端口时用 `ENDFIELD_MARIONETTE_PORT`。
- 守护连接加超时与大小上限，读写异常不再让守护直接退出；浏览器重启后能自己接回。
- 停掉「留着活动页」的去重逻辑：游戏页可能是在后台打开的，现在留最新打开的那一页。
- 命令文件超过 60 秒视为过期，不再被重放；`--once` 在守护运行时不抢会话。
- 状态与命令文件权限改为 0600、目录 0700。
- 启动参数校验：窗口尺寸必须是数字，`--url` 不接受 `--` 开头的值。
- 构建不再从 `continuous` 拉 appimagetool，固定 1.9.1 并校验 SHA-256。

## v1.1.2

- 资产文件名去掉版本号：`.AppImage` 固定叫 `EndfieldCloud.AppImage`，版本号只出现在压缩包名与 tag 上。
  升级只替换文件内容，Steam 条目的目标路径不变，手柄布局不会因为改名而丢失。
- README 安装步骤与常见问题同步：固定路径 `~/Applications/EndfieldCloud.AppImage`。

## v1.1.1

- 标签栏恢复隐藏（窗口化模式）：重复的 `/cloud` 页已在 1.1.0 收敛成一页，遮住标签栏不再造成"找不到当前页"。
- README 常见问题补一条：下载来的 `.AppImage` 没有执行权限时，用 `.AppImage.tar.gz` 解压，或双击一次确认。

## v1.1.0

同一款游戏的两个 `/cloud` 页只留一页，标签页也重新能关了。

### 修复

- **第二次启动变成两页**：上次会话留下的固定页与本次启动打开的页同时存在，现在收敛成
  **当前这一页**（留活动页，其余关闭），并把留下那页固定。`ENDFIELD_TAB_DEDUPE=0` 可关闭。
- **云游戏页一个都关不掉**：以前按 URL 拦 `removeTab`，同名登录页与游戏页都被拦。
  现在只保护当前这一页（tab 对象身份），其余同域名标签可以正常关闭。

### 变更

- 标签栏保持**可见**（本版用于测试）。隐藏标签栏后同名两页看不出差别，容易误判「卡死」。
- Release 增加 `endfield-cloud-firefox-<版本>.AppImage.tar.gz`：GitHub 下载不保留可执行位，
  从 tar.gz 解压出来就是 755，不必再双击确认或 `chmod +x`。
- `SHA256SUMS.txt` 现在同时覆盖 `.AppImage` 与 `.tar.gz`。

## v1.0.16

把一批「按错一下就把机器搞坏」的浏览器快捷键关掉。

### 新增

- **菜单栏不再弹出**：`ui.key.menuAccessKey=0`（Alt / F10 失效）、`ui.key.chromeAccess=0`、
  `ui.key.contentAccess=0`（Alt+字母 的菜单访问键失效），外加 CSS 压住 `#toolbar-menubar`。
- **工具栏键盘遍历关闭**：`browser.toolbars.keyboard_navigation=false`，Tab 焦点只落在页面上。
- **守护拦下这 13 个组合**（chrome 捕获阶段 `preventDefault`）：
  `Ctrl+N`、`Ctrl+Shift+P`、`Ctrl+Shift+A`、`Ctrl+Shift+I`、`Ctrl+Shift+K`、`Ctrl+Shift+C`、
  `Ctrl+Shift+O`、`Ctrl+U`、`Ctrl+J`、`Ctrl+P`、`Ctrl+S`、`Ctrl+O`、`F12`。
  拦它们的理由：装扩展、清数据、开第二个窗口（多一条串流）、开发者工具挤掉画面。
- **开关**：`ENDFIELD_KEY_BLOCK=0` 放行全部；`ENDFIELD_TAB_GUARD=0` 时这一段同样不生效
  （这类拦截由守护装，不依赖 profile 里的 pref）。

### 保留

- 标签页全部（`Ctrl+T/W/Shift+T/Tab/1-9`）、`Ctrl+L` 地址栏、`Ctrl+F` 查找、缩放、复制粘贴。

## v1.0.15

把「永远只有一个标签页」做成结构上的保证，而不是靠不许出错。

### 新增

- **云游戏就是主页**：`browser.startup.page=1` + `browser.startup.homepage=<云游戏地址>`。
  启动只开这一个标签。
- **启动器不再往命令行塞 URL**（除非显式 `--url=`）：以前是「主页一个标签 + 参数一个标签」，
  这就是两个同名 `/cloud` 页的直接来源。
- **关掉最后一个标签后不空转**：`closeWindowWithLastTab=false`（早就有）让窗口留着，
  守护发现「只有一个空标签」时就地把它导航回云游戏，**不新增一页**，所以仍然只有一个标签。
- **防多余的启动标签**：`browser.aboutwelcome.enabled=false`、
  `browser.startup.homepage_override.mstone=ignore`、`browser.newtabpage.enabled=false`，
  升级后不会多一个「新特性」页或欢迎页。
- **守护不再自作主张补页**：只有一个普通网页时不再硬塞云游戏页（用户自己关掉了就尊重）；
  零标签才新建，唯一空标签则复用。

### 语义

- 「没手动钉标签时永远只有一个标签页」= 主页保证启动一个 + 空标签复用保证关闭后回到一个。
- 手动再开标签、手动钉住，都是用户自己的选择，外壳不干预。

## v1.0.14

v1.0.13 的「折叠重复页」默认打开是个错误判断，这一版收回。

### 修复

- **默认不再自动关标签页**。两个 `/cloud` 页同 URL、同标题，光凭 URL 分不出哪个才是真正进游戏的，
  自动关有把正在玩的那页关掉的风险。折叠改成可选：`ENDFIELD_TAB_GUARD_COLLAPSE=1` 或 `--collapse` 才生效。
- **两个云游戏页时不自动固定**，`--list` 里多一个 `"ambiguous": true` 说明「有歧义、请自己决定」，
  日志也会写「注意：有 2 个同名云游戏页，未自动固定」。
- 固定只在**恰好一个**云游戏页时进行（那种情况没有歧义）。

## v1.0.13

Deck 实测（Firefox 158.0.1）暴露的问题，逐条修掉。

### 修复

- **守护在真 Firefox 上起不来**：`WebDriver:SetContext` 在 138 之后改名成
  `Marionette:SetContext`，且要求启动参数 `-remote-allow-system-access`。守护现在两个命令名都试，
  启动器在有守护时自动加那个参数，端口仍只监听回环。
- **两个同名 `/cloud` 页**：点「开始游戏」时页面自己会新开一个同 URL、同标题的标签，旧版守护
  按 URL 取了第一个（登录页）固定住，用户看到「固定页 + 切不回去」。现在保留**最新**那个、
  把旧的折叠掉；`user.js` 关掉 `browser.sessionstore.restore_on_demand`，
  避免会话恢复时懒加载的标签被误判成「云游戏页不在」而再开一页。
- **不再跟用户抢固定状态**：用户手动取消固定后，本次会话内不再自动 pin。
- **窗口化模式标签栏不再隐藏**：`userChrome.css` 里那条 `#TabsToolbar { display:none }`
  改成注释掉的选项，默认可见。
- **`--list` / `--close-strays` / `--focus-game` 在守护运行时可用**：Firefox 只允许一个
  Marionette 会话，第二个连接会把守护踢掉。现在守护每轮写 `tab-guard-state.json`，
  `--list` 读它；控制命令走 `tab-guard-cmd.json`，由守护用现有会话执行并回写结果。
- **打包不再带 `__pycache__`**：构建脚本打包前清掉 Python 字节码缓存。

### 变更

- 守护的 `blocked` 计数不再是「关不掉」的证据：原生 pinned 标签本来就拦 `Ctrl+W`。
- 新增 `tests/bench-guard.mjs`，量守护每轮的实际开销。

## v1.0.12

### 新增

- **标签页守护** `scripts/tab-guard.py`：把云游戏标签页固定在标签栏第一位，
  拦截对它的 `removeTab` / `removeCurrentTab`（`Ctrl+W`、`Ctrl+F4`、关闭按钮全部失效），
  云游戏标签页意外消失时自动重建并切回。由启动器自动拉起，`ENDFIELD_TAB_GUARD=0` 可关闭。
- **标签页快捷键**：`Ctrl+Tab` / `Ctrl+Shift+Tab` 切换，`Ctrl+1` 直接回云游戏，
  `Ctrl+Shift+T` 恢复误关的标签。`user.js` 增加配套开关（后台开链接、不连窗口关最后一个标签、
  多留 12 个可恢复标签、`Ctrl+Tab` 按顺序切换）。
- **Steam 手柄映射文档** `docs/tabs-and-gamepad.md`：在现有 GAMEPAD / DESKTOP 两套操作集上，
  用空闲的 L4 / L5 / R4 加标签页键位，不占用游戏内按键。
- **中文发版**：Release 标题与正文改为中文，`.github/release.yml` 用中文分类名，
  并在 `docs/PUBLISHING.md` 写明「CI 出资产、人补中文正文」的流程；新增中文 `CHANGELOG.md`。
- **离线回归测试** `tests/`：守护的浏览器侧逻辑（`node tests/tab-guard-logic.mjs`，21 条断言）
  与 Marionette 通信层（`python3 tests/marionette-mock.py`），都不需要 Deck。

### 改进

- `userChrome.css` 放大 `Ctrl+Tab` 标签切换面板（标签栏隐藏后，这是唯一能看清标签标题的地方）。
- `install-firefox-shell.sh` 增加 `python3` 与 Marionette 端口检查，提前暴露「守护起不来」的原因。
- `launch-firefox.sh` 只在守护真的要跑时才给 Firefox 加 `--marionette`，
  并在端口被占用时跳过守护而不是让浏览器起不来。
- `SECURITY.md`、`NOTICE`（加中文摘要）、`AppRun --help`、`.desktop` 全部中文化。
- `README` 结构调整：先讲「这个外壳做了什么」，再讲使用；版本号统一写成 `<版本>` 占位。

### 清理

- 移除对同类项目的引用与路线对比表述，正文只描述本项目自己做了什么。
- 目录结构示例、注释里的旧项目名统一为本项目名。
- `.gitignore` 去掉重复规则。

## v1.0.11

- 首个可分发版本：Firefox/Gecko 云游戏外壳（AppImage + Flatpak Firefox），
  gamescope 自动 XWayland + kiosk、桌面模式窗口化，profile 单向同步、单实例、
  Steam 非 Steam 快捷方式写入器。
