# 图标资源说明

## 现状

`resources/icons/` 包含 `256x256.png`、`512x512.png`；源文件是 `resources/icon.svg`。

Firefox AppImage 只打包 **512x512.png**（`scripts/build-firefox-appimage.sh` 使用），其余尺寸留给桌面/Steam 手动替换。

## 替换图标

用同名 PNG 覆盖即可；重新打包：

```bash
cd endfield-cloud-firefox
sh scripts/build-firefox-appimage.sh
```

## 版权

`icon.svg` 为本项目原创几何图标，不含官方角色或徽标。
