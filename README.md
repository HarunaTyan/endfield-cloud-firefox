# Endfield Cloud for Steam Deck with Firefox

基于 Firefox/Gecko 实现的 Steam Deck《云·终末地》客户端

- 无须将整个浏览器添加为 非 Steam 游戏，隐藏无关交互，保留极简。
- 程序本体不到 1 MB：调用系统已安装的 Flatpak 版本 Firefox。
- 锁住云游戏标签页：意外关闭后自动补回。

## 安装

> 已经装过 Firefox 的可以跳过第一步。若安装完毕手柄无反应，见「常见问题」最后一条。
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

## 启动参数（可选）
- `--fullscreen` 全屏模式
  > 使 Firefox 以 kiosk 模式运行，以在桌面模式下隐藏浏览器边框。但请确保自己在 Steam → 设置 → 控制器 → 非游戏控制器布局 下，事先设置过`Alt+Tab`或`Alt+F4`等作为应急按键，以免因误操作导致难以退出。

- `--focus` 专注模式
  > 拦截意外跳转，打开标签页时触发自动关闭并回到云·终末地。
  

## 常见问题

- **添加`.AppImage`后 从 Steam 启动没有反应？**

  Linux 下载的文件不带执行权限。改用同版本的 `.AppImage.tar.gz` 解压（包内已带权限），或在双击提示中确认允许执行一次。

- **不慎跳转其他网页后 如何回到云游戏？**

  设置 `Ctrl+1` 或 `Ctrl+Tab`的组合键后可切回云游戏标签页。`Ctrl+W` 可用于关闭误开的网页，且云游戏标签页本身无法关闭。或可以设置启动参数`--focus`

- **文件名可以修改吗？**

  可以，但需同步在 Steam 中修改 属性 → 快捷方式 → 目标 中记录的文件名。

- **为何位于 其他设备 / 平台 的 Steam 库中也出现了我在Steam Deck上添加的程序？**

  任何添加 / 修改路径的行为均可能触发库同步，请等待 Valve 官方修复。

- **我该如何更新？**

  从 [Releases](https://github.com/HarunaTyan/endfield-cloud-firefox/releases/latest) 下载新版本，解压覆盖到同一个 `~/<目录>/`，保持文件名不变，Steam 条目不用改。

- **进了游戏，但手柄没有反应？**

  请运行以下命令，确保浏览器获取设备调用权限：

  ```sh
  flatpak override --user --device=all org.mozilla.firefox
  ```

## 声明

本项目为非官方项目，与鹰角网络（Hypergryph）不存在隶属或授权关系。

## 许可

本项目代码以 MIT 许可发布，条款见 [`LICENSE`](LICENSE)。
