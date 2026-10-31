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

## 发版流程（tag 之后必须补中文说明）

`.github/workflows/release.yml` 只负责构建 AppImage 与上传资产，用的是 GitHub 的
Auto-generated notes —— 固定小节名（`What's Changed` / `Full Changelog`）由 GitHub 决定，改不了成中文。
所以流程是「CI 出资产，人补中文正文」：

```sh
V=v1.0.12
git tag -a "$V" -m "云·终末地 · Firefox 外壳 $V"
git push origin "$V"
gh run watch --exit-status          # 等 CI 打包并上传
# 从 CHANGELOG 摘出该版本，写成中文正文后覆盖：
gh release edit "$V" --title "云·终末地 · Firefox 外壳 $V" --notes-file notes.md
```

想连 workflow 里的中文模板也生效，需要给 gh 的 token 加 `workflow` 权限
（`gh auth refresh -s workflow`）；加之前改 `.github/workflows/*` 会被 GitHub 直接拒绝推送
（`refusing to allow an OAuth App to create or update workflow`）。`.github/release.yml`
只是自动说明的分类配置，不属于 workflow，可以正常提交。

## 公开前

1. **许可证**：本项目原创代码使用 MIT（`LICENSE`）；`NOTICE` 说明了第三方商标/素材边界
   （含中文摘要）。本仓库不含任何上游项目的代码或素材，因此不继承、也不需要合并其他项目的许可。
2. **敏感信息扫描**（工作区 + **全部历史**，两步都要跑）：

   ```sh
   # 只看当前文件
   git grep -nE '/home/|/Users/|<steamid>|ghp_|github_pat_|Bearer|token=' || true
   git status --short

   # 历史里也要扫：删掉的提交不等于消失，任何人翻 git log 都看得到
   git log --all -p | grep -nE '/home/[a-z]|/Users/[A-Za-z]|ghp_[A-Za-z0-9]{20,}|Bearer [A-Za-z0-9]|token=[A-Za-z0-9]{8,}'
   ```
   
   > 历史扫描这一步是补的教训：把敏感内容 `git rm` 再提交一个新 commit，**只改了 HEAD**，
   > 老内容仍然留在历史里，`git log -p` 或 GitHub 的提交页都能翻到。
   > 真正删掉要重写历史（见 `SECURITY.md`「万一敏感信息已经提交」）。
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
