# 变更记录

本文件是**中文**变更记录，Release 说明以这里的条目为准。版本号与 tag 一致（`vX.Y.Z`）。

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
