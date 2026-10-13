#!/usr/bin/env python3
"""T344 独立对账：fourgroups.html 的数字 vs 源文件（口径①早报 / 口径②json）。
只读。运行：cd repo && python3 v2/evidence/t344_fourgroups_reconcile.py
"""
import json, re, os, subprocess, sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HTML = os.path.join(REPO, "code", "frontend", "fourgroups.html")
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
def eq(label, got, want):
    if str(got) != str(want):
        diffs.append(f"{label}: 页面={got!r} 源={want!r}")

# ---------- 口径① vs 早报 §1 ----------
rep = open(REPORT, encoding="utf-8").read()
rows = re.findall(r"^\|\s*(\*{0,2})([ABCD])\s.*?\|\s*(.*?)\s*\|.*?\|\s*([\d,]+)\s*\|\s*(\d+)\s*\|\s*(\d+MB)\s*\|\s*([^|]+)\|\s*`([0-9a-f]{8})`\s*\|\s*`([0-9a-f]{8})`\s*\|", rep, re.M)
if not rows:
    # 备用：逐行解析
    for line in rep.splitlines():
        mm = re.match(r"\|\s*\**([ABCD])[^|]*\|[^|]*\|[^|]*\|\s*\**([\d,]+)\**\s*\|\s*(\d+)\s*\|\s*(\d+MB)\s*\|\s*([^|]+)\|\s*`([0-9a-f]{8})`\s*\|\s*`([0-9a-f]{8})`", line)
        if mm:
            rows.append((mm.group(1), None, None, mm.group(2), mm.group(3), mm.group(4), mm.group(5), mm.group(6), mm.group(7)))
print(f"\n[口径①] 早报解析到 {len(rows)} 行")
for r in rows:
    g = r[1] if len(r) == 9 else r[0]
    ev = r[-5] if len(r) == 9 else r[3]
    llm = r[-4] if len(r) == 9 else r[4]
    rss = r[-3] if len(r) == 9 else r[5]
    tm = r[-2] if len(r) == 9 else r[6]
    fp = r[-1] if len(r) == 9 else r[7]
    sh = r[-0] if False else (r[-1] if len(r) == 9 else r[7])
    # 规范：line-based rows have 9 groups (g,name,sw,ev,llm,rss,time,fp,sh)? handled below
for line in rep.splitlines():
    mm = re.match(r"\|\s*\**(A|B|C|D)[^|]*\|[^|]*\|[^|]*\|\s*\**([\d,]+)\**\s*\|\s*(\d+)\s*\|\s*(\d+MB)\s*\|\s*([^|]+)\|\s*`([0-9a-f]{8})`\s*\|\s*`([0-9a-f]{8})`", line)
    if not mm:
        continue
    g, ev, llm, rss, tm, fp, sh = mm.groups()
    ev = int(ev.replace(",", ""))
    x = DATA["d1"]["groups"][g]
    eq(f"①{g}.events", x["events"], ev)
    eq(f"①{g}.llm", x["llm"], int(llm))
    eq(f"①{g}.rss", x["rss"], rss)
    eq(f"①{g}.fp", x["fp"], fp)
    eq(f"①{g}.sh", x["sh"], sh)
    tmin = re.search(r"\((\d+)m\)", tm)
    if tmin:
        eq(f"①{g}.time", x["time"], tmin.group(1) + "m")

# ---------- 口径② vs t292 / t310 ----------
t292 = json.load(open(T292, encoding="utf-8"))
t310 = json.load(open(T310, encoding="utf-8"))
print(f"\n[口径②] t292 组={sorted(t292)} ; t310 组={sorted(t310)}")
for g in ["A", "B", "C", "D"]:
    if g not in t292:
        continue
    src = t292[g]; pg = DATA["d2"]["groups"].get(g, {})
    for f in ["events", "llm_calls", "cached", "fingerprint", "state_hash"]:
        eq(f"②{g}.{f}", pg.get(f), src.get(f))
    if src.get("secs") is not None and pg.get("secs") is not None:
        eq(f"②{g}.secs", round(pg["secs"], 1), round(src["secs"], 1))
    # type_counts 全量
    if pg.get("type_counts") is not None:
        eq(f"②{g}.type_counts", json.dumps(pg["type_counts"], sort_keys=True), json.dumps(src["type_counts"], sort_keys=True))
for g in sorted(t310):
    src = t310[g]; pg = DATA["d2"].get("t310", {}).get(g, {})
    eq(f"②t310.{g}.events", pg.get("events"), src.get("events"))
    eq(f"②t310.{g}.state_hash", pg.get("state_hash"), src.get("state_hash"))

# ---------- 可追溯：sha 真实 ----------
def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True).stdout.strip()
sha = DATA["sha"]
typ = git("cat-file", "-t", sha)
print(f"\n[可追溯] DATA.sha={sha} 类型={typ or '不存在'}")
if not typ:
    diffs.append(f"sha '{sha}' 不是真实提交")
# 页面提交 2f1361a 是否存在于历史
page_commit = git("log", "--oneline", "-1", "--format=%H", "2f1361a")
eq("页面提交存在(2f1361a)", bool(page_commit), True)
# 早报声明的冻结 sha & 指纹
eq("① 冻结sha(notes)", "6a5f14e" in " ".join(DATA["d1"]["notes"]), True)
# source 文件存在
for k, p in [("d1", REPORT), ("d2", T292)]:
    eq(f"{k}.source存在", os.path.exists(os.path.join(REPO, DATA[k]["source"])), True)

print("\n==== 差异清单 ====")
if diffs:
    for d in diffs:
        print("  ✗ " + d)
    print(f"共 {len(diffs)} 处差异")
else:
    print("  0 处差异（N/N 全等）")
