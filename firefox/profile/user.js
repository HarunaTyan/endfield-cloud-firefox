// 云·终末地 · Firefox profile prefs（云游戏方向）
// 所有 pref 名均已对本机 Firefox 158.0 (Flatpak) 的 libxul.so / greprefs.js /
// firefox.js 做过字符串核对（2026-10-20）；被移除的 pref 以注释保留并说明。
// user.js 在每次启动时覆盖 prefs.js 中的同名项；Firefox 退出时会把值写回 prefs.js。

// ==== 硬件解码 / 渲染 ====
// 注意：media.ffmpeg.vaapi.enabled 在 Firefox 158 已不存在（VA-API 默认启用且
// pref 被 Mozilla 移除，libxul.so 中已无此字符串）。无需也无法设置。
// 158 仍存在的相关开关：media.rdd-ffmpeg.enabled（RDD 解码进程，默认开）。
user_pref("media.hardware-video-decoding.enabled", true);
user_pref("media.hardware-video-decoding.force-enabled", true);
user_pref("gfx.webrender.all", true);
// 谨慎项：个别驱动下强制加速层可能导致崩溃。若启动黑屏/崩溃，先注释这一行。
user_pref("layers.acceleration.force-enabled", true);

// ==== WebRTC（云游戏串流依赖）====
user_pref("media.peerconnection.enabled", true);
user_pref("media.navigator.enabled", true);
// 硬件 H.264 编码（WebRTC 路径）。软件 H.264 解码路径的
// media.webrtc.h264.enabled 在 158 中不存在（已并入 ffmpeg 默认行为）。
user_pref("media.webrtc.hw.h264.enabled", true);

// ==== WebCodecs / WebTransport ====
// 两者均已核对存在于 158。WebTransport 默认即 true；显式写以自证。
user_pref("dom.media.webcodecs.enabled", true);
user_pref("network.webtransport.enabled", true);

// ==== 手柄 ====
user_pref("dom.gamepad.enabled", true);
user_pref("dom.gamepad.extensions.enabled", true);
user_pref("dom.gamepad.haptic_feedback.enabled", true);
// Steam Deck 手柄在 Firefox 中以标准 Gamepad API 暴露；震动走 haptic feedback。

// ==== 自动播放 / 全屏 ====
user_pref("media.autoplay.default", 0);
user_pref("media.autoplay.blocking_policy", 0);
user_pref("full-screen-api.allow-trusted-requests-only", false);
// 全屏警告横幅停留时间(ms)。0 = 立即消失（仍会短暂渲染）。
user_pref("full-screen-api.warning.timeout", 0);
user_pref("full-screen-api.keyboardlock-warning.timeout", 0);
user_pref("pointer-lock-api.warning.timeout", 0);

// ==== 去 UI / 去干扰（窗口化模式；kiosk 模式不依赖这些）====
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);
user_pref("browser.tabs.inTitlebar", 0);
user_pref("browser.uidensity", 1);
user_pref("browser.toolbars.bookmarks.visibility", "never");
user_pref("browser.newtabpage.enabled", false);
// 云游戏就是主页：启动只开这一个标签；关掉最后一个标签也不会退出浏览器，
// 新开出来的空标签由守护装回主页 —— 保证「没手动钉标签时永远只有一个标签页」。
user_pref("browser.startup.page", 1);
user_pref("browser.startup.homepage", "https://endfield.hypergryph.com/cloud");

// ==== 屏蔽一批「能把这台机器搞坏」的快捷键 ====
// Alt（以及 F10）不再唤出菜单栏：菜单里能开附加组件、开发者工具、清数据。
user_pref("ui.key.menuAccessKey", 0);
// Alt+字母 的菜单访问键一并关掉（chrome = 界面层，content = 网页里）。
user_pref("ui.key.chromeAccess", 0);
user_pref("ui.key.contentAccess", 0);
// 工具栏的键盘遍历（Tab 落在按钮上）关掉，焦点只留给页面。
user_pref("browser.toolbars.keyboard_navigation", false);

// ==== 标签页：切换 / 关闭 / 防误关 ====
// 快捷键由 Firefox 原生处理，锁定由启动器拉起的 scripts/tab-guard.py 负责；
// 这里只放让原生行为更安全的开关。
// 关掉最后一个标签不连窗口一起关：误按 Ctrl+W 不会把整个 shell 关掉。
user_pref("browser.tabs.closeWindowWithLastTab", false);
// 页面里点开的链接在后台打开：云游戏标签页不会被抢走聚焦，误触时画面不中断。
user_pref("browser.tabs.loadInBackground", true);
// 会话恢复时立刻加载每个标签，不懒加载：懒加载的标签 URL 还是 about:blank，
// 守护脚本会误判「云游戏页不在」而再开一页，用户就看到两个同样的网页。
// 升级后别弹「新特性」标签、首次运行别弹欢迎页，否则启动就多一个标签
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("browser.aboutwelcome.enabled", false);
user_pref("browser.sessionstore.restore_on_demand", false);
// 多标签时关窗要确认（Steam「退出游戏」走信号，不受影响）。
user_pref("browser.tabs.warnOnClose", true);
user_pref("browser.tabs.warnOnCloseOtherTabs", true);
// Ctrl+Shift+T 的后悔药数量。
user_pref("browser.sessionstore.max_tabs_undo", 12);
user_pref("browser.sessionstore.max_windows_undo", 3);
// Ctrl+Tab 按标签顺序走而不是按最近使用，位置可预期。
user_pref("browser.ctrlTab.sortByRecentlyUsed", false);

// ==== 遥测 / 检查 / 恢复 / 杂项 ====
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("toolkit.telemetry.enabled", false);
user_pref("app.shield.optoutstudies.enabled", false);
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.sessionstore.resume_from_crash", false);
user_pref("extensions.pocket.enabled", false);
user_pref("identity.fxaccounts.enabled", false);

// ==== Cookie：云游戏登录需要持久会话 ====
// 0 = 接受全部 cookie（含第三方）。选 0 而不是 5（仅同站）的原因：
// 串流/登录链路可能跨域下发会话 cookie，ETP 严格/同站限制会导致掉登录。
// 风险：第三方跟踪 cookie 也会被保留——这是专用游戏 shell profile，可接受。
user_pref("network.cookie.cookieBehavior", 0);
// 不开 ETP 严格模式（默认平衡即可；严格模式会打断部分串流 CDN）
user_pref("privacy.trackingprotection.enabled", false);
