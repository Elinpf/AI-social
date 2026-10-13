#!/usr/bin/env python3
"""T344 独立对账（v2：新布局）——fourgroups.html 数字 vs 源文件。
 口径①  ↔ 早报 nightly-20261012-morning-report.md
 口径② 权威 ↔ t310_results.json（d2.groups）
 口径② 参考 ↔ t292_shared_results.json（d2.aux，已被 T310 取代）
 file_shas ↔ 各源文件 sha256 前16
只读。运行：cd repo && python3 v2/evidence/t344_fourgroups_reconcile.py
"""
import json, re, os, subprocess, sys, hashlib

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HTML = os.environ.get("T344_HTML", os.path.join(REPO, "code", "frontend", "fourgroups.html"))
REPORT = os.path.join(REPO, "v2", "evidence", "nightly-20261012-morning-report.md")
T292 = os.path.join(REPO, "v2", "evidence", "t292_shared_results.json")
T310 = os.path.join(REPO, "v2", "evidence", "t310_results.json")

html = open(HTML, encoding="utf-8").read()
m = re.search(r"const DATA = (\{.*?\});\s*\nlet CAL", html, re.S)
if not m:
    print("FAIL: 未找到 DATA"); sys.exit(1)
DATA = json.loads(m.group(1))
print(f"DATA.sha = {DATA['sha']}")

diffs = []
N = 0
def eq(label, got, want):
    global N
    N += 1
    if str(got) != str(want):
        diffs.append(f"{label}: 页面={got!r} 源={want!r}")

def sha16(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]

FIELDS = ["events", "llm_calls", "cached", "fingerprint", "state_hash"]

# ---------- 口径① vs 早报 §1 ----------
rep = open(REPORT, encoding="utf-8").read()
n1 = 0
for line in rep.splitlines():
    mm = re.match(r"\|\s*\**(A|B|C|D)[^|]*\|[^|]*\|[^|]*\|\s*\**([\d,]+)\**\s*\|\s*(\d+)\s*\|\s*(\d+MB)\s*\|\s*([^|]+)\|\s*`([0-9a-f]{8})`\s*\|\s*`([0-9a-f]{8})`", line)
    if not mm:
        continue
    n1 += 1
    g, ev, llm, rss, tm, fp, sh = mm.groups()
    x = DATA["d1"]["groups"][g]
    eq(f"①{g}.events", x["events"], int(ev.replace(",", "")))
    eq(f"①{g}.llm", x["llm"], int(llm))
    eq(f"①{g}.rss", x["rss"], rss)
    eq(f"①{g}.fp", x["fp"], fp)
    eq(f"①{g}.sh", x["sh"], sh)
    t = re.search(r"\((\d+)m\)", tm)
    if t:
        eq(f"①{g}.time", x["time"], t.group(1) + "m")
print(f"[口径①] 早报匹配 {n1} 组（应 4）")

# ---------- 口径② 权威 vs t310（d2.groups）----------
t310 = json.load(open(T310, encoding="utf-8"))
t292 = json.load(open(T292, encoding="utf-8"))
grp = DATA["d2"].get("groups", {})
print(f"[口径②权威] t310 组={sorted(t310)} ; 页 d2.groups={sorted(grp)}（应无 C）")
eq("②权威.组集", sorted(grp), sorted(t310))
for g in sorted(t310):
    src = t310[g]; pg = grp.get(g, {})
    for f in FIELDS:
        eq(f"②权威{g}.{f}", pg.get(f), src.get(f))
    if src.get("secs") is not None and pg.get("secs") is not None:
        eq(f"②权威{g}.secs", round(pg["secs"], 1), round(src["secs"], 1))
    if pg.get("type_counts") is not None:
        eq(f"②权威{g}.type_counts", json.dumps(pg["type_counts"], sort_keys=True), json.dumps(src["type_counts"], sort_keys=True))

# ---------- 口径② 参考 vs t292（d2.aux）----------
aux = DATA["d2"].get("aux", {})
print(f"[口径②参考] t292 组={sorted(t292)} ; 页 d2.aux={sorted(aux)}")
eq("②参考.组集", sorted(aux), sorted(t292))
for g in sorted(t292):
    src = t292[g]; pg = aux.get(g, {})
    for f in FIELDS:
        eq(f"②参考{g}.{f}", pg.get(f), src.get(f))

# ---------- file_shas ↔ 源文件 sha256 前16 ----------
fs = DATA.get("file_shas", {})
print(f"[file_shas] {fs}")
eq("file_shas.report", fs.get("report"), sha16(REPORT))
eq("file_shas.t310", fs.get("t310"), sha16(T310))
eq("file_shas.t292", fs.get("t292"), sha16(T292))

# ---------- 可追溯 ----------
def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True).stdout.strip()
sha = DATA["sha"]
eq("DATA.sha 是真实提交", bool(git("cat-file", "-t", sha)), True)
for key in ["source", "aux_source"]:
    p = DATA["d2"].get(key)
    if p:
        eq(f"d2.{key}存在", os.path.exists(os.path.join(REPO, p)), True)
eq("d1.source存在", os.path.exists(os.path.join(REPO, DATA["d1"]["source"])), True)

print(f"\n==== 差异清单 | 比对 {N} 条 ====")
if N < 20:
    print(f"  ⚠️ 比对条数异常少({N}) —— 可能是静默未比（假绿）")
if diffs:
    for d in diffs:
        print("  ✗ " + d)
    print(f"共 {len(diffs)} 处差异")
    sys.exit(1)
else:
    print("  0 处差异（N/N 全等）")
