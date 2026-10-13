#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_dashboard.py — 生成「前端看板 v1」自包含 HTML（T343 批2）。

- 只读 obs 清单 `v2/evidence/t343-obs-manifest.json`（权威性/时效由 obs 定，本器不猜）+ 四组对照页。
- 输出 `code/frontend/dashboard.html`：左侧 5 区（实时世界 / 四组对照 / 基线 / 指标 / 证据索引），
  右侧内容区；**常驻口径角标**；**每视图标 来源文件 + sha + 时效**；自包含（数据内联，无构建/无联网）。
- 实时世界：iframe 跟随 `?live=<abs>&tail=1`（增量尾读）；四组对照：iframe `fourgroups.html`。

用法：python3 code/frontend/tools/gen_dashboard.py
"""
from __future__ import annotations
import json, subprocess, sys
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


HTML = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>青溪镇 · 前端看板 v1</title>
<style>
 :root{--bg:#0d1117;--panel:#161b22;--line:#30363d;--fg:#e6edf3;--muted:#8b949e;--accent:#58a6ff;--ok:#3fb950;--warn:#d29922;--bad:#f85149}
 *{box-sizing:border-box}
 html,body{height:100%}
 body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 -apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
 header{padding:9px 16px;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:14px;flex-wrap:wrap}
 header h1{margin:0;font-size:15px}
 .badge{font-size:12px;padding:2px 9px;border-radius:999px;border:1px solid var(--warn);color:var(--warn)}
 .badge.src{border-color:var(--line);color:var(--muted)}
 .wrap{display:grid;grid-template-columns:190px 1fr;height:calc(100% - 44px)}
 aside{border-right:1px solid var(--line);padding:10px;display:flex;flex-direction:column;gap:6px}
 aside button{text-align:left;background:var(--panel);border:1px solid var(--line);color:var(--fg);padding:9px 11px;border-radius:8px;cursor:pointer;font-size:13px}
 aside button.active{border-color:var(--accent);background:#1d2b3a}
 aside .hint{color:var(--muted);font-size:11px;margin-top:auto;line-height:1.4}
 main{overflow:auto;padding:0}
 iframe{width:100%;height:100%;border:0;display:block}
 .pane{padding:14px 18px}
 .paneinfo{color:var(--muted);font-size:12px;margin:0 0 10px}
 .card{background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:10px 12px;margin:8px 0}
 .card h3{margin:0 0 6px;font-size:13.5px}
 .kv{display:grid;grid-template-columns:120px 1fr;gap:2px 10px;font-size:12px}
 .kv .k{color:var(--muted)}
 .mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11.5px}
 .tag{display:inline-block;font-size:11px;padding:1px 7px;border-radius:5px;border:1px solid var(--line);margin-left:6px;color:var(--muted)}
 .tag.ok{color:var(--ok);border-color:#1f6f3a}.tag.warn{color:var(--warn);border-color:#6b5a1f}.tag.bad{color:var(--bad);border-color:#6e2a2a}
 code{background:#0b0f14;padding:1px 5px;border-radius:4px}
 .livebar{display:flex;gap:8px;align-items:center;padding:8px 12px;border-bottom:1px solid var(--line);background:var(--panel)}
 .livebar input{flex:1;background:#0b0f14;border:1px solid var(--line);color:var(--fg);border-radius:6px;padding:6px 8px;font-size:12px}
 .livebar button{background:#1d3b52;border:1px solid var(--accent);color:var(--fg);border-radius:6px;padding:6px 10px;cursor:pointer}
 .livewrap{display:flex;flex-direction:column;height:100%}
</style></head>
<body>
<header>
 <h1>青溪镇 · 前端看板 v1</h1>
 <span class="badge" id="calibadge">口径角标</span>
 <span class="badge src" id="srcbadge">来源</span>
</header>
<div class="wrap">
 <aside id="nav"></aside>
 <main id="main"></main>
</div>
<script>
const M = /*__MANIFEST__*/;
const SHA = /*__SHA__*/;
const QS = new URLSearchParams(location.search);
const LIVE = QS.get("live") || "/root/t271/runs/nightly/D/run.jsonl";
const ZONES = [["live","🎬 实时世界"],["four","📊 四组对照"],["baseline","🧭 基线"],["metrics","📈 指标"],["evidence","🗂 证据索引"]];
let ZONE = QS.get("z") || "live";
function esc(s){return String(s==null?"":s).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));}
function authTag(a){const c=/权威/.test(a)?"ok":(/作废/.test(a)?"bad":(/参考|过期/.test(a)?"warn":""));return a?`<span class="tag ${c}">${esc(a)}</span>`:"";}
function setCalib(c,s){document.getElementById("calibadge").textContent=c;document.getElementById("srcbadge").innerHTML="来源："+s;}
function renderNav(){document.getElementById("nav").innerHTML=ZONES.map(([k,l])=>`<button data-k="${k}" class="${k===ZONE?'active':''}">${l}</button>`).join("")+`<div class="hint">只读看板 · 数据权威性/时效由 obs 清单定 · 树 sha <b>${esc(SHA)}</b></div>`;
 document.querySelectorAll("#nav button").forEach(b=>b.onclick=()=>{ZONE=b.dataset.k;render();});}
function render(){
 renderNav();
 const main=document.getElementById("main");
 if(ZONE==="live"){
   setCalib("实时世界 · 增量尾读（/__tail）","live 路径（只读）");
   main.innerHTML=`<div class="livewrap"><div class="livebar">
      <span class="mono">live=</span><input id="lv" value="${esc(LIVE)}"/>
      <button id="go">跟随</button><span class="mono" style="color:var(--muted)">尾部窗口，非从头回放</span></div>
      <iframe id="fr" src="index.html?live=${encodeURIComponent(LIVE)}&tail=1&tailmb=4&view=default"></iframe></div>`;
   document.getElementById("go").onclick=()=>{const v=document.getElementById("lv").value.trim();document.getElementById("fr").src="index.html?live="+encodeURIComponent(v)+"&tail=1&tailmb=4&view=default";};
   return;
 }
 if(ZONE==="four"){ setCalib("四组对照 · 两版口径分套","v2/evidence/t292_shared_results.json + t310_results.json");
   main.innerHTML=`<iframe src="fourgroups.html"></iframe>`; return; }
 const section = ZONE==="baseline"?M.baseline : ZONE==="metrics"?M.metrics : M.evidence_index;
 const title = ZONE==="baseline"?"基线":ZONE==="metrics"?"指标":"证据索引";
 let srcline = (M.generated_at? ("obs 清单生成于 "+M.generated_at+" · tree_head_at_generation=+"+M.tree_head_at_generation):"");
 setCalib(title+" · 权威性/时效由 obs 清单标注", "v2/evidence/t343-obs-manifest.json");
 main.innerHTML=`<div class="pane"><p class="paneinfo">${esc(srcline)}${ZONE==="evidence"?" · display=可展示/内部件":""}</p>`+
   (ZONE==="baseline"?`<div class="card"><b>时效总提醒：</b>${esc((M.global_notes||[])[0]||"")}</div>`:"")+
   (section||[]).map(it=>{
     const rows=[["来源文件",it.source_file],["sha256(前16)",it.sha256_16],["生成时间",it.generated_ts],["口径",it.caliber],["KPI",it.kpi],["时效",it.freshness],["展示",it.display],["说明",it.note]]
       .filter(r=>r[1]);
     return `<div class="card"><h3>${esc(it.name)} ${authTag(it.authority)}</h3><div class="kv">`+
       rows.map(([k,v])=>`<div class="k">${k}</div><div>${k.includes("sha")||k==="来源文件"?`<span class="mono">${esc(v)}</span>`:esc(v)}</div>`).join("")+
       `</div></div>`;}).join("")+
   (ZONE==="baseline"&&(M.placeholders||[]).length?`<div class="card"><h3>待更新（T300）</h3>${(M.placeholders).map(p=>`<div>· ${esc(p)}</div>`).join("")}</div>`:"")+
   `</div>`;
}
render();
document.body.dataset.ready="1";
</script>
</body></html>
"""


def main() -> int:
    man = json.loads((EV / "t343-obs-manifest.json").read_text(encoding="utf-8")) if (EV / "t343-obs-manifest.json").exists() else {}
    sha = head_sha()
    html = HTML.replace("/*__MANIFEST__*/", json.dumps(man, ensure_ascii=False)).replace("/*__SHA__*/", json.dumps(sha))
    out = FRONTEND / "dashboard.html"
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out}  sha={sha}  baseline={len(man.get('baseline',[]))} metrics={len(man.get('metrics',[]))} evidence={len(man.get('evidence_index',[]))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
