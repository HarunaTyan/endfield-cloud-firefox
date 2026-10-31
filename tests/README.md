# 离线回归测试

两个测试都不需要 Steam Deck、不需要 Flatpak、不需要真的 Firefox，用来在改代码后先自查一遍。

## 1. 守护的浏览器侧逻辑

```sh
node tests/tab-guard-logic.mjs
```

直接从 `scripts/tab-guard.py` 里取出注入浏览器的 JS，塞进一个假的 tabbrowser 运行，断言：

- 云游戏标签页被 `pinTab`；
- `removeTab` / `removeCurrentTab` 打到云游戏标签上被拦下，打到别的标签上照常关闭；
- 云游戏标签页消失时会 `addTab` 重建、固定并切回；
- `--list` 是只读的（不建标签、不打补丁、不动选中）；
- `--close-strays` 只留云游戏标签；
- 没有浏览器窗口时不抛异常。

只依赖 Node（CI 的 ubuntu-latest 自带）。

## 2. Marionette 通信层

```sh
python3 tests/marionette-mock.py 2928 -v &
python3 scripts/tab-guard.py --port 2928 --list
python3 scripts/tab-guard.py --port 2928 --once
```

桩按 Marionette 协议回包（握手 `{"applicationType":"gecko","marionetteProtocol":3}`、
命令帧 `[0, id, 命令名, 参数]`、响应帧 `[1, id, error, result]`），用来确认守护脚本的
分帧、握手、`WebDriver:SetContext(chrome)`、`WebDriver:ExecuteScript(sandbox=system)` 序列没写错。

**它验证不了**：Firefox 实际会不会接受这些命令、`gBrowser` 行为是否如预期 ——
那部分要在机器上用 `python3 scripts/tab-guard.py --list` 自测（见 `docs/tabs-and-gamepad.md`）。

## 3. 启动器

```sh
sh -n scripts/launch-firefox.sh
sh -n firefox/appimage/AppRun
DRY_RUN=1 sh scripts/launch-firefox.sh --windowed
```

`DRY_RUN=1` 只打印最终命令、不启动、也不拉起守护。
