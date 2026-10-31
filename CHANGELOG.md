# 变更记录

本文件是**中文**变更记录，Release 说明以这里的条目为准。版本号与 tag 一致（`vX.Y.Z`）。

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
- **中文发版**：Release 标题与正文改为中文模板，`CHANGELOG.md` 为中文变更记录。

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
