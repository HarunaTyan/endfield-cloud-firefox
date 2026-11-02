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

**打开其他网页后，怎么切回云游戏？**
把某个按键绑定 `Ctrl+1`，按下即回到云游戏标签页；误开的网页按 `Ctrl+W` 关闭，云游戏标签页本身关不掉。

**刚下载的 `.AppImage` 双击没反应，或从 Steam 启动失败？**
Linux 下载来的文件不带执行权限。改用同一版本的 `.AppImage.tar.gz` 解压（包内已带权限），
或双击一次 `.AppImage`，在提示里选择继续。

**已经用别的文件名加进 Steam 了，升级后会不会变成另一款游戏？**
会。改成固定路径 `~/Applications/EndfieldCloud.AppImage` 再指向它一次，之后升级只替换内容。

**升级怎么办？**
下载新版本，解压覆盖 `~/Applications/EndfieldCloud.AppImage` 后重新运行。

## 声明

本项目为非官方项目，与鹰角网络（Hypergryph）不存在隶属或授权关系。

## 许可

本项目代码以 MIT 许可发布，条款见 [`LICENSE`](LICENSE)。
