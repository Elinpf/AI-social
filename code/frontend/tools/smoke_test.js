#!/usr/bin/env node
/* smoke_test.js — 无浏览器环境下的前端自检（Node）。
 *
 * 覆盖两层：
 *   A. replay 逻辑：用真实样例日志折叠状态，验证「按回合能看到 Agent 移动」、
 *      事实/事件流/气泡可生成；
 *   B. 渲染代码路径：用最小 PIXI mock 跑 sprites/town/audit 的构造与逐回合渲染，
 *      确认无运行时异常、场所/角色精灵按预期创建。
 *
 * 说明：本机若无 Chrome，无法做真实浏览器 WebGL 截图；本脚本作为等价的可复现门禁，
 *      需要真实像素渲染时请用 tools/serve.py + 浏览器人工查看。
 *
 * 用法：
 *   cd code && node frontend/tools/smoke_test.js
 *   cd code && node frontend/tools/smoke_test.js --selftest-render-only
 */
"use strict";
const fs = require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "..");

let failures = 0;
function check(cond, msg) { if (cond) { console.log("  ok  - " + msg); } else { failures++; console.error("  FAIL- " + msg); } }

// ---------- 公用：最小 PIXI mock ----------
function installPixiMock() {
  class C {
    constructor() { this.children = []; this.x = 0; this.y = 0; this.style = {}; this.anchor = { set() {} }; this.scale = { set() {} }; }
    addChild(c) { this.children.push(c); return c; }
    removeChild(c) { this.children = this.children.filter((x) => x !== c); return c; }
  }
  class Graphics extends C {
    beginFill() { return this; } endFill() { return this; } lineStyle() { return this; }
    drawRect() { return this; } drawRoundedRect() { return this; } drawCircle() { return this; }
    drawEllipse() { return this; } moveTo() { return this; } lineTo() { return this; } clear() { return this; }
  }
  class Text extends C { constructor(t, s) { super(); this.text = t; this.style = s || {}; this.anchor = { set() {} }; } destroy() {} }
  class Sprite extends C { constructor(tex) { super(); this.texture = tex; this.tint = 0xffffff; } }
  class Texture { constructor(base, rect) { this.base = base; this.rect = rect; } }
  class BaseTexture {}
  class Rectangle { constructor(x, y, w, h) { this.x = x; this.y = y; this.width = w; this.height = h; } }
  class Application { constructor() { this.view = { style: {} }; this.stage = new C(); this.ticker = { add() {} }; } }
  global.window = global;
  global.Image = class { set src(v) { this._src = v; if (this.onload) this.onload(); } };
  global.PIXI = {
    Application, Container: C, Graphics, Text, Sprite, Texture, Rectangle,
    BaseTexture: { from: () => new BaseTexture() },
    Assets: { load: async () => new BaseTexture() },
  };
}

function loadModules() {
  require(path.join(ROOT, "src/data.js"));
  require(path.join(ROOT, "src/sprites.js"));
  require(path.join(ROOT, "src/town.js"));
  require(path.join(ROOT, "src/replay.js"));
  require(path.join(ROOT, "src/audit.js"));
}

function replayOf(file) {
  const recs = global.HITTData.parseJSONL(fs.readFileSync(path.join(ROOT, file), "utf8"));
  return new global.HITTReplay.Replay(recs);
}

function testA() {
  console.log("\n[A] replay 逻辑");
  const demo = replayOf("sample/demo_run.jsonl");
  const ids = Object.keys(demo.snapshots[demo.maxRound]);
  const movers = ids.filter((id) => new Set(demo.rounds.map((r) => (demo.snapshots[r][id] || {}).location)).size > 1);
  check(demo.records.length > 0, "demo 日志解析 " + demo.records.length + " 条");
  check(movers.length >= 1, "demo 有 " + movers.length + " 个 Agent 跨回合改变场所（可见移动）");
  const bubbleRound = demo.rounds.find((r) => Object.values(demo.displayState(r).agents).some((a) => a.bubble));
  check(bubbleRound != null, "存在带头顶气泡的回合（活动提示）");
  const f = demo.facts[demo.maxRound];
  check(f.alive === f.total && f.total === 3, "事实存活 3/3");

  const eng = replayOf("sample/engine_run_seed12345_r20.jsonl");
  check(Object.keys(eng.snapshots[eng.maxRound]).length === 3, "engine 样例 3 个 Agent");
  check(eng.facts[eng.maxRound].moneySupply === 30000, "engine 样例货币总量取 TURN_SEAL=30000");
}

async function testB() {
  console.log("\n[B] 渲染代码路径（PIXI mock）");
  installPixiMock();
  loadModules();
  const places = JSON.parse(fs.readFileSync(path.join(ROOT, "data/places.json"))).places;
  const topo = JSON.parse(fs.readFileSync(path.join(ROOT, "data/topology.json")));
  const town = new global.HITTTown.Town({ appendChild() {} }, places, topo);
  await town.load("assets/");
  check(town.placeLayer.children.length === places.length, "场所精灵 " + town.placeLayer.children.length + "/" + places.length);
  check(town._kindGrid && town._kindGrid.length > 0, "地形 tile 网格已构建（" + town._cols + "x" + town._rows + "）");
  check(town.groundLayer.children.length >= 3, "ground 层含 背景+地形+装饰（" + town.groundLayer.children.length + " 组）");
  // 图层顺序：地面必须在场所/角色之下（否则地面会盖住小镇）
  const order = town.worldLayer.children;
  check(order[0] === town.groundLayer && order.indexOf(town.placeLayer) > order.indexOf(town.groundLayer)
    && order.indexOf(town.agentLayer) > order.indexOf(town.placeLayer), "图层顺序 ground < place < agent");

  const rp = replayOf("sample/demo_run.jsonl");
  let maxAgents = 0;
  for (const r of rp.rounds) { town.renderState(rp.displayState(r)); town.tick(); maxAgents = Math.max(maxAgents, Object.keys(town.agents).length); }
  check(maxAgents === 3, "角色精灵 " + maxAgents + " 个（逐回合渲染无异常）");

  const el = () => ({ innerHTML: "", textContent: "", scrollTop: 0, querySelectorAll: () => [] });
  const kf = el(), st = el(), cnt = el();
  const audit = new global.HITTAudit.Audit(kf, st, cnt);
  audit.renderFacts(rp, rp.maxRound);
  audit.renderStream(rp, 0);
  check(/kfact/.test(kf.innerHTML), "审计台 K 类事实已渲染");
  check(st.innerHTML.length > 0, "事件流已渲染（与「本回合事件」统计同口径）");

  // 挂钟时间口径（1 tick = 2h，纯展示）
  const w0 = global.HITTReplay.wallClock(0), w1 = global.HITTReplay.wallClock(1);
  const w3 = global.HITTReplay.wallClock(3), w6 = global.HITTReplay.wallClock(6), w9 = global.HITTReplay.wallClock(9);
  check(w0.hhmm === "06:00" && w0.slotName === "早晨", "round0 → 06:00 早晨");
  check(w1.hhmm === "08:00", "round1 → 08:00（每 tick +2h）");
  check(w3.hhmm === "12:00" && w6.hhmm === "18:00" && w9.hhmm === "00:00", "round 3/6/9 → 12:00/18:00/00:00");
  check(global.HITTReplay.wallClock(12).day === 2, "round12 → 第 2 日（12 tick/日）");
}

function testC() {
  console.log("\n[C] 静态帧 SVG 导出（无浏览器门禁）");
  const { spawnSync } = require("child_process");
  const os = require("os");
  const out = path.join(os.tmpdir(), "hitt_smoke_snapshot.svg");
  const script = path.join(ROOT, "tools", "render_svg.py");
  const r = spawnSync("python3", [script, "--log", path.join(ROOT, "sample/demo_run.jsonl"),
    "--round", "12", "--out", out], { encoding: "utf8" });
  if (r.error) { check(false, "调用 python3 render_svg.py 失败: " + r.error.message); return; }
  check(r.status === 0, "render_svg.py 退出码 0（stderr: " + (r.stderr || "").trim() + "）");
  let svg = "";
  try { svg = fs.readFileSync(out, "utf8"); } catch (e) { check(false, "未生成 SVG: " + e.message); return; }
  check(svg.length > 2000, "SVG 非空（" + svg.length + " bytes）");
  check(/^<svg[\s>]/.test(svg.trim()) && svg.trim().endsWith("</svg>"), "是自包含 <svg> 根元素");
  check(!/https?:\/\//.test(svg.replace(/xmlns="[^"]*"/g, "")), "无外部 http(s) 引用（自包含）");
  check((svg.match(/class="place"/g) || []).length === 17, "含 17 个场所元素");
  // demo_run round12 的存活 Agent 数（与 replay 折叠一致）
  const rp = replayOf("sample/demo_run.jsonl");
  const nAgents = Object.keys(rp.snapshots[12] || rp.snapshots[rp.maxRound]).length;
  check((svg.match(/class="agent"/g) || []).length === nAgents, "含当前回合 Agent 数 = " + nAgents);
  check(/log_hash/.test(svg), "页脚含 log_hash（确定性重绘声明）");
}

function testD() {
  console.log("\n[D] 无头渲染 CPU 优化（still 模式 / 截图脚本）");
  const sh = fs.readFileSync(path.join(ROOT, "tools", "screenshot.sh"), "utf8");
  check(/still=1/.test(sh), "screenshot.sh 使用 still=1");
  check(/flock/.test(sh), "screenshot.sh 串行（flock 互斥）");
  check(/pkill .*chrome/.test(sh), "screenshot.sh 退出清理残留进程");
  check(/shot\.py/.test(sh), "screenshot.sh 委托 shot.py（等就绪）");
  // T121：截图等就绪、超时非零、防"假黑图"
  const shot = fs.readFileSync(path.join(ROOT, "tools", "shot.py"), "utf8");
  check(/__RENDER_READY__/.test(shot) && /wait_for_function/.test(shot), "shot.py 等 __RENDER_READY__（不用固定 sleep）");
  check(/return 1/.test(shot) && /超时/.test(shot), "shot.py 等不到就绪 → 非零退出（不产黑图）");
  check(/--force-device-scale-factor=1|device_scale_factor=1/.test(shot) && /enable-webgl|swiftshader/.test(shot), "shot.py 关键 flags 齐全");
  check(/假黑图|false negative/.test(shot), "shot.py 注释记录已知坑（大日志假黑图）");
  check(/_mean_brightness/.test(shot) && /601/.test(shot), "shot.py 定义 mean_brightness 口径（灰度 601，防同名不同义）");
  const main = fs.readFileSync(path.join(ROOT, "src", "main.js"), "utf8");
  check(/__RENDER_READY__/.test(main), "main.js 置 __RENDER_READY__");
  check(/data-render-ready/.test(main), "main.js 置 data-render-ready 属性");
  check(/visibilitychange/.test(main), "main.js 后台标签页停 rAF");
  check(/setLighting/.test(main), "main.js 调用 town.setLighting（与 art-director 光照 API 对齐）");
  // T75：live 跟随模式
  check(/startLive/.test(main) && /state\.live/.test(main), "main.js 有 live 跟随模式");
  check(/__RENDER_READY__/.test(main), "main.js 置 __RENDER_READY__");
  check(fs.existsSync(path.join(ROOT, "tools", "live_run.py")), "tools/live_run.py 存在");
  check(/run_round/.test(fs.readFileSync(path.join(ROOT, "tools", "live_run.py"), "utf8")), "live_run.py 逐回合推进（run_round）");
}

function testE() {
  console.log("\n[E] 观测台重做（T77：人话/因果/角色卡/中文化）");
  const recs = global.HITTData.parseJSONL(fs.readFileSync(path.join(ROOT, "sample/tiny_lifecycle.jsonl"), "utf8"));
  const ctx = { name: (x) => x, place: (x) => x || "" };
  let leaks = 0;
  recs.forEach((e) => { if (/undefined|「」/.test(global.HITTReplay.humanize(e, ctx).text)) leaks++; });
  check(leaks === 0, "humanize 无 undefined/空引号 泄漏（" + recs.length + " 事件）");
  const died = global.HITTReplay.humanize(recs.find((e) => e.type === "AGENT_DIED"), ctx);
  check(/去世了/.test(died.text) && /原因/.test(died.text), "AGENT_DIED 含「为什么（原因）」");
  const audit = fs.readFileSync(path.join(ROOT, "src", "audit.js"), "utf8");
  check(/_iconHtml/.test(audit) && /ICON_ATLAS/.test(audit), "图标有像素图集升级钩子（ICON_ATLAS 单一真源）");
  check(/_focusSeq/.test(audit) && /scrollIntoView/.test(audit), "因果跳转后定位/高亮源事件");
  const html = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");
  check(/id="ev-level"/.test(html) && /id="ev-search"/.test(html) && /id="ev-audit"/.test(html), "编年史筛选栏（层级/搜索/审计模式）");
  check(/id="insp-body"/.test(html), "角色卡抽屉存在");
  // 中文化：main.js 必须含人格字段中文映射与「档位」描述
  const main = fs.readFileSync(path.join(ROOT, "src", "main.js"), "utf8");
  check(/开放性/.test(main) && /尽责性/.test(main) && /熟悉度/.test(main), "人格/关系字段中文映射（开放性/尽责性/熟悉度）");
  check(/很高|较高|偏高|档位|tier/.test(main), "数值含档位描述");
  // T111/T118：事件卡缩略图（门控）
  check(/_cardHtml/.test(audit) && /EVENT_CARDS/.test(audit), "事件卡缩略图接线（EVENT_CARDS 单一真源）");
  check(/eventCardSlug/.test(audit) && /EVENT_CARDS_BY_TEMPLATE/.test(audit) && /机械事件/.test(audit), "事件卡门控（机械事件默认不配卡；template 驱动）");
  check(/_wireCardArt/.test(audit) && /ev-lightbox/.test(audit), "事件卡点击放大（lightbox）");
  check(/ev-cardart-img/.test(fs.readFileSync(path.join(ROOT, "styles", "app.css"), "utf8")), "事件卡样式在 app.css（shell 侧）");
  // G-12 经济/制度面板
  check(/data-tab="econ"/.test(html) && /id="econ-body"/.test(html), "经济/制度面板（econ tab + pane）");
  check(/renderEcon/.test(audit) && /giniOf/.test(audit) && /sparkline/.test(audit), "经济面板由日志确定性重算（renderEcon/gini/sparkline）");
  testECrossGate();
}

// 第 7 道门禁（T123）：JS `eventCardSlug()` ≡ Python `obs.gated_slug()`。
// 两边各自实现同一套门控；任何一边改了映射/门控就会静默分叉 → 此处不一致即红。
function testECrossGate() {
  const fixture = [
    // 无条件
    { type: "SKILL_PRACTICE", payload: {} }, { type: "OFFER_REJECTED", payload: {} },
    { type: "ROLE_CHANGE", payload: {} }, { type: "NORM_PROPOSED", payload: {} },
    { type: "OFFER_COUNTERED", payload: {} }, { type: "CONFLICT_STARTED", payload: {} },
    { type: "CONFLICT_RESOLVED", payload: {} },
    // template 命中（全量模板）
    ...["mentorship", "creative_collab", "academic_collab", "combat_training", "select_location",
      "gift", "savings", "whisper", "ice_break", "rel_maintain"].map((t) => ({ type: "ACTIVITY_STARTED", payload: { template: t } })),
    // 语义条件
    { type: "TRANSFER", payload: { reason: "gift" } }, { type: "TRANSFER", payload: { reason: "wage" } },
    { type: "DEPOSIT", payload: {} }, { type: "WITHDRAW", payload: {} },
    { type: "STATE_CHANGE", payload: { to: "exhausted" } }, { type: "STATE_CHANGE", payload: { to: "alive" } },
    { type: "MARKET_TRADE", payload: { reason: "scarce_buy", scarcity_index: 0 } },
    { type: "MARKET_TRADE", payload: { reason: "normal", scarcity_index: 0 } },
    { type: "MARKET_TRADE", payload: { scarcity_index: 0.9 } },
    { type: "MSG_DM", payload: { visibility: "private" } }, { type: "MSG_DM", payload: {} },
    // 机械（默认不配卡）
    { type: "RELATION_CHANGE", payload: { from: "P1", to: "P2" } }, { type: "NEED_UPDATE", payload: { dim: "energy" } },
    { type: "PLACE_MOVE", payload: {} }, { type: "ACTIVITY_STARTED", payload: {} },
    { type: "LLM_JUDGMENT", payload: { dimension: "weekly_focus" } }, { type: "SCORE_POSTED", payload: {} },
    // 反造假：template=rel_accept 不得点亮 rel-acceptance（两边都必须空）
    { type: "LLM_JUDGMENT", payload: { template: "rel_accept" } },
  ];
  const js = fixture.map((e) => global.HITTAudit.eventCardSlug(e, global.HITTSprites) || "");
  const pyCode = "import sys,json; from obs.recount_cards import gated_slug; " +
    "d=json.load(sys.stdin); print(json.dumps([gated_slug(r) or '' for r in d]))";
  const r = require("child_process").spawnSync("python3", ["-c", pyCode],
    { cwd: path.join(ROOT, ".."), input: JSON.stringify(fixture), encoding: "utf8" });
  if (r.error || r.status !== 0) {
    check(false, "JS≡Python 门控对拍：python 调用失败（" + (r.error ? r.error.message : (r.stderr || "").trim()) + "）");
    return;
  }
  let py;
  try { py = JSON.parse(r.stdout.trim()); } catch (e) { check(false, "JS≡Python 门控对拍：输出解析失败"); return; }
  const mism = [];
  for (let i = 0; i < fixture.length; i++) if (js[i] !== py[i]) mism.push(`${fixture[i].type}${fixture[i].payload && fixture[i].payload.template ? "/tmpl=" + fixture[i].payload.template : ""}: JS=${js[i] || "-"} PY=${py[i] || "-"}`);
  check(mism.length === 0, "JS eventCardSlug ≡ Python obs.gated_slug（" + fixture.length + " 例" + (mism.length ? "，不一致:" + mism.slice(0, 4).join(" | ") : "，全一致") + "）");
}

const onlyRender = process.argv.includes("--selftest-render-only");
console.log("frontend smoke test @ " + ROOT);
installPixiMock();
loadModules();
(async () => {
  if (!onlyRender) testA();
  await testB();
  testC();
  testD();
  testE();
  console.log("\n" + (failures ? "FAIL (" + failures + ")" : "PASS"));
  process.exit(failures ? 1 : 0);
})();
