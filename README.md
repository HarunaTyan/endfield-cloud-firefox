# Endfield Cloud for Steam Deck with Firefox

基于 Firefox/Gecko 实现的 Steam Deck《云·终末地》客户端。

## 安装

1. 安装 Firefox：

```sh
flatpak install -y flathub org.mozilla.firefox
```

2. 从 [Releases](https://github.com/HarunaTyan/endfield-cloud-firefox/releases/latest) 下载 `.AppImage.tar.gz` 并解压（解压后自带执行权限）：

```sh
mkdir -p ~/Applications
tar -xzf EndfieldCloud-*.AppImage.tar.gz -C ~/Applications
```

3. 桌面模式 → 库 → 添加非 Steam 游戏 → 选择 `~/Applications/EndfieldCloud.AppImage`。
之后升级只替换这个文件，Steam 条目不用动。

## 常见问题

- **不慎跳转其他网页后如何回到云游戏？**

  绑定了 `Ctrl+1` 的按键可切回云游戏标签页。`Ctrl+W` 用于关闭误开的网页，云游戏标签页本身无法关闭。

- **`.AppImage` 双击或从 Steam 启动没有反应**

  Linux 下载的文件不带执行权限。改用同版本的 `.AppImage.tar.gz` 解压（包内已带权限），或在提示中确认允许执行一次。

- **文件名可以修改吗？**

  可以，但 Steam 按路径与文件名识别游戏，改动后会成为另一款游戏，手柄布局需要重新配置。建议固定为 `~/Applications/EndfieldCloud.AppImage` 后再添加。

- **如何以全屏运行**

  在启动项末尾追加 `--fullscreen`，Firefox 以 kiosk 模式启动，无窗口边框与浏览器界面。退出使用 `Alt+F4`；该模式下 Steam 覆盖层仍显示在最上层。

- **如何升级**

  下载新版本，覆盖 `~/Applications/EndfieldCloud.AppImage` 后重新运行。

## 声明

本项目为非官方项目，与鹰角网络（Hypergryph）不存在隶属或授权关系。

## 许可

本项目代码以 MIT 许可发布，条款见 [`LICENSE`](LICENSE)。
