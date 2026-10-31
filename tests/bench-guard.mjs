// 一次性基准：把 tab-guard.py 的 JS_TEMPLATE 拿出来，用假 gBrowser 跑 N 次，量单次注入成本。
// 用法：node F:/DSH/.tmp/efcf/tests/bench-guard.mjs
import { readFileSync } from 'node:fs'

const py = readFileSync(new URL('../scripts/tab-guard.py', import.meta.url), 'utf8')
const MARK = 'JS_TEMPLATE = r"""'
const start = py.indexOf(MARK) + MARK.length
const end = py.indexOf('"""', start)
const HOSTS = ['endfield.hypergryph.com']
const GAME = 'https://endfield.hypergryph.com/cloud'

const script = (action) =>
  py.slice(start, end)
    .replace('%(hosts)s', JSON.stringify(HOSTS))
    .replace('%(url)s', JSON.stringify(GAME))
    .replace('%(action)s', JSON.stringify(action))

const mkTab = (spec, pinned, label) => ({
  label,
  pinned,
  linkedBrowser: { currentURI: { spec } },
  url: spec,
})
const tabs = [
  mkTab(GAME, true, '云·终末地'),
  mkTab('about:blank', false, 'about:blank'),
  mkTab('https://example.com/', false, 'Example'),
]
const win = {}
const Services = { scriptSecurityManager: { getSystemPrincipal: () => ({}) } }
const gB = {
  tabs,
  selectedTab: tabs[0],
  removeTab() {},
  removeCurrentTab() {},
  pinTab() {},
  addTab() { return tabs[0] },
}

const body = script('watch')
const fn = new Function('gB', 'win', 'Services', 'return (function(){' + body + '})()')

// 预热
for (let i = 0; i < 200; i += 1) fn(gB, win, Services)

const N = 5000
const t0 = process.hrtime.bigint()
for (let i = 0; i < N; i += 1) fn(gB, win, Services)
const t1 = process.hrtime.bigint()
console.log('脚本字节:', Buffer.byteLength(body, 'utf8'))
console.log('单次执行均值:', (Number(t1 - t0) / N / 1e6).toFixed(3), 'ms')
console.log('每 3 秒一次 → 折算 CPU 占用约', (Number(t1 - t0) / N / 1e6 / 3000 * 100).toFixed(4), '%')
