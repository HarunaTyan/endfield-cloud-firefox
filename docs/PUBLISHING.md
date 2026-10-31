# 公开发布检查清单

本仓库按「可直接公开」的干净历史准备：只包含源码、文档、profile、图标和构建脚本。
以下内容**不应**进入 git：

- `analysis/`：本机证据、截图、日志、官方美术素材
- `dist/`、`build/`、`*.AppImage`：二进制走 GitHub Release
- `userdata/`、cookie、token、账号名、SteamID、`/home/<user>` 绝对路径
- 任何官方游戏美术/商标资源（见 `NOTICE`）

## 发版语言

**Release 标题与说明一律用中文**（面向国服玩家）。已经发布过的英文说明要就地改成中文，
不要留着中英混排的旧文案。`.github/workflows/release.yml` 里的 `body` 是中文模板；
每次发版前把「本次改动」写进 `CHANGELOG.md`，Release 正文再指向对应 tag 的 CHANGELOG。

## 公开前

1. **许可证**：本项目原创代码使用 MIT（`LICENSE`）；`NOTICE` 说明了第三方商标/素材边界
   （含中文摘要）。本仓库不含任何上游项目的代码或素材，因此不继承、也不需要合并其他项目的许可。
2. **敏感信息扫描**：
   ```sh
   git grep -nE '/home/|/Users/|<steamid>|ghp_|github_pat_|Bearer|token=' || true
   git status --short
   ```
3. **确认被忽略的私有目录没有入库**：
   ```sh
   git ls-files | grep -E '^(analysis|dist|build)/' && echo 'ERROR: private path tracked'
   ```
4. **构建与冒烟测试**：
   ```sh
   sh -n scripts/launch-firefox.sh
   sh -n scripts/build-firefox-appimage.sh
   sh -n firefox/appimage/AppRun
   python3 -m py_compile scripts/tab-guard.py scripts/steam-shortcut.py
   sh scripts/build-firefox-appimage.sh
   DRY_RUN=1 sh scripts/launch-firefox.sh --windowed
   ```
5. **Release**：打 tag（例如 `v1.0.12`），让 `.github/workflows/release.yml`
   构建并附加 AppImage + `SHA256SUMS.txt`；私有仓库的 Release 仅对协作者可见。
6. **切换可见性**：确认 `git log` 里没有历史私有数据后，再在 GitHub Settings →
   General → Danger Zone 改为 Public；同时启用 Security advisories。
7. **公开后**：不要重写已公开的历史；补充 issue 模板/行为准则可按需再加。

## 私有仓库阶段

```sh
# 仅演示；实际仓库名以创建时为准
gh repo create endfield-cloud-firefox --private --source=. --remote=origin --push
gh release create v1.0.12 dist/endfield-cloud-firefox-1.0.12.AppImage \
  --title "云·终末地 · Firefox 外壳 v1.0.12" \
  --notes-file CHANGELOG.md
```
