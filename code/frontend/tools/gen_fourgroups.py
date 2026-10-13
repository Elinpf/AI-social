#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_fourgroups.py — 生成「四组对照」自包含 HTML（T343）。

- **只读**证据：口径① 取自 `v2/evidence/nightly-20261012-morning-report.md`（数字逐字抄），
  口径② 取自 `v2/evidence/t292_shared_results.json`（另有 `t310_results.json` 作同口径二次复跑备注）。
- 输出 `code/frontend/fourgroups.html`：**自包含**（数据内联，无构建/无联网）、窄屏可读。
- **两版口径分套、不混**；结论**逐条对齐早报**（不"翻译"成更强说法）。
- 页脚绑定 **证据 sha**（当前 HEAD）+ 源文件。

用法：python3 code/frontend/tools/gen_fourgroups.py
"""
from __future__ import annotations
import hashlib, json, subprocess, sys
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[1]
ROOT = FRONTEND.parents[1]
EV = ROOT / "v2" / "evidence"


def head_sha() -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=5).stdout.strip() or "—"
    except Exception:
        return "—"


# ---- 口径①：逐字抄自 nightly-20261012-morning-report.md §1/§2（数字/限定词不改写）----
D1 = {
    "label": "口径① · 10-12 夜跑原始四批",
    "source": "v2/evidence/nightly-20261012-morning-report.md",
    "runtime": "各 80–90 分钟（19:01 起）",
    "rss_note": "峰值 RSS 来自早报 §1",
    "groups": {
        "A": {"name": "A 基线", "sw": "-", "status": "SUCCESS", "events": 301384, "llm": 4794, "rss": "383MB", "time": "80m", "fp": "f1ea31a3", "sh": "a8b6da39"},
        "B": {"name": "B 关世界导演", "sw": "world_director.enabled=false", "status": "SUCCESS", "events": 301395, "llm": 4794, "rss": "436MB", "time": "80m", "fp": "a89546fd", "sh": "07046536"},
        "C": {"name": "C 关三族", "sw": "life_v2 sleep/forgetting=false", "status": "SUCCESS", "events": 151968, "llm": 4794, "rss": "310MB", "time": "80m", "fp": "f8d3f0a8", "sh": "dd1c7906"},
        "D": {"name": "D 开双时钟", "sw": "wake.enabled=true", "status": "SUCCESS", "events": 304607, "llm": 4718, "rss": "382MB", "time": "90m", "fp": "adaede05", "sh": "b7c21436"},
    },
    # 早报 §2 明示的类型差异（仅列明示项，不补造全量）
    "diffs": {
        "B": ["WORLD_DIRECTIVE 1→0、WORLD_GROUP_EVENT 1→0（84 回合只介入 1 次）", "PERSONA_DRIFT 0→9", "MEMORY_FORGET +4"],
        "C": ["事件 301,384 → 151,968（≈ 半）"],
        "D": ["（早报未逐类列出；见口径② 的同类对照）"],
    },
    "diff_head": "类型差异（早报 §2 明示项；口径①未逐类全列）",
    "concl": {
        "A": "基线",
        "B": "旁白型：84 回合只介入 1 次，且两类在 replay 属 _NOOP_TYPES、不改世界状态 ⇒ 非 D3 要的『宏观群体事件』",
        "C": "★ 第一条真实消融效应：关睡眠/遗忘/人格三族 → 事件 ≈ 半",
        "D": "开双时钟（wake.enabled=true）",
    },
    "notes": ["全部 provider=openai_compat、无 mock 混入；每批 rc=0。", "冻结 sha 6a5f14e；底座指纹 sha256:f1ea31a3…（= A 日志 WORLD_INIT）。"],
}

# ---- 口径②：读 t292（主表，数字与任务口径一致）+ t310（同口径二次复跑，备注）----
def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def file_sha16(p: Path) -> str:
    """数据源文件自身的 sha256 前 16 位（回答"数从哪个文件的哪个版本来"）。"""
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    except Exception:
        return "—"


def main() -> int:
    t292 = load_json(EV / "t292_shared_results.json")
    t310 = load_json(EV / "t310_results.json")
    sha = head_sha()
    file_shas = {
        "report": file_sha16(EV / "nightly-20261012-morning-report.md"),
        "t310": file_sha16(EV / "t310_results.json"),
        "t292": file_sha16(EV / "t292_shared_results.json"),
    }
    html = _render(D1, t292, t310, sha, file_shas)
    out = FRONTEND / "fourgroups.html"
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out}  head={sha}  file_shas={file_shas}")
    return 0


def _render(D1, t292, t310, sha, file_shas) -> str:
    payload = {
        "d1": D1,
        "d2": {
            "label": "口径② · 10-13 干净复跑（分进程，权威=t310）",
            "source": "v2/evidence/t310_results.json",
            "groups": t310,
            "aux_source": "v2/evidence/t292_shared_results.json",
            "aux": t292,
            "notes": [
                "口径② = 【分进程】复跑；t310 = 权威（该口径的正确仪器），t292 = 参考（被 T310 取代）。",
                "C 仅 t292 有（t292 那次 C 未被真正关掉 ⇒ C≡A，机制缺口已修 T297b）；t310 无 C。",
                "t310 与 t292 的 A/B 绝对值不可直接比：树 63c200a ≠ 8680737，A 301,332→292,141 的差是【树前进】(T298 行为变)，非装置；两处 B−A 都 = −2（这才是稳健结论）。别把绝对值变小当性能/装置收益。",
            ],
        },
        "sha": sha,
        "file_shas": file_shas,
    }
    return HTML_TMPL.replace("/*__DATA__*/", json.dumps(payload, ensure_ascii=False))


HTML_TMPL = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>四组对照 · A/B/C/D</title>
<style>
 :root{--bg:#0d1117;--panel:#161b22;--line:#30363d;--fg:#e6edf3;--muted:#8b949e;--accent:#58a6ff;--ok:#3fb950;--warn:#d29922;--bad:#f85149}
 *{box-sizing:border-box}
 body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.55 -apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
 header{padding:16px 20px;border-bottom:1px solid var(--line)}
 h1{margin:0 0 6px;font-size:19px}
 .sub{color:var(--muted);font-size:13px}
 main{padding:16px 20px 40px;max-width:1400px;margin:0 auto}
 .switcher{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0 10px}
 .switcher button{background:var(--panel);border:1px solid var(--line);color:var(--fg);padding:8px 14px;border-radius:8px;cursor:pointer;font-size:13px}
 .switcher button.active{border-color:var(--accent);background:#1d2b3a}
 .caliber{display:inline-block;margin:6px 0 12px;padding:4px 10px;border-radius:999px;border:1px solid var(--warn);color:var(--warn);font-size:12.5px}
 table{width:100%;border-collapse:collapse;font-size:12.5px;margin:6px 0 16px}
 th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
 th{background:var(--panel);white-space:nowrap}
 td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
 .mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11.5px}
 h2{font-size:15px;margin:20px 0 8px;border-left:3px solid var(--accent);padding-left:8px}
 ul{margin:6px 0;padding-left:20px}
 li{margin:3px 0}
 .concl{color:#c9d1d9}
 .tag{display:inline-block;font-size:11px;padding:1px 6px;border-radius:5px;border:1px solid var(--line);color:var(--muted)}
 .ok{color:var(--ok)} .bad{color:var(--bad)} .warn{color:var(--warn)}
 .note{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 12px;font-size:12.5px;color:#c9d1d9;margin:10px 0}
 .note.warnbox{border-color:var(--warn);background:#241f10}
 footer{border-top:1px solid var(--line);padding:12px 20px;color:var(--muted);font-size:11.5px}
 code{background:#0b0f14;padding:1px 5px;border-radius:4px}
</style></head>
<body>
<header>
 <h1>四组对照 · A / B / C / D</h1>
 <div class="sub">夜跑消融四组并排 · <b>只读证据</b>（不改世界层）· 两版口径<b>分套、不混</b></div>
 <div class="switcher" id="sw"></div>
</header>
<main>
 <div class="caliber" id="caliber">口径标注</div>
 <div id="tblwrap"></div>
 <h2 id="diffhead">事件类型差异（相对 A）</h2>
 <div id="diffs"></div>
 <h2>每组结论</h2>
 <div id="concl"></div>
 <h2>结论（逐条对齐早报，含限定词）</h2>
 <div id="conclusions"></div>
 <div class="note" id="notes"></div>
</main>
<footer id="foot"></footer>
<script>
const DATA = /*__DATA__*/;
let CAL = (new URLSearchParams(location.search).get("cal")==="d2") ? "d2" : "d1";
function esc(s){return String(s).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));}
function fmt(n){return (n==null)?"—":Number(n).toLocaleString("en-US");}
function delta(a,b){const d=(b==null||a==null)?null:b-a; if(d===null)return""; const s=d>0?"+":""; return `<span class="${d>0?'ok':(d<0?'bad':'')}">${s}${fmt(d)}</span>`;}

function renderSw(){
 const sw=document.getElementById("sw");
 const items=[["d1",DATA.d1.label],["d2",DATA.d2.label]];
 sw.innerHTML=items.map(([k,l])=>`<button data-k="${k}" class="${k===CAL?'active':''}">${esc(l)}</button>`).join("");
 sw.querySelectorAll("button").forEach(b=>b.onclick=()=>{CAL=b.dataset.k;render();});
}
function render(){
 document.getElementById("caliber").textContent = CAL==="d1"
   ? "当前口径：" + DATA.d1.label + "（" + DATA.d1.runtime + "）"
   : "当前口径：" + DATA.d2.label;
 document.getElementById("foot").innerHTML =
   (CAL==="d1"
     ? "数据源：<code>"+esc(DATA.d1.source)+"</code> · <b>源文件 sha256(前16) "+esc(DATA.file_shas.report)+"</b>"
     : "数据源(权威)：<code>"+esc(DATA.d2.source)+"</code> · <b>源文件 sha256(前16) "+esc(DATA.file_shas.t310)+"</b>；参考：<code>"+esc(DATA.d2.aux_source)+"</code> sha256(前16) "+esc(DATA.file_shas.t292))
   + " · 页面生成时 HEAD <b>"+esc(DATA.sha)+"</b>（≠数据源版本）· 只读证据、不改世界层 · 结论不超出早报/证据";
 if(CAL==="d1") renderD1(); else renderD2();
}
function renderD1(){
 const g=DATA.d1.groups;
 const rows=["A","B","C","D"].map(k=>{const x=g[k];
   return `<tr><td><b>${esc(x.name)}</b></td><td class="mono">${esc(x.sw)}</td><td class="ok">${esc(x.status)}</td>
   <td class="num">${fmt(x.events)}</td><td class="num">${fmt(x.llm)}</td><td class="num">${esc(x.rss)}</td><td class="num">${esc(x.time)}</td>
   <td class="mono">${esc(x.fp)}</td><td class="mono">${esc(x.sh)}</td></tr>`;}).join("");
 document.getElementById("tblwrap").innerHTML =
  `<table><thead><tr><th>组</th><th>开关</th><th>状态</th><th>事件数</th><th>LLM_CALL</th><th>峰值RSS</th><th>耗时</th><th>指纹</th><th>state_hash</th></tr></thead><tbody>${rows}</tbody></table>`;
 document.getElementById("diffhead").textContent = DATA.d1.diff_head;
 document.getElementById("diffs").innerHTML = ["B","C","D"].map(k=>
   `<div><b>${esc(g[k].name)}</b> <span class="tag">vs A</span><ul>${DATA.d1.diffs[k].map(t=>`<li>${esc(t)}</li>`).join("")}</ul></div>`).join("");
 document.getElementById("concl").innerHTML = ["A","B","C","D"].map(k=>`<div class="concl"><b>${esc(g[k].name)}</b>：${esc(DATA.d1.concl[k])}</div>`).join("");
 document.getElementById("conclusions").innerHTML = `<ol>
   <li>★ 第一条真实消融效应：<b>关掉睡眠/遗忘/人格三族（C）→ 事件 301,384 → 151,968（≈ 半）</b> ⇒ T244 三族贡献约一半事件量。</li>
   <li>世界导演（B）——口径修正（依 T289）：不能用"B≈A 事件数"当剂量证据；A/B 类型差异超出 director 的 2 条，且 B 反比 A 多 11 条 ⇒ 根因=每批独立 freeze_cache + 真 LLM ⇒ 首跑轨迹分叉的跨批噪声，淹没小剂量信号。稳健剂量证据=直接计数：A WORLD_DIRECTIVE/GROUP=1，<b>B=0</b>（84 回合只介入 1 次），且属 _NOOP_TYPES ⇒ 旁白型，非 D3 要的宏观群体事件。</li>
   <li>80–90 min 跑满 84 回合（远快于预估 2.5–3.3h）。成因【未验证】：疑端点更快 + T264 可见性索引；未做单变量隔离，<b>不作结论</b>。</li></ol>
   <div class="note"><b>诚实缺口（早报 §3）：</b>① collect 状态误判（以日志末行 round==target / rc=0 / RUN_END 为准）② 流水线一次起 4 批（与排班口径不符，结果无损）③ meta.ended_at/fingerprint 依赖 collect 回填。</div>`;
 document.getElementById("notes").innerHTML = DATA.d1.notes.map(t=>"· "+esc(t)).join("<br/>");
}
function renderD2(){
 const g=DATA.d2.groups, aux=DATA.d2.aux||{}, A=g.A, keys=Object.keys(A.type_counts||{});
 const order=["A","B","D"].filter(k=>g[k]);            // 主表=t310（分进程·权威）；t310 无 C
 const rows=order.map(k=>{const x=g[k];
   return `<tr><td><b>${k}</b> <span class="tag">${esc(Object.keys(x.override||{}).join(",")||"-")}</span></td>
   <td class="num">${fmt(x.events)}</td><td class="num">${fmt(x.llm_calls)}</td><td class="num">${fmt(x.cached)}</td>
   <td class="num">${x.secs!=null?(x.secs/60).toFixed(1)+"m":"—"}</td>
   <td class="mono">${esc((x.fingerprint||"").replace("sha256:","").slice(0,8))}</td>
   <td class="mono">${esc((x.state_hash||"").replace("sha256:","").slice(0,8))}</td></tr>`;}).join("")
  + `<tr><td><b>C</b> <span class="tag warn">T310 未覆盖</span></td><td class="num">—</td><td class="num">—</td><td class="num">—</td><td class="num">—</td><td class="mono">—</td><td class="mono">—</td></tr>`;
 document.getElementById("tblwrap").innerHTML =
  `<table><thead><tr><th>组 / 开关</th><th>事件数</th><th>LLM_CALL</th><th>cached</th><th>耗时</th><th>指纹</th><th>state_hash</th></tr></thead><tbody>${rows}</tbody></table>
   <div class="note warnbox">⚠️ <b>口径纪律（最重要）：t310 与 t292 的 A/B 绝对值不可直接比</b> —— 树 63c200a ≠ 8680737，A 301,332→292,141 的差是<b>树前进（T298 行为变）</b>、<b>非装置/性能收益</b>；<b>两处 B−A 都 = −2</b>（这才是稳健结论）。权威 = <code>t310</code>（分进程）；<b>C 未被 T310 覆盖</b> ⇒ 不填（<b>不拿 t292 的 C 去补</b>）；本口径未记录峰值 RSS。</div>`;
 document.getElementById("diffhead").textContent = "事件类型差异（相对 A，按类型）· 口径②（t310）";
 const diffs=[];
 for(const k of order){ if(k==="A")continue; const x=g[k]; const arr=[];
   for(const t of keys){const a=A.type_counts[t]||0,b=x.type_counts[t]||0; if(b!==a) arr.push([t,a,b]);}
   for(const t of Object.keys(x.type_counts)) if(!(t in A.type_counts)) arr.push([t,0,x.type_counts[t]]);
   arr.sort((p,q)=>Math.abs(q[2]-q[1])-Math.abs(p[2]-p[1]));
   diffs.push(`<div><b>${k}</b> <span class="tag">vs A</span> 差异类型 ${arr.length} 个<ul>`+
     arr.slice(0,12).map(([t,a,b])=>`<li class="mono">${esc(t)}: ${fmt(a)} → ${fmt(b)} (${delta(a,b)})</li>`).join("")+
     (arr.length>12?`<li class="mono">… 另 ${arr.length-12} 类</li>`:"")+`</ul></div>`);
 }
 document.getElementById("diffs").innerHTML = diffs.join("");
 document.getElementById("concl").innerHTML =
  `<div class="concl"><b>B 关世界导演</b>：WORLD_DIRECTIVE/GROUP 1→0（84 回合只介入 1 次）⇒ 旁白型；<b>B−A = −2</b>。</div>
   <div class="concl"><b>D 开双时钟</b>：WAKE 出现（${fmt((g.D.type_counts||{}).WAKE)}）；IDLE ${fmt((g.D.type_counts||{}).IDLE)}。</div>
   <div class="concl"><b>C</b>：<span class="warn">T310 未覆盖</span>（见备注）。</div>`;
 // 备注：t292 = 参考（已被 T310 取代），标注不删
 const auxk=Object.keys(aux);
 const auxnote = auxk.length ? `<div class="note">参考/备注（<code>${esc(DATA.d2.aux_source)}</code>，<b>已被 T310 取代</b>；标注不删）：`+
   auxk.map(k=>`${k} ${fmt(aux[k].events)}`).join(" · ")+`。历史事实：<b>t292 那次 C 未被真正关掉</b>（C≡A）⇒ 机制缺口已修 <code>T297b</code>（这是后来重跑确认的原因）。</div>`:"";
 document.getElementById("conclusions").innerHTML =
  `<ol><li>口径② = <b>分进程</b>复跑；<b>权威 = t310（A/B/D）</b>，<b>B−A = −2</b>（稳健结论）。</li>
   <li>t292 与 t310 的 A/B 绝对值<b>不可直接比</b>：树 63c200a ≠ 8680737，A 301,332→292,141 的差是<b>树前进（T298 行为变）</b>，非装置——别把绝对值变小当收益。</li></ol>`+
   `<div class="note">${(DATA.d2.notes||[]).map(esc).join("<br/>")}</div>`+auxnote;
 document.getElementById("notes").innerHTML = "";
}
renderSw(); render();
document.body.dataset.ready="1";
</script>
</body></html>
"""


if __name__ == "__main__":
    sys.exit(main())
