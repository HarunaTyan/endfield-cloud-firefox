# Endfield Cloud for Steam Deck with Firefox

基于 Firefox/Gecko 实现的 Steam Deck《云·终末地》客户端

- 无须将整个浏览器添加为非 Steam 游戏，隐藏无关交互，保留极简。
- 程序本体不到 1 MB：调用系统已安装的 Flatpak 版本 Firefox。
- 锁住云游戏标签页：意外关闭后自动补回。

## 安装

> 已经装过 Firefox 的可以跳过第一步。
1. 安装 Firefox：

  ```sh
  flatpak install -y flathub org.mozilla.firefox
  ```

2. 从 [Releases](https://github.com/HarunaTyan/endfield-cloud-firefox/releases/latest) 下载 `.AppImage.tar.gz` 并解压（解压后自带执行权限）：

  ```sh
  cd ~/<目录>
  tar -xzf EndfieldCloud-*.AppImage.tar.gz
  ```

3. 桌面模式 → 库 → 添加非 Steam 游戏 → 选择 `~/<目录>/EndfieldCloud.AppImage`。

> 若安装完毕手柄无反应，请执行以下命令确保浏览器获取调用权限：

```sh
flatpak override --user --device=all org.mozilla.firefox
 ```
 
## 启动参数（可选）
- `--fullscreen` 全屏模式
  > 使 Firefox 以 kiosk 模式运行，以在桌面模式下隐藏浏览器边框。注意：请确保已在 Steam → 设置 → 控制器 → 非游戏控制器布局 下，事先设置过`Alt+Tab`或`Alt+F4`等作为应急按键，以免因误操作难以退出程序。

- `--focus` 专注模式
  > 拦截意外跳转，打开标签页时触发自动关闭并回到云·终末地。不影响充值、问卷、网页小游戏等内置行为。
  
## 常见问题

- **添加`.AppImage`后 从 Steam 启动没有反应？**

  Linux 下载的文件不带执行权限。可下载对应版本的 `.AppImage.tar.gz` 解压（包内已带权限），或在资源管理器中双击运行并点击**继续**。也可通过执行以下命令完成提权：
  ```sh
  cd ~/<目录>
  chmod +x EndfieldCloud.AppImage
  ```
  
- **文件名可以修改吗？**

  可以，但需同步修改在 Steam 中对应项目的 属性 → 快捷方式 → 目标 中记录的文件名。

- **为何位于 其他设备 / 平台 的 Steam 库中也出现了我在Steam Deck上添加的程序？**

  任何添加 / 修改路径的行为均可能触发库同步，请等待 Valve 官方修复。
  
- **卡在「正在检测网络环境」，或提示「连接服务器超时 / 网络连接异常」？**

  官方云游戏依赖 WebRTC 传输画面。先确认浏览器的 WebRTC 是否打开：进入`about:config` 输入 `media.peerconnection.enabled` ，设置为 `true`
  
- **不慎跳转其他网页后 如何回到云游戏？**

  设置 `Ctrl+1` 或 `Ctrl+Tab`的组合键后可切回云游戏标签页。`Ctrl+W` 可用于关闭误开的网页，且云游戏标签页本身无法关闭。或通过设置启动参数`--focus`进入专注模式。

- **我该如何更新？**

  从 [Releases](https://github.com/HarunaTyan/endfield-cloud-firefox/releases/latest) 下载新版本对应压缩包，解压覆盖到同一个 `~/<目录>/`，凡保持文件名不变即可确保 Steam 处不用调整。若选择下载`.AppImage`，仍需手动进行一次提权，详情见常见问题第一条。

- **桌面模式下进游戏，为何是移动端界面？**

  官方云游戏启动类型由用户在启动页面点击「开始游戏」时的输入类型决定：
  - 鼠标行为 分配至 端游客户端（可切换键鼠/手柄）
  - 触摸行为 分配至 移动端客户端（固定触摸屏）
  
  该判定只会处理一次。
  
  因此，若想在桌面模式体验键鼠/手柄操作，**请务必以触控板 / 鼠标 点击最初的 「开始游戏」**。

## 声明

本项目为非官方项目，与鹰角网络（Hypergryph）不存在隶属或授权关系。

## 许可

本项目代码以 MIT 许可发布，条款见 [`LICENSE`](LICENSE)。
