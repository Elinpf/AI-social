#!/usr/bin/env python3
"""F-6 跨天记忆引用 · 零-LLM 链条证明（不跑新批，只读已有真 LLM 日志）。

复算 R20 / T-f6-measure 的 C1–C4 四项判据，并对 F-6 注入臂做结构分析。
用法（仓库根目录）：
    python3 v2/evidence/f6_chain_20261022/verify_chain.py
输出：stdout 可读报告（同时建议 tee 到 chain_out.txt）。

口径来源：
  - 事件/字段结构：code/life/memory.py, code/orchestration/integration.py, code/life/sleep_window.py
  - F-6 词表指标：tools/d5/dialogue_metrics.py:738，词表 tools/d5/timeref_lexicon.txt
  - F-6 注入臂：code/life/agent.py:1195-1297 (_memory_line) + :55-69 (memory_f6_enabled)
本脚本不写任何业务代码、不改任何状态，只读。
"""
import json, re, sys, subprocess, hashlib, os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

LOGS = [
    ("A5 (pre-fix)",  "v2/evidence/run_a5_real_n16r42_seed42/run.jsonl",
     "v2/evidence/run_a5_real_n16r42_seed42/switch_proof.txt"),
    ("D12A (post-fix)","v2/evidence/run_d12a_real_n16r24_seed42/run.jsonl",
     "v2/evidence/run_d12a_real_n16r24_seed42/switch_proof.txt"),
]

LEX = os.path.join(REPO, "tools/d5/timeref_lexicon.txt")


def sh(*args):
    try:
        return subprocess.run(args, cwd=REPO, capture_output=True, text=True).stdout.strip()
    except Exception:
        return ""


def git_ancestor(a, b):
    """a 是否为 b 的祖先（True/False/None-未知）。"""
    r = subprocess.run(["git", "merge-base", "--is-ancestor", a, b], cwd=REPO,
                       capture_output=True)
    if r.returncode == 0:
        return True
    if r.returncode == 1:
        return False
    return None


def load(p):
    return [json.loads(l) for l in open(os.path.join(REPO, p), encoding="utf-8") if l.strip()]


def switch_proof(p):
    d = {}
    for line in open(os.path.join(REPO, p), encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or "=" not in line:
            continue
        # "params seed=42 n=16 ..." 这类行：首个空格前是键名，后面是整串参数
        head = line.split(" ", 1)[0]
        if head == "params":
            d["params"] = line[len("params "):] if line.startswith("params ") else ""
            continue
        k, v = line.split("=", 1)
        d[k] = v
    return d


def readable(t, name_sub=True):
    """复刻 code/life/agent.py::_readable 的门（用于结构分析，name_sub 用占位替换 Pxxx）。"""
    s = (t or "").strip().replace("\n", " ")
    if not s:
        return None
    if name_sub:
        s = re.sub(r"P\d{3}", "阿某", s)
    s = s.replace(" 说：", "说：")
    if "事件" in s or re.search(r"[A-Za-z]{3,}", s):
        return None
    if re.search(r"[A-Z]{2,}", s):
        return None
    if len(re.sub(r"\s+", "", s)) < 6:
        return None
    return s


def main():
    lexicon = [w.strip() for w in open(LEX, encoding="utf-8")
               if w.strip() and not w.startswith("#")]
    lex_sha = hashlib.sha256(open(LEX, "rb").read()).hexdigest()
    print(f"repo={REPO}")
    print(f"timeref_lexicon sha256={lex_sha}  n_terms={len(lexicon)}")

    for tag, logp, swp in LOGS:
        print("\n" + "=" * 78)
        events = load(logp)
        sp = switch_proof(swp)
        code_sha = sp.get("code_sha", "?")
        print(f"[{tag}] log={logp}")
        print(f"  switch_proof: code_sha={code_sha} started={sp.get('started_at')} "
              f"branch={sp.get('branch')} params={sp.get('params')}")
        anc = git_ancestor("c01f6dd", code_sha) if code_sha not in ("?", "") else None
        print(f"  是否含修复 c01f6dd（ancestor?）: {anc}  "
              f"(True=修复后批次, False=修复前)")

        cons, retr, writes, msgs, dropped = [], [], {}, [], []
        sm_writes = set()
        for d in events:
            t = d.get("type"); p = d.get("payload") or {}
            if t == "MEMORY_CONSOLIDATE":
                cons.append(p)
            elif t == "MEMORY_RETRIEVE":
                retr.append(p)
            elif t == "MEMORY_WRITE":
                mid = str(p.get("mem_id"))
                writes[mid] = p
                if "-SM-" in mid:
                    sm_writes.add(mid)
            elif t in ("MSG_DM", "MSG_PUBLIC", "MSG_GROUP"):
                msgs.append(p)
            elif t == "DROPPED":
                # DROPPED payload 里"被丢弃的事件类型"键是 "type"（非 event_type）
                dropped.append((p.get("reason"), tuple(sorted(p.get("keys") or [])),
                                p.get("event_type") or p.get("type")))

        # ---- C1 CONSOLIDATE text ----
        text_ok = sum(1 for p in cons if (p.get("text") or "").strip())
        tmpl = sum(1 for p in cons if "聚合" in (p.get("text") or ""))
        drop_text = sum(1 for r, k, et in dropped
                        if r == "unknown_intent_field" and k == ("text",)
                        and et == "MEMORY_CONSOLIDATE")
        print(f"  C1 CONSOLIDATE n={len(cons)}  text非空={text_ok} "
              f"({(100*text_ok/len(cons) if cons else 0):.2f}%)  模板文本={tmpl}")
        print(f"     DROPPED[unknown_intent_field,keys=(text,),MEMORY_CONSOLIDATE]={drop_text}")

        # ---- C2 SM write ----
        kinds = {}
        for mid in sm_writes:
            kinds[writes[mid].get("kind")] = kinds.get(writes[mid].get("kind"), 0) + 1
        print(f"  C2 SM(MEMORY_WRITE mem_id含-SM-)唯一条数={len(sm_writes)}  kind分布={kinds}")
        # 交叉检查：CONSOLIDATE.produced_mem_id 去重 == SM write 去重
        produced = {p.get("produced_mem_id") for p in cons if p.get("produced_mem_id")}
        print(f"     交叉: CONSOLIDATE.produced_mem_id 去重={len(produced)}  "
              f"SM write 去重={len(sm_writes)}  相等={produced == sm_writes if sm_writes or produced else None}")
        # SM 写入按 day（跨天资格供给）
        sm_day = {}
        for mid in sm_writes:
            day = writes[mid].get("day")
            sm_day[day] = sm_day.get(day, 0) + 1
        print(f"     SM 写入按 day: {dict(sorted(sm_day.items(), key=lambda x:(x[0] is None, x[0])))}")

        # ---- C3 retrieve ----
        sel_ok = sum(1 for p in retr if p.get("selected_mem_ids"))
        sm_selected = set()
        for p in retr:
            for mid in (p.get("selected_mem_ids") or []):
                if "-SM-" in str(mid):
                    sm_selected.add(mid)
        print(f"  C3 RETRIEVE n={len(retr)}  selected非空={sel_ok} "
              f"({(100*sel_ok/len(retr) if retr else 0):.2f}%)  被选中的SM唯一条数={len(sm_selected)}"
              f"  选中SM⊆SM写入={sm_selected <= sm_writes}")

        # ---- C4 注入面 ----
        refs_ok = sum(1 for m in msgs if (m.get("ctx") or {}).get("memory_refs"))
        f6_env = sp.get("env_LIFE_PROMPT_MEMORY_F6") or "<unset>"
        print(f"  C4 MSG n={len(msgs)}  ctx.memory_refs非空={refs_ok}  "
              f"switch_proof env_LIFE_PROMPT_MEMORY_F6={f6_env}")

        # ---- F-6 timeref_rate (正文词表命中，官方口径复算) ----
        hit = tot = 0
        for m in msgs:
            tot += 1
            b = m.get("body") or ""
            if any(w in b for w in lexicon):
                hit += 1
        print(f"  F-6 timeref_rate = {hit}/{tot} = {(hit/tot if tot else 0):.6f} "
              f"(词表 sha {lex_sha[:12]}…)")

        # ---- 结构分析：SM 模板文本能否过 _readable ----
        if cons:
            pass_n = sum(1 for p in cons if readable(p.get("text")))
            print(f"  结构: SM 模板文本过 _readable 门 = {pass_n}/{len(cons)} "
                  f"(subject 分布见下)")
        # 跨天 observation 供给（day 分布）
        byday = {}
        for w in writes.values():
            if w.get("kind") == "observation":
                byday[w.get("day")] = byday.get(w.get("day"), 0) + 1
        print(f"  observation MEMORY_WRITE 按 day 分布: {dict(sorted(byday.items(), key=lambda x:(x[0] is None,x[0])))}")
        subj = {}
        for p in cons:
            subj[p.get("subject")] = subj.get(p.get("subject"), 0) + 1
        top = sorted(subj.items(), key=lambda x: -x[1])[:6]
        print(f"  CONSOLIDATE subject top6: {top}")


if __name__ == "__main__":
    main()
