# 安全

本项目是一个很薄的浏览器启动器：不做认证、不代理流量、不实现游戏逻辑，
这些都交给官方网页和用户自己安装的 Flatpak Firefox。

## 提 issue / 报漏洞

- 不要在公开 issue 里贴账号凭据、cookie、可被利用的细节。
- 发现安全问题时用本仓库的私有安全通告：Security → Advisories → New draft advisory。
- AppImage 只从本仓库的 Releases 页面下载，并核对随附的 SHA-256。

## 入库纪律

不要把下面这些东西提交进仓库：

- cookie、token、账号名、SteamID
- Steam `userdata/`、`shortcuts.vdf`
- 含账号信息的截图
- 本机绝对路径（`/home/<user>`、`/Users/<user>`）

## 万一敏感信息已经提交

顺序不能颠倒，先做第 1 条再做后面的：

1. **先轮换**：token、密码、密钥只要进过一次 git，就当作已经泄露 —— 立刻到对应平台撤销重发。
   清理历史可以慢慢来，撤销凭据不能等。
2. **再清理**：`git rm` 加一个新 commit 只改了 HEAD，老内容仍在历史里（`git log -p`、GitHub 提交页
   都能翻到）。要真删得用 `git filter-repo`（或 BFG）重写历史并强制推送；必要时联系 GitHub 支持
   清理缓存。强推只让旧提交变成「不可达」，不等于立刻从服务器上抹掉。
3. **已经公开过的**：假定有人在 fork、CDN 缓存、GitHub Archive 里留了副本，
   重写历史只能挡住后来的查看者，挡不住已经拿到的人。
4. **本项目的正确做法**是别让它进 git：`.gitignore` 挡住 `dist/`、`build/`、日志、cookie；
   发布前跑 `docs/PUBLISHING.md` 里的**工作区 + 全历史**两段扫描。

## 关于提交历史本身

- 仓库现在是私有的：历史只有你和被邀请的协作者能看到，切 Public 的一瞬间**全部历史**一起公开。
- 历史是工作日志，不是宣传册：先写后改留下的痕迹属于正常开发过程；对外呈现以 README / CHANGELOG 为准。
- 真要一份干净历史，只能在**还没公开**的时候重写（重写会改变 commit SHA，需要重建 tag 与 Release）。

## 标签页守护的边界

`scripts/tab-guard.py` 通过 Firefox 内置的 Marionette 协议工作，端口只监听 `127.0.0.1`：

- 只在本游戏启动期间开启，Firefox 退出即断开；
- 只调用 `gBrowser` 的标签页相关接口，不注入页面脚本、不读 cookie、不改登录态；
- 仍是「本机任意进程可连」的本地信任模型。不需要这层能力就用 `ENDFIELD_TAB_GUARD=0` 启动，
  此时启动器不会给 Firefox 加 `--marionette`，端口根本不会开。
