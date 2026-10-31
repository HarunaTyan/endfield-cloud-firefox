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

## 标签页守护的边界

`scripts/tab-guard.py` 通过 Firefox 内置的 Marionette 协议工作，端口只监听 `127.0.0.1`：

- 只在本游戏启动期间开启，Firefox 退出即断开；
- 只调用 `gBrowser` 的标签页相关接口，不注入页面脚本、不读 cookie、不改登录态；
- 仍是「本机任意进程可连」的本地信任模型。不需要这层能力就用 `ENDFIELD_TAB_GUARD=0` 启动，
  此时启动器不会给 Firefox 加 `--marionette`，端口根本不会开。
