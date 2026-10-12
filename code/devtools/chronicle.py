#!/usr/bin/env python3
"""chronicle.py — 世界观编年史可视化工具（devtools P0：DT-1 / DT-2 / DT-3）。

只读事件日志 → 生成**可读的编年史**：① 事件时间线（DT-1/W-1）② 编年史大纲（DT-3/W-2）
③ 可视化关系网（DT-2/W-3）④ 角色记忆 Prompt 导出（DT-3/W-4）⑤ 溯源跳转（W-6）。

## 约束（v2/refs/devtools-requirements.md §0）
- **只读优先**：经 `obs.reader.ReadOnlyLog` 读取，构造即校验哈希链；**不写世界**（无任何写事件）。
- **来源可追溯**：时间线节点/大纲条目/关系边/角色素材**每一项**都带真实 `event_seq`，界面可点开 payload。
- **口径复用 `obs/*`**：语义普查用 `obs.census.semantic_census`、关系权重用 `obs.folds.relation_weights`，
  **工具不另立算法**；周/日/时段用 `engine.time.derive_time`（纯函数）。
- **红线**：只呈现**已发生**的事；**不改结局/不调分支/不替 Agent 决定社会结果**。
- **不新增不可复现环节**：产物是**只读旁路**（模型 JSON + 静态 HTML + 角色素材），不进世界。
- 不改 `engine/` `life/` `freeze/` 既有语义。

## 用法
    cd code
    python devtools/chronicle.py \
        --log frontend/sample/run_b2_n20_week.play.jsonl \
        --out /tmp/chronicle_out \
        [--personas config/personas.json] [--cap 0]

产物（写入 `--out`）：
    chronicle.model.json    数据模型（真实日志派生；含 log_hash/seed/max_round）
    chronicle.html          自包含查看器（时间线 / 大纲 / 关系网 / 普查 / 溯源）
    characters/<id>.md      每角色一份记忆素材（身份 + 关键记忆 + 关系，均带 seq）
"""
from __future__ import annotations

import argparse
import collections
import html
import json
import sys
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[1]           # -> code/
sys.path.insert(0, str(CODE_DIR))

from obs.reader import ReadOnlyLog                        # noqa: E402
from obs.census import semantic_census, SEMANTIC_EVENT_ORDER  # noqa: E402
from obs.folds import relation_weights                    # noqa: E402
from engine.time import derive_time                       # noqa: E402

# 时间线/大纲里视为"重大"的事件类型（展示口径；非判定口径——不改 obs/census 语义）
SIGNIFICANT = [
    "AGENT_BORN", "AGENT_DIED", "AGENT_REVIVED", "STATE_CHANGE",
    "MARKET_TRADE", "TRANSFER", "LOAN_ISSUED", "LOAN_DEFAULT", "TAX_LEVIED", "UBI_PAID",
    "PENALTY_APPLIED", "REVIVE_FEE_PAID",
    "MSG_DM", "MSG_PUBLIC", "MSG_GROUP", "RELATION_CHANGE", "RELATION_ENCOUNTER",
    "OFFER_CREATED", "OFFER_ACCEPTED", "OFFER_REJECTED", "OFFER_COUNTERED",
    "CONFLICT_STARTED", "CONFLICT_RESOLVED", "NORM_PROPOSED", "NORM_ADOPTED",
    "GROUP_CREATED", "GROUP_JOINED", "ROLE_CHANGE", "SKILL_LEVEL_UP", "SEED_EVENT",
    "GOAL_SET", "GOAL_ACHIEVED", "NARRATIVE",
]
TYPE_CN = {
    "AGENT_BORN": "出生", "AGENT_DIED": "离世", "AGENT_REVIVED": "复活", "STATE_CHANGE": "状态变化",
    "MARKET_TRADE": "市集交易", "TRANSFER": "转账", "LOAN_ISSUED": "借入贷款", "LOAN_DEFAULT": "贷款违约",
    "TAX_LEVIED": "缴税", "UBI_PAID": "领取 UBI", "PENALTY_APPLIED": "受罚", "REVIVE_FEE_PAID": "支付复活费",
    "MSG_DM": "私信", "MSG_PUBLIC": "公开发言", "MSG_GROUP": "群内发言",
    "RELATION_CHANGE": "关系变化", "RELATION_ENCOUNTER": "相遇",
    "OFFER_CREATED": "发起协商", "OFFER_ACCEPTED": "接受协商", "OFFER_REJECTED": "拒绝协商",
    "OFFER_COUNTERED": "协商还价", "CONFLICT_STARTED": "冲突爆发", "CONFLICT_RESOLVED": "冲突结束",
    "NORM_PROPOSED": "规范提案", "NORM_ADOPTED": "规范采纳", "GROUP_CREATED": "创建群体",
    "GROUP_JOINED": "加入群体", "ROLE_CHANGE": "身份变化", "SKILL_LEVEL_UP": "技能升级",
    "SEED_EVENT": "种子事件", "GOAL_SET": "立下目标", "GOAL_ACHIEVED": "达成目标", "NARRATIVE": "叙事小记",
}


def _load_records(path: Path) -> list[dict]:
    recs = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    recs.sort(key=lambda r: r.get("seq", 0))
    return recs


def build_model(log_path: Path, *, cap: int, personas_path: Path | None, verify: bool = True) -> dict:
    records = _load_records(log_path)
    log = ReadOnlyLog(records, verify=verify)
    if verify:
        log.require_chain()                               # 只读 + 拒绝非法日志（15 §5）
    # 注意：派生的"播放视图"(play.jsonl) 剔除了事件 → seq 不连续、哈希链不成立，
    # 属**已知**：须显式 `--no-verify` 并接受它是**派生日志**（canonical 才是事实源）。
    tcfg = None
    tc = collections.OrderedDict()

    def tinfo(round_no: int) -> dict:
        if round_no not in tc:
            tc[round_no] = derive_time(int(round_no), tcfg)
        return tc[round_no]

    # ---- DT-1 时间线（全部事件；可选 cap 截断，另存每回合计数=全量）----
    round_counts: dict[int, int] = collections.Counter(int(r["round"]) for r in records)
    tline = []
    for r in records:
        ti = tinfo(r["round"])
        tline.append({
            "seq": r["seq"], "round": r["round"], "week": ti["week"], "day": ti["day_of_week"],
            "slot": ti["slot"], "phase": r.get("phase"), "type": r["type"],
            "actor": r.get("actor"), "payload": r.get("payload") or {},
        })
    truncated = False
    if cap and len(tline) > cap:
        # 截断时优先保留"重大"事件（可复现：按 seq 升序稳定过滤）
        sig = [e for e in tline if e["type"] in SIGNIFICANT]
        rest = [e for e in tline if e["type"] not in SIGNIFICANT]
        tline = (sig + rest)[:cap]
        truncated = True

    # ---- DT-3/W-2 大纲：按周分章（重大事件按类型聚合 + 来源 seq）----
    weeks: dict[int, dict] = collections.OrderedDict()
    for r in records:
        if r["type"] not in SIGNIFICANT:
            continue
        ti = tinfo(r["round"])
        wk = ti["week"]
        ch = weeks.setdefault(wk, {"week": wk, "items": collections.defaultdict(list)})
        ch["items"][r["type"]].append(r["seq"])
    outline = []
    for wk, ch in sorted(weeks.items()):
        items = []
        for t, seqs in sorted(ch["items"].items(), key=lambda kv: kv[1][0]):
            items.append({
                "type": t, "label": TYPE_CN.get(t, t), "count": len(seqs),
                "source_event_seqs": seqs[:50], "seq_truncated": max(0, len(seqs) - 50),
            })
        outline.append({"week": wk, "items": items})

    # ---- DT-2/W-3 关系网：复用 obs.folds.relation_weights（有向 (from,to,dim)→last_after）----
    wmap = relation_weights(records)                      # {(from,to,dim): value}
    edge_seqs: dict[tuple, list] = collections.defaultdict(list)
    for r in records:
        if r["type"] == "RELATION_CHANGE":
            p = r["payload"]
            if p.get("from") and p.get("to"):
                edge_seqs[(p["from"], p["to"])].append(r["seq"])
    graph_edges = []
    nodes = set()
    for (frm, to, dim), val in sorted(wmap.items(), key=lambda kv: str(kv[0])):
        if not frm or not to:
            continue
        nodes.add(frm); nodes.add(to)
        graph_edges.append({
            "from": frm, "to": to, "dim": dim, "weight": val,
            "source_event_seqs": edge_seqs.get((frm, to), [])[:50],
        })

    # ---- V-2 口径复用：整段语义普查（obs.census，逐字）----
    census = semantic_census(records)
    census_view = collections.OrderedDict(
        (k, census.get("hits", {}).get(k, {})) for k in SEMANTIC_EVENT_ORDER
    )

    # ---- DT-3/W-4 角色素材（身份 + 关键记忆 + 关系；均带 seq）----
    personas = {}
    if personas_path and Path(personas_path).exists():
        pd = json.loads(Path(personas_path).read_text(encoding="utf-8"))
        for p in (pd.get("personas") or pd):
            personas[p["persona_id"]] = p
    mem_by_agent: dict[str, list] = collections.defaultdict(list)
    born, died, revived = {}, {}, {}
    for r in records:
        t, p = r["type"], r["payload"] or {}
        if t == "MEMORY_WRITE":
            mem_by_agent[p.get("agent_id")].append((float(p.get("importance") or 0), r["seq"], p))
        elif t == "AGENT_BORN":
            born[p.get("agent_id")] = r["seq"]
        elif t == "AGENT_DIED":
            died[p.get("agent_id")] = r["seq"]
        elif t == "AGENT_REVIVED":
            revived[p.get("agent_id")] = r["seq"]

    agents = sorted(set(born) | set(died) | set(revived) | set(mem_by_agent) | nodes)
    characters = {}
    for aid in agents:
        rels = [{"to": to, "dim": dim, "weight": v, "source_event_seqs": edge_seqs.get((aid, to), [])[:20]}
                for (frm, to, dim), v in wmap.items() if frm == aid]
        mems = sorted(mem_by_agent.get(aid, []), key=lambda x: (-x[0], x[1]))[:20]
        characters[aid] = {
            "id": aid,
            "persona": personas.get(aid),                 # 可能缺（【未验证】时前端标注）
            "born_seq": born.get(aid), "died_seq": died.get(aid), "revived_seq": revived.get(aid),
            "status": "dead" if (aid in died and aid not in revived) else "alive",
            "relations": rels,
            "key_memories": [{"seq": s, "importance": imp, "kind": p.get("kind"),
                              "subject": p.get("subject"), "body_ref": p.get("body_ref")} for imp, s, p in mems],
        }

    return {
        "meta": {
            "source_log": str(log_path), "log_hash": log.log_hash(), "seed": log.seed(),
            "max_round": log.max_round(), "chain_ok": log.chain_ok, "derived": (not verify),
            "total_events": len(records), "round_counts": round_counts,
            "timeline_truncated": truncated, "timeline_len": len(tline),
            "note": "只读派生；所有条目均带真实 event_seq；口径复用 obs/*（census/folds）+ engine.time.derive_time",
        },
        "timeline": tline,
        "outline": outline,
        "graph": {"nodes": sorted(nodes), "edges": graph_edges},
        "census": census_view,
        "characters": characters,
    }


def render_char_md(aid: str, c: dict) -> str:
    p = c.get("persona") or {}
    L = [f"# {p.get('display_name') or aid}  （角色记忆素材 · 只读派生 · 来源可追溯）", ""]
    L.append(f"- id: `{aid}`　状态: **{c['status']}**")
    if p:
        L.append(f"- 身份: {p.get('age','?')} 岁 · {p.get('role_id','?')} · 家「{p.get('home_place','?')}」")
        if p.get("background"):
            L.append(f"- 背景: {p['background']}")
    else:
        L.append("- 身份: 【未验证】未在 persona 配置中找到该角色（仅据日志）")
    seqs = [f"`{c['born_seq']}`" if c.get("born_seq") is not None else "—"]
    if c.get("died_seq") is not None:
        seqs.append(f"离世 `{c['died_seq']}`")
    if c.get("revived_seq") is not None:
        seqs.append(f"复活 `{c['revived_seq']}`")
    L += ["", "## 生命节点（来源 seq）", "- 出生 " + "；".join(seqs), "",
          "## 关系（obs.folds.relation_weights，含来源 seq）"]
    if c["relations"]:
        for r in c["relations"]:
            L.append(f"- → {r['to']}　{r['dim']}={r['weight']}　seq={r['source_event_seqs'][:5]}")
    else:
        L.append("- （无关系记录）")
    L += ["", "## 关键记忆（按 importance，含来源 seq）"]
    if c["key_memories"]:
        for m in c["key_memories"]:
            L.append(f"- [{m['importance']}] {m.get('kind') or ''} {m.get('subject') or ''}（seq `{m['seq']}`）")
    else:
        L.append("- （无 MEMORY_WRITE 记录）")
    L += ["", "> 本素材**仅含日志已发生事实**，可直接接入记忆系统；不含任何未发生/编造内容。"]
    return "\n".join(L) + "\n"


VIEWER_HTML = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>青溪镇 · 世界观编年史（devtools P0）</title>
<style>
:root{--bg:#0e1218;--panel:#1a2029;--line:#303a49;--fg:#e6ebf2;--muted:#8b98ab;--acc:#5cc8ff;--acc2:#ffcf5c}
*{box-sizing:border-box}body{margin:0;height:100vh;display:flex;flex-direction:column;background:var(--bg);color:var(--fg);font:13px/1.5 "PingFang SC","Microsoft YaHei",sans-serif}
header{padding:8px 14px;background:var(--panel);border-bottom:1px solid var(--line);display:flex;gap:14px;align-items:center}
header .t{font-weight:700}header .m{color:var(--muted);font-size:12px}
.tabs{display:flex;gap:6px;padding:8px 14px;background:var(--panel);border-bottom:1px solid var(--line)}
.tab{background:#232b37;border:1px solid var(--line);color:var(--muted);border-radius:8px;padding:5px 10px;cursor:pointer}
.tab.active{color:var(--fg);border-color:var(--acc);background:#1d3b52}
main{flex:1;display:flex;min-height:0}
#pane{flex:1;overflow:auto;padding:10px 14px}
#drawer{width:430px;background:var(--panel);border-left:1px solid var(--line);overflow:auto;padding:10px 12px}
#drawer pre{background:#121721;border:1px solid var(--line);border-radius:6px;padding:8px;white-space:pre-wrap;word-break:break-word;font-size:11px}
.row{padding:5px 8px;border-left:3px solid var(--line);border-radius:6px;background:rgba(35,43,55,.4);margin:3px 0;cursor:pointer}
.row:hover{background:rgba(92,200,255,.14)}
.seq{color:var(--muted);font-family:monospace;font-size:11px}.ty{color:var(--acc2);font-family:monospace}
.wk{color:var(--acc);font-weight:700;margin:12px 0 4px;border-bottom:1px dashed var(--line)}
.badge{color:var(--muted);font-size:11px}
svg{background:#0b0f14;border:1px solid var(--line);border-radius:8px}
.e{stroke:var(--acc);stroke-opacity:.5}.n{fill:var(--acc2)}.n text{fill:#0b0f14;font-size:9px}
h3{margin:10px 0 4px}
</style></head><body>
<header><span class="t">青溪镇 · 世界观编年史</span><span class="m" id="meta"></span></header>
<div class="tabs">
  <button class="tab active" data-t="timeline">时间线</button>
  <button class="tab" data-t="outline">编年史大纲</button>
  <button class="tab" data-t="graph">关系网</button>
  <button class="tab" data-t="census">语义普查（复用 obs）</button>
  <button class="tab" data-t="chars">角色素材</button>
</div>
<main><div id="pane"></div><div id="drawer"><div class="badge">点任一条目/边 → 此处显示溯源（seq / payload）</div><div id="detail"></div></div></main>
<script>
const M = __MODEL__;
const esc = s => String(s==null?'':s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const typeCn = __TYPECN__;
function detail(seq){ const e = M.timeline.find(x=>x.seq===seq); const d=document.getElementById('detail');
  if(!e){ d.innerHTML='<div class="badge">该 seq 不在时间线（可能被 cap 截断）</div>'; return; }
  d.innerHTML='<h3>溯源 #'+seq+'</h3><div class="badge">'+esc(e.type)+' · round '+e.round+' · week '+e.week+' day '+e.day+' '+e.slot+' · actor '+esc(e.actor)+'</div><pre>'+esc(JSON.stringify(e.payload,null,1))+'</pre>'; }
function seqLinks(seqs, trunc){ return (seqs||[]).map(s=>'<a href="#" onclick="detail('+s+');return false">#'+s+'</a>').join(' ')+(trunc?(' …+'+trunc):''); }
function show(t){
  document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('active',b.dataset.t===t));
  const P=document.getElementById('pane'); let h='';
  if(t==='timeline'){ let curW=null;
    h='<div class="badge">共 '+M.timeline.length+' 节点'+(M.meta.timeline_truncated?'（已截断，全量 '+M.meta.total_events+' 事件；每回合计数见 meta.round_counts）':'（全量）')+'</div>';
    for(const e of M.timeline){ if(e.week!==curW){curW=e.week; h+='<div class="wk">第 '+(e.week+1)+' 周</div>';}
      h+='<div class="row" onclick="detail('+e.seq+')"><span class="seq">#'+e.seq+'</span> <span class="ty">'+esc(e.type)+'</span> <span class="badge">r'+e.round+' d'+e.day+' '+esc(e.slot)+' · '+esc(e.actor)+'</span></div>'; } }
  else if(t==='outline'){ for(const ch of M.outline){ h+='<div class="wk">第 '+(ch.week+1)+' 周</div>';
      for(const it of ch.items){ h+='<div class="row"><span class="ty">'+esc(it.label)+'</span> ×'+it.count+' <span class="badge">来源 '+seqLinks(it.source_event_seqs,it.seq_truncated)+'</span></div>'; } } }
  else if(t==='graph'){ h=graphSVG(); }
  else if(t==='census'){ h='<div class="badge">逐字复用 obs.census.semantic_census（V-2 口径一致）</div><table style="width:100%;border-collapse:collapse">';
      for(const k of Object.keys(M.census)){ const v=M.census[k]; h+='<tr style="border-bottom:1px solid #303a49"><td>'+esc(k)+'</td><td>'+(v.hit?('×'+(v.count||0)+'　首轮 r'+(v.first_round)):'—')+'</td></tr>'; } h+='</table>'; }
  else if(t==='chars'){ for(const id of Object.keys(M.characters)){ const c=M.characters[id];
      h+='<div class="row"><b>'+esc((c.persona&&c.persona.display_name)||id)+'</b> <span class="badge">'+esc(id)+' · '+c.status+' · 记忆'+c.key_memories.length+' · 关系'+c.relations.length+'</span><br><span class="badge">出生 '+seqLinks([c.born_seq])+'　离世 '+(c.died_seq!=null?seqLinks([c.died_seq]):'—')+'</span></div>'; } }
  P.innerHTML=h;
}
function graphSVG(){ const n=M.graph.nodes, raw=M.graph.edges, R=Math.min(560, 30+n.length*20);
  // 聚合为"无向人物对"（合并 dim；权重求和；合并来源 seq），避免每 dim 一条边导致近完全图的视觉噪声
  const pm=new Map(); for(const ed of raw){ const k=[ed.from,ed.to].sort().join('|');
    const o=pm.get(k)||{a:ed.from,b:ed.to,w:0,dims:new Set(),seqs:new Set()}; o.w+=ed.weight; o.dims.add(ed.dim);
    (ed.source_event_seqs||[]).forEach(s=>o.seqs.add(s)); pm.set(k,o); }
  const pairs=[...pm.values()].sort((x,y)=>y.w-x.w);
  const cx=R+20, cy=R+20; const pos={}; n.forEach((id,i)=>{const a=2*Math.PI*i/Math.max(1,n.length); pos[id]=[cx+R*Math.cos(a),cy+R*Math.sin(a)];});
  let s='<svg width="'+(2*R+40)+'" height="'+(2*R+40)+'" font-family="monospace">';
  for(const p of pairs){ const a=pos[p.a], b=pos[p.b]; if(!a||!b)continue;
    s+='<line class="e" stroke-width="'+Math.min(3,0.5+p.w/40)+'" x1="'+a[0]+'" y1="'+a[1]+'" x2="'+b[0]+'" y2="'+b[1]+'"/>'; }
  for(const id of n){ const p=pos[id]; const lx=p[0]<cx?-4:4;
    s+='<circle class="n" cx="'+p[0]+'" cy="'+p[1]+'" r="11"/>'+
       '<text x="'+(p[0]+lx)+'" y="'+(p[1]+3)+'" text-anchor="'+(lx<0?'end':'start')+'" style="font-size:10px">'+esc(id)+'</text>'; }
  s+='</svg><div class="badge">节点='+n.length+'　人物对='+pairs.length+'（边=obs.folds.relation_weights 聚合；点下方边→溯源首条 seq）</div>';
  for(const p of pairs.slice(0,200)){ const seqs=[...p.seqs].sort((a,b)=>a-b).slice(0,6);
    s+='<div class="row" onclick="detail('+(seqs[0]!=null?seqs[0]:0)+')">'+esc(p.a)+' ↔ '+esc(p.b)+' <span class="badge">w='+Math.round(p.w)+'　'+[...p.dims].join('/')+'　seq '+seqLinks(seqs,0)+'</span></div>'; }
  return s; }
document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>show(b.dataset.t));
document.getElementById('meta').textContent = '来源: '+M.meta.source_log+' · log_hash='+M.meta.log_hash.slice(0,22)+'… · seed='+M.meta.seed+' · max_round='+M.meta.max_round+' · chain_ok='+M.meta.chain_ok+' · 总事件 '+M.meta.total_events;
window.addEventListener('hashchange',()=>show((location.hash||'#timeline').slice(1)));
show((location.hash||'#timeline').slice(1));
</script></body></html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="世界观编年史可视化（devtools P0：DT-1/2/3）")
    ap.add_argument("--log", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--personas", default=str(CODE_DIR / "config" / "personas.json"))
    ap.add_argument("--cap", type=int, default=0, help="时间线嵌入上限（0=全量）")
    ap.add_argument("--no-verify", action="store_true",
                    help="跳过哈希链校验（仅用于**派生日志**如 play.jsonl；canonical 请勿用）")
    args = ap.parse_args()

    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    if args.no_verify:
        print("WARN: --no-verify —— 跳过哈希链校验。仅当输入是**派生日志**(如 play.jsonl)时使用；"
              "事实源应为 canonical 日志。")
    model = build_model(Path(args.log).expanduser().resolve(), cap=args.cap,
                        personas_path=Path(args.personas) if args.personas else None,
                        verify=not args.no_verify)

    (out / "chronicle.model.json").write_text(
        json.dumps(model, ensure_ascii=False, indent=1), encoding="utf-8")

    char_dir = out / "characters"
    char_dir.mkdir(exist_ok=True)
    for aid, c in model["characters"].items():
        (char_dir / f"{aid}.md").write_text(render_char_md(aid, c), encoding="utf-8")

    html_txt = VIEWER_HTML.replace("__MODEL__", json.dumps(model, ensure_ascii=False)) \
                          .replace("__TYPECN__", json.dumps(TYPE_CN, ensure_ascii=False))
    (out / "chronicle.html").write_text(html_txt, encoding="utf-8")

    print(f"chronicle -> {out}")
    print(f"  model: timeline={len(model['timeline'])}/{(model['meta']['total_events'])} "
          f"outline_weeks={len(model['outline'])} graph_edges={len(model['graph']['edges'])} "
          f"characters={len(model['characters'])}")
    print(f"  log_hash={model['meta']['log_hash'][:24]}… chain_ok={model['meta']['chain_ok']}")
    print(f"  html:  {out/'chronicle.html'}")
    print(f"  chars: {char_dir}/<id>.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
