# Endfield Cloud for Steam Deck with Firefox

基于 Firefox/Gecko 实现的 Steam Deck《云·终末地》客户端。

## 安装

1. 安装 Firefox：

```sh
flatpak install -y flathub org.mozilla.firefox
```

2. 从 [Releases](https://github.com/HarunaTyan/endfield-cloud-firefox/releases/latest) 下载 `.AppImage`，双击一次并确认允许执行。

3. 桌面模式 → 库 → 添加非 Steam 游戏 → 选择该 `.AppImage`。

## 常见问题

**打开其他网页后，怎么切回云游戏？**
把某个按键绑定 `Ctrl+1`，按下即回到云游戏标签页；误开的网页按 `Ctrl+W` 关闭，云游戏标签页本身关不掉。

**升级怎么办？**
下载新版本，替换同一个文件后重新运行。

## 声明

本项目为非官方项目，与鹰角网络（Hypergryph）不存在隶属或授权关系。

## 许可

本项目代码以 MIT 许可发布，条款见 [`LICENSE`](LICENSE)。
