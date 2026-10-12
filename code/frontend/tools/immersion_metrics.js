#!/usr/bin/env node
/* immersion_metrics.js — R9「沉浸/质感」可复算口径（A 部分，只读日志/渲染坐标）。
 *
 * 三条子指标（确定性、可对拍、进 CI）：
 *   1) activity_ratio   = 产生"可见画面反馈"的事件数 / 总事件数        （阈值 ≥0.5）
 *   2) idle_round_ratio = 零变化回合数 / 总回合数                      （阈值 ≤0.2）
 *   3) causal_coverage  = 叙事级事件中"能展开为什么(reason/cause/cause_event_seq)"的比例 （阈值 ≥0.8）
 *   4) label_overlap_rate = default 视图下，场所标签包围盒与**其它**场所建筑矩形相交的占比（阈值 ≤0.05）
 *
 * ★ 成立条件（leader 要求：写清条件，变了要重校）：
 *   - 视图：`view=default`（仅场所名标签；无 NPC ID）· 缩放：**scale=1（未缩放）**· 世界尺寸：960×720；
 *   - 日志：本脚本对**任意传入日志**计算；CI 使用 `sample/demo_run.jsonl`（固定）；
 *   - label_overlap 为**渲染坐标的确定性近似**（标签宽≈`len*13*0.66`，置于建筑下方），
 *     非像素级测量；视图/尺寸/人口/标签口径变化 → 阈值须重校。
 *
 * 用法：node frontend/tools/immersion_metrics.js [--log <jsonl>] [--json]
 * 退出码：0=PASS（四项全达标）；1=FAIL。
 */
"use strict";
const fs = require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "..");

global.window = global;
require(path.join(ROOT, "src", "data.js"));
require(path.join(ROOT, "src", "sprites.js"));
require(path.join(ROOT, "src", "replay.js"));

const R = global.HITTReplay;
const TH = { activity_ratio: 0.5, idle_round_ratio: 0.2, causal_coverage: 0.8, label_overlap_rate: 0.05 };

// "可见画面反馈"事件（会在地图上产生可感知变化）
const VISIBLE = new Set([
  "PLACE_MOVE", "PLACE_ARRIVED", "ACTIVITY_STARTED", "ACTIVITY_COMPLETED", "ACTIVITY_INTERRUPTED",
  "MSG_PUBLIC", "MSG_DM", "MSG_GROUP", "MARKET_TRADE", "TRANSFER", "AGENT_DIED", "AGENT_REVIVED",
  "NORM_PROPOSED", "NORM_ADOPTED", "NORM_VIOLATED", "CONFLICT_STARTED", "CONFLICT_RESOLVED",
  "GROUP_CREATED", "GROUP_JOINED", "GROUP_LEFT", "ROLE_CHANGE", "SKILL_LEVEL_UP", "SKILL_OUTPUT",
  "GOAL_SET", "GOAL_ACHIEVED", "SEED_EVENT", "RELATION_CHANGE", "RELATION_ENCOUNTER", "AGENT_BORN",
]);

function metricsFromLog(file) {
  const recs = global.HITTData.parseJSONL(fs.readFileSync(file, "utf8"));
  const rp = new R.Replay(recs);
  let vis = 0, total = 0, narr = 0, causal = 0;
  const roundVis = {};
  for (const ev of recs) {
    total++;
    if (VISIBLE.has(ev.type)) { vis++; roundVis[ev.round] = 1; }
    const h = R.humanize(ev, { name: (x) => x, place: (x) => x || "" });
    if (h.level === "narrative") {
      narr++;
      const c = R.causalOf(ev);
      if ((c.code) || (c.links && c.links.length)) causal++;
    }
  }
  const rounds = rp.rounds.length || 1;
  const idle = rp.rounds.filter((r) => !roundVis[r]).length;
  return {
    total_events: total, rounds,
    activity_ratio: total ? vis / total : 0,
    idle_round_ratio: idle / rounds,
    causal_coverage: narr ? causal / narr : 1,
  };
}

// label_overlap_rate（default 视图、scale=1、960×720 的确定性近似）
function labelOverlap() {
  const places = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "places.json"), "utf8")).places;
  const topo = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "topology.json"), "utf8"));
  const nodes = {}; topo.nodes.forEach((n) => { nodes[n.place_id] = n; });
  const S = 78, HT = S * 0.72;
  const rects = places.filter((p) => nodes[p.place_id]).map((p) => {
    const n = nodes[p.place_id];
    return { id: p.place_id, x0: n.x - S / 2, y0: n.y - HT / 2, x1: n.x + S / 2, y1: n.y + HT / 2 };
  });
  const labels = places.filter((p) => nodes[p.place_id]).map((p) => {
    const n = nodes[p.place_id];
    const name = p.name_cn || p.place_id;
    const w = Math.max(40, name.length * 13 * 0.66);
    const y = n.y + HT / 2 + 15;               // 标签基线（与 sprites.js makePlaceSprite 一致）
    return { id: p.place_id, x0: n.x - w / 2, y0: y - 13, x1: n.x + w / 2, y1: y + 3 };
  });
  const inter = (a, b) => a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1;
  let hit = 0;
  for (const L of labels) {
    if (rects.some((r) => r.id !== L.id && inter(L, r))) hit++;
  }
  return { labels: labels.length, overlapping: hit, label_overlap_rate: labels.length ? hit / labels.length : 0 };
}

function main() {
  const argv = process.argv.slice(2);
  const li = argv.indexOf("--log");
  const logArg = li >= 0 ? argv[li + 1] : "sample/demo_run.jsonl";
  const log = path.isAbsolute(logArg) ? logArg : path.join(ROOT, logArg);
  const m = Object.assign(metricsFromLog(log), labelOverlap());
  const checks = [
    ["activity_ratio", m.activity_ratio, (v) => v >= TH.activity_ratio, "≥" + TH.activity_ratio],
    ["idle_round_ratio", m.idle_round_ratio, (v) => v <= TH.idle_round_ratio, "≤" + TH.idle_round_ratio],
    ["causal_coverage", m.causal_coverage, (v) => v >= TH.causal_coverage, "≥" + TH.causal_coverage],
    ["label_overlap_rate", m.label_overlap_rate, (v) => v <= TH.label_overlap_rate, "≤" + TH.label_overlap_rate],
  ];
  let fail = 0;
  console.log(`immersion metrics @ ${path.relative(ROOT, log)}（total=${m.total_events} rounds=${m.rounds} labels=${m.labels}）`);
  console.log(`  条件：view=default · scale=1 · 960×720 · label_overlap 为渲染坐标近似`);
  for (const [k, v, ok, cmp] of checks) {
    const good = ok(v);
    if (!good) fail++;
    console.log(`  ${good ? "ok  -" : "FAIL-"} ${k} = ${(+v).toFixed(4)} (需 ${cmp})`);
  }
  console.log(fail ? `IMMERSION FAIL (${fail})` : "IMMERSION PASS");
  return fail ? 1 : 0;
}
process.exit(main());
