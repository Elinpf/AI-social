#!/usr/bin/env python3
"""C-1 窗口（round 30–35）定向取证：两臂同口径对比。

窗口来源：`life/agent.py::_world_line` 只提「在期」世界事件，ctrl 的世界事件落在
round 30、窗口 [30,36)；因此 rounds 30–35 是本轮**唯一**可能承载「镇上的事」的区间。

口径说明（诚实边界，写在输出里）：
  - **exposure（暴露机会，可比）**：该臂在 rounds 30–35 内的 dialogue LLM 调用条数。
    ON 臂在这些调用里只要 `wv.location` 非空就会插入那一行 ⇒ 这是「有机会看到世界行」的分母。
  - **world_line_bits（内容剂量）**：世界事件是否落在同一 round / 同一 kind（事件层可比）。
  - **body_proxy（文案层代理，弱指标）**：消息正文里出现「镇/集市/市集/眼下/节庆/气氛/紧俏/供/灾/病/通告」等词的条数。
    该指标**对两臂都可能自然出现**（ctrl 也会说「镇上」），不是开关证据，只能作为粗抓手；
    真正的开关生效证据是 `prompt_diff_proof.txt` 与 `launch_evidence.txt` 的 /proc environ。

用法：cd v2/evidence && python3 run_worldline_c1_a1_n16r84_seed42/window_probe.py
"""
import collections
import json

A1 = "run_worldline_c1_a1_n16r84_seed42/run.jsonl"
CTRL = "run_worldline_c1_ctrl_n16r84_seed42/run.jsonl"
LO, HI = 30, 35
PROXY_WORDS = ("镇上", "镇里", "集市", "市集", "眼下", "节庆", "气氛", "紧俏", "供货",
               "灾", "闹了场病", "通告", "修公共设施", "外乡人", "大活动")
MSG_TYPES = ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP")


def probe(path, label):
    msg_by_type = collections.Counter()
    threads = collections.Counter()      # (type, thread_id)
    dialogue_calls = 0
    proxy_hits = []
    world_events = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        e = json.loads(line)
        r = e.get("round")
        t = e.get("type")
        if t in ("WORLD_DIRECTIVE", "WORLD_GROUP_EVENT"):
            p = e.get("payload") or {}
            world_events.append({"round": r, "type": t, "kind": p.get("kind"),
                                 "directed": p.get("directed"),
                                 "start_round": p.get("start_round", p.get("effective_from_round")),
                                 "end_round": p.get("end_round", p.get("expires_round")),
                                 "directive_id": p.get("directive_id") or p.get("event_id") or p.get("id"),
                                 "payload_keys": sorted(p.keys())})
        if not (LO <= r <= HI):
            continue
        if t == "LLM_CALL" and (e.get("payload") or {}).get("purpose") == "dialogue":
            dialogue_calls += 1
        if t in MSG_TYPES:
            msg_by_type[t] += 1
            threads[(t, (e.get("payload") or {}).get("thread_id"))] += 1
            body = (e.get("payload") or {}).get("body") or ""
            hit = [w for w in PROXY_WORDS if w in body]
            if hit:
                proxy_hits.append({"round": r, "type": t, "author": (e.get("payload") or {}).get("author"),
                                   "words": hit, "body": body[:80]})
    print(f"--- {label} ----")
    print(f"  窗口 rounds {LO}-{HI}：MSG 合计 {sum(msg_by_type.values())}"
          f"（{dict(msg_by_type)}）  线程数 {len(threads)}  dialogue LLM 调用 {dialogue_calls}")
    print(f"  窗口内正文含世界类词的消息：{len(proxy_hits)} 条")
    for h in proxy_hits[:10]:
        print(f"     r{h['round']} {h['type']} {h['author']} {'/'.join(h['words'])} :: {h['body']}")
    print(f"  全批世界事件：{len(world_events)} 条")
    for w in world_events:
        print(f"     {w}")
    print()
    return {"msgs": dict(msg_by_type), "threads": len(threads),
            "dialogue_calls": dialogue_calls, "proxy": len(proxy_hits),
            "world_events": world_events}


def main():
    c = probe(CTRL, "ctrl（OFF）")
    a = probe(A1, "a1（ON）")
    print("== 对照小结 ==")
    print(f"  dialogue 暴露机会：ctrl={c['dialogue_calls']} a1={a['dialogue_calls']}"
          f"（a1/ctrl={a['dialogue_calls'] / max(1, c['dialogue_calls']):.3f}）")
    print(f"  窗口消息数：ctrl={sum(c['msgs'].values())} a1={sum(a['msgs'].values())}")
    print(f"  窗口线程数：ctrl={c['threads']} a1={a['threads']}")
    print(f"  正文代理命中：ctrl={c['proxy']} a1={a['proxy']}（弱指标，见文件头口径说明）")
    print(f"  世界事件落点：ctrl={[(w['round'], w['kind'], w['type']) for w in c['world_events']]}")
    print(f"                a1  ={[(w['round'], w['kind'], w['type']) for w in a['world_events']]}")


if __name__ == "__main__":
    main()
