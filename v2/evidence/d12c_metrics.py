#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D12-C 读数器（照 d12c_reading_table.md 的口径，冻结；跑完只填数）

用法：python3 v2/evidence/d12c_metrics.py --run OFF=.../run.jsonl --run ON=.../run.jsonl \
        --out-json v2/evidence/d12c_metrics.json
输出：P1 具体性代理 / P2 第三方代理 / len_p50 / 结构三项 / paren_rate（观察）
"""
import argparse, json, re, statistics
from collections import defaultdict

DETAIL = [r"[0-9０-９一二三四五六七八九十百千万两]", r"[斤两把钱文斗升只条块张副担捆]",
          r"米|面|柴|油|盐|糖|布|木|铁|药|茶|酒|鸡|鱼|菜|糕|饼|书|笔|伞|鞋|绳|灯|碗|锅"]
PAREN = re.compile(r"[（(][^）)]{0,60}[）)]")
MSG = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")


def names():
    try:
        d = json.load(open('code/config/personas.json', encoding='utf-8'))
        return [str(p['display_name']).split('·')[-1] for p in d['personas']]
    except Exception:
        return []


def metrics(path):
    rows = []
    for line in open(path, encoding='utf-8'):
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get('type') not in MSG:
            continue
        rows.append(e)
    nm = names()
    n = len(rows)
    p1 = p2 = par = 0
    lens = []
    th = defaultdict(int)
    for e in rows:
        pl = e.get('payload') or {}
        b = pl.get('body') or ''
        speaker = pl.get('from') or pl.get('author')
        present = {speaker}
        if pl.get('to'):
            present.add(pl['to'])
        present.update(pl.get('participants') or [])
        p1 += any(re.search(x, b) for x in DETAIL)
        p2 += any(x in b and x not in present for x in nm)
        par += b.lstrip().startswith(("（", "("))
        lens.append(len(PAREN.sub('', b).strip()))
        tid = pl.get('thread_id') or f"legacy-{pl.get('msg_uid')}"
        th[tid] += 1
    lens.sort()
    sizes = sorted(th.values())
    turns = sizes[:]  # 单发线程算 1 轮
    return {"n_msgs": n,
            "P1_specificity_rate": round(100 * p1 / n, 2) if n else None,
            "P2_thirdparty_rate": round(100 * p2 / n, 2) if n else None,
            "paren_rate": round(100 * par / n, 2) if n else None,
            "len_p50": statistics.median(lens) if lens else None,
            "n_threads": len(th),
            "threads_p50": statistics.median(sizes) if sizes else None,
            "turns_A_p50": statistics.median(turns) if turns else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True)
    ap.add_argument("--out-json", required=True)
    a = ap.parse_args()
    out = {}
    for spec in a.run:
        arm, _, path = spec.partition("=")
        out[arm] = metrics(path)
    json.dump(out, open(a.out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2, sort_keys=True)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
