# 公开发布检查清单

本仓库默认按“可直接公开”的干净历史准备：只包含源码、文档、profile、图标和构建脚本。
以下内容**不应**进入 git：

- `analysis/`：本机证据、截图、日志、官方美术素材
- `dist/`、`*.AppImage`：二进制走 GitHub Release
- `userdata/`、cookie、token、账号名、SteamID、`/home/<user>` 绝对路径
- 任何官方游戏美术/商标资源（见 `NOTICE`）

## 公开前

1. **许可证**：本项目原创代码使用 MIT（`LICENSE`）；`NOTICE` 已说明第三方商标/素材边界。
   如果未来合并上游 `RoderickEzreal/endfield-cloud-steamdeck` 的代码，先确认其许可证；
   上游当前没有声明许可证，不能默认继承。
2. **敏感信息扫描**：
   ```sh
   git grep -nE '/home/|/Users/|<steamid>|ghp_|github_pat_|DEEPSEEK|Bearer|token=' || true
   git status --short
   ```
3. **确认被忽略的私有目录没有入库**：
   ```sh
   git ls-files | grep -E '^(analysis|dist)/' && echo 'ERROR: private path tracked'
   ```
4. **构建与冒烟测试**：
   ```sh
   sh -n scripts/launch-firefox.sh
   sh -n scripts/build-firefox-appimage.sh
   sh -n firefox/appimage/AppRun
   sh scripts/build-firefox-appimage.sh
   DRY_RUN=1 sh scripts/launch-firefox.sh --windowed
   ```
5. **Release**：打 tag（例如 `v1.0.11`），让 `.github/workflows/release.yml`
   构建并附加 AppImage + `SHA256SUMS.txt`；私有仓库的 Release 仅对协作者可见。
6. **切换可见性**：确认 `git log` 里没有历史私有数据后，再在 GitHub Settings →
   General → Danger Zone 改为 Public；同时启用 Security advisories。
7. **公开后**：不要重写已公开的历史；补充 issue 模板/行为准则可按需再加。

## 私有仓库阶段

```sh
# 仅演示；实际仓库名以创建时为准
gh repo create endfield-cloud-firefox --private --source=. --remote=origin --push
gh release create v1.0.11 dist/endfield-cloud-firefox-1.0.11.AppImage \
  --title "Endfield Cloud (Firefox) v1.0.11" \
  --notes "Firefox/Gecko shell for Steam Deck. Requires Flatpak Firefox."
```
