# 标签页与手柄映射

云游戏外壳最怕的一种卡死：游戏里误触手柄/触控板打开别的网页，云游戏被挤到后台标签页，
而页面是 kiosk 全屏、没有标签栏，回不去。这篇文档说明外壳提供的两层机制，以及手柄怎么配。

## 1. 两层机制

| 层 | 手段 | 解决什么 |
|---|---|---|
| 第一层 | Firefox 原生快捷键 | 切换、关闭、恢复标签页 |
| 第二层 | `scripts/tab-guard.py`（Marionette 守护） | 云游戏标签页**关不掉**、消失后**自动重建**、一键清场 |

第一层不依赖任何东西，`Ctrl+Tab` 在 kiosk 全屏下照常工作。
第二层由启动器自动拉起，起不来也不影响游戏。

## 2. 快捷键

| 快捷键 | 作用 | 备注 |
|---|---|---|
| `Ctrl+Tab` | 下一个标签页 | 会弹出 Firefox 的标签切换面板 |
| `Ctrl+Shift+Tab` | 上一个标签页 | |
| `Ctrl+1` | 第 1 个标签页 = 云游戏 | **误触后最省事的一招** |
| `Ctrl+W` | 关闭当前标签页 | 当前是云游戏标签页时被守护拦下，无动作 |
| `Ctrl+Shift+T` | 恢复刚关掉的标签页 | 最多 12 个（`browser.sessionstore.max_tabs_undo`） |

配套的 profile 设置（`firefox/profile/user.js`）：

- `browser.tabs.closeWindowWithLastTab=false`：关掉最后一个标签不会连窗口一起关。
- `browser.tabs.loadInBackground=true`：从页面里点开的链接在**后台**打开，不抢走聚焦。
- `browser.sessionstore.max_tabs_undo=12`：给 `Ctrl+Shift+T` 留够后悔药。
- `browser.ctrlTab.sortByRecentlyUsed=false`：`Ctrl+Tab` 按标签顺序走，不是按最近使用，位置可预期。

## 3. 守护做了什么

`scripts/tab-guard.py` 通过 Firefox 内置的 Marionette 协议（`127.0.0.1:2828`）连进浏览器，
在 **chrome 权限上下文**里做三件事。

> 名词澄清：这里的 **chrome 不是 Google Chrome**，而是 Firefox/Mozilla 的「浏览器界面层」——
> 即标签栏、工具栏、`gBrowser` 这些浏览器自身的部件（所以 profile 里的样式表才叫 `chrome/userChrome.css`）。
> 与之相对的是 **content 上下文**，也就是网页本身能碰到的范围。
> 关标签页的 API 只在 chrome 层，所以守护必须 `WebDriver:SetContext("chrome")` 才能拿到。

1. **固定**：把云游戏标签页 `pinTab`，钉在标签栏第一位（`Ctrl+1` 因此恒定指向它）。
2. **拦截**：给 `gBrowser.removeTab` / `gBrowser.removeCurrentTab` 打补丁，
   目标标签是云游戏时直接返回，`Ctrl+W`、`Ctrl+F4`、标签栏上的关闭按钮全部无效；其他标签照常关。
3. **自愈**：每 3 秒巡检一次，云游戏标签页不在（崩溃恢复、外部脚本、意外）就重建并切回。

启动器只有在**守护真的要跑**时才给 Firefox 加 `--marionette`，所以关掉守护就不会开端口。

### 手动用法

```sh
python3 scripts/tab-guard.py --list           # 列出标签页（JSON：序号、标题、域名、是否固定、是否当前）
python3 scripts/tab-guard.py --close-strays   # 关掉除云游戏外的全部标签，并切回云游戏
python3 scripts/tab-guard.py --focus-game     # 只切回云游戏标签
python3 scripts/tab-guard.py --once           # 执行一次「固定 + 打补丁 + 自愈」
python3 scripts/tab-guard.py --watch          # 持续守护（启动器用的就是这个）
```

退出码：`0` 正常（或浏览器已退出）、`2` 连不上 Marionette、`3` 浏览器侧执行失败。

### 开关

| 环境变量 | 默认 | 说明 |
|---|---|---|
| `ENDFIELD_TAB_GUARD` | `1` | 设 `0` 关掉守护（同时不开 Marionette 端口） |
| `ENDFIELD_MARIONETTE_PORT` | `2828` | 端口；改了要同时给 Firefox 设 `marionette.port` |
| `ENDFIELD_GAME_URL` | `https://endfield.hypergryph.com/cloud` | 自愈时重建用的地址 |
| `ENDFIELD_GAME_HOST` | `endfield.hypergryph.com` | 认哪个域名算云游戏，逗号分隔可加 |

## 4. Steam 手柄映射

云游戏要用 Gamepad 操作，所以标签页快捷键必须放在**不影响游戏内按键**的位置。
Steam Deck 的两套操作集刚好可以这么排：

```text
操作集 GAMEPAD（打游戏用）─── ≡ 键切换 ───▶ 操作集 DESKTOP（打字/桌面用）
```

`≡`（Menu/开始）在两套操作集之间来回切，这是现成的。标签页快捷键加在 **GAMEPAD** 集上，
因为 GAMEPAD 集的 L4 / L5 / R4 一般是空的（游戏本体用不到后拨片）。

### 4.1 推荐键位（GAMEPAD 集）

在「控制器设置 → 编辑布局 → 按键」里，选中对应键，改成**键盘**绑定：

| 手柄键 | 绑定 | 怎么录 |
|---|---|---|
| `L4`（左后拨片） | `Ctrl + Shift + Tab` | 按住 Ctrl+Shift 再按 Tab |
| `L5`（左后拨片） | `Ctrl + Tab` | 按住 Ctrl 再按 Tab |
| `R4`（右后拨片） | `Ctrl + W` | 按住 Ctrl 再按 W |
| `R4` **长按** | `Ctrl + Shift + T` | 同一个键再加一条「长按」绑定 |
| `L5` **长按**（可选） | `Ctrl + 1` | 一键回云游戏标签 |

说明：

- Steam 的按键绑定支持「常规按压 / 长按 / 双击」多条，长按阈值默认约 0.4 秒；
  不想让长按生效就只留常规按压。
- 录制组合键时直接在手柄布局界面按物理键盘的组合，Steam 会记成 `Ctrl + Tab`；
  如果只录到单键，改用「新增额外命令」补第二个键。
- 这些键位是**推荐位**，不是硬要求：按你当前 GAMEPAD 集的空闲键放，别覆盖游戏要用的键。
- 若某个后拨片已被占用，退而求其次用「左触控板点击」「右摇杆点击」——但要先确认游戏不用它们。

### 4.2 DESKTOP 集

DESKTOP 集是给打字和鼠标操作用的（`L1=Ctrl`、`L4=Shift`、`L5=Alt`、右触控板=鼠标），
不建议再塞标签页键。需要切标签时按一次 `≡` 回 GAMEPAD 集即可（`≡` 在 DESKTOP 集里本来就是
「更改操作集（Gamepad）」）。

### 4.3 为什么不用「关闭其他标签」

Firefox 没有「关闭其他标签」的快捷键，`Ctrl+Shift+W` 关的是**窗口**，在 kiosk 下等于退出。
要清场只有两条路：

1. 逐个 `Ctrl+W`（云游戏标签会被拦下）；
2. 在桌面模式跑一次 `python3 scripts/tab-guard.py --close-strays`。

## 5. 排错

| 现象 | 原因 / 处理 |
|---|---|
| 日志出现 `[tab-guard] 无法接管浏览器：连接超时` | Firefox 没带 `--marionette`（自己改了启动命令），或 2828 端口被别的程序（比如 geckodriver）占了：`ss -ltnp \| grep 2828` |
| 启动输出 `未找到 python3，跳过标签页守护` | `command -v python3`；SteamOS 自带，但有些精简系统没有。装上，或接受没有这层保护（快捷键仍可用） |
| `Ctrl+W` 在云游戏标签上「没反应」 | 这是**预期行为**：守护拦下了 |
| `Ctrl+Tab` 弹出面板但看不清 | `userChrome.css` 已调大 `#ctrlTab-panel`；全屏下若仍不可见，用 `Ctrl+1` |
| 守护在 `--watch` 里 3 次失败后退出 | Firefox 已退出或真的失联；重启游戏即可 |
| 想确认守护是否生效 | `python3 scripts/tab-guard.py --list`，看云游戏标签是不是 `"pinned": true` |

日志：`~/.var/app/org.mozilla.firefox/endfield-cloud/launch-firefox.log`（`ENDFIELD_LOG=1` 时保留）。

## 6. 安全边界

- Marionette 只监听 `127.0.0.1`，不对外网开放；Firefox 退出，守护连接断开，端口随之消失。
- 但这仍是「本机任意进程可连」的本地信任模型：能在这台机器上执行代码的人，本来也能读这个 profile
  的 cookie。不需要这层能力就用 `ENDFIELD_TAB_GUARD=0`。
- 守护只改 `gBrowser` 的两个方法，不动页面、不注入 content script、不碰登录态。
