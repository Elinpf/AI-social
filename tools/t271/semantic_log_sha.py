#!/usr/bin/env python3
"""世界语义投影 sha256（v2：重算哈希链）—— 本门回答『续跑有没有改变【世界语义】』，
不比本地 freeze 缓存命中状态。依据：Leader 2026-10-12 裁定 T299；见 runbook §4。

排除（白名单式，仅这 4 个，且仅在 LLM_CALL.payload 内）：
    cached / tokens_in / tokens_out / cost_units
保留（语义/审计字段，其余全部参与比较）：
    cache_key / prompt_hash / meta_digest / engine_version / provider / purpose /
    model / priority / tier / thinking / degraded / TURN_SEAL.state_hash ... 等

【为什么"重算链"而不是"简单删字段"】(Leader 预判正确，已由代码证实)
    record["hash"] = compute_event_hash(整条记录含 payload)  （engine/ledger.py:24）
    TURN_SEAL.payload.last_hash = ledger.last_hash() = 上一条记录的 hash（engine/kernel.py:239）
    ⇒ 计量字段在【发射时】已进哈希链 ⇒ 只删"显示层 payload 的 4 字段"不会改写已存的
      hash/prev_hash/last_hash，两路的链仍不等 ⇒ 简单删字段的投影仍会报红（不充分）。
    ⇒ 本工具对【规范化后的事件】【重算】prev_hash / hash / TURN_SEAL.last_hash
      （复用引擎 compute_event_hash + canonical_json）⇒ "语义相同 ⇒ 规范化链相同"。
    ⇒ 因此【不排除 last_hash、不靠断言】—— 走的正是"规范化后自然相等"。

用法：
    T271_CODE=<code_dir> semantic_log_sha.py <log> [<log> ...]   # 打印语义投影 sha256
    T271_CODE=<code_dir> semantic_log_sha.py --selftest <log>    # 双条件：删计量=>不变；改语义=>变
"""
from __future__ import annotations
import sys, os, json, hashlib, copy, tempfile

EXCLUDE = {"cached", "tokens_in", "tokens_out", "cost_units"}
CODE = os.environ.get("T271_CODE", "/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/code")


def _engine():
    if CODE not in sys.path:
        sys.path.insert(0, CODE)
    from engine.events import compute_event_hash, GENESIS_HASH
    from engine.canon import canonical_json
    return compute_event_hash, canonical_json, GENESIS_HASH


def _normalize(rec, prev):
    norm = dict(rec)
    p = dict(norm.get("payload") or {})
    if norm.get("type") == "LLM_CALL":
        for k in EXCLUDE:
            p.pop(k, None)
    if norm.get("type") == "TURN_SEAL" and "last_hash" in p:
        p["last_hash"] = prev          # 规范化后的前驱 hash（重算链）
    norm["payload"] = p
    norm["prev_hash"] = prev            # 规范化后的前驱 hash（重算链）
    norm.pop("hash", None)
    return norm


def sem_sha(path, ceh=None, cj=None, genesis=None):
    if ceh is None:
        ceh, cj, genesis = _engine()
    prev = genesis
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for line in f.read().split(b"\n"):
            s = line.strip()
            if not s:
                continue
            try:
                rec = json.loads(s)
            except Exception:
                h.update(s + b"\n"); continue
            norm = _normalize(rec, prev)
            nh = ceh(norm)
            full = dict(norm); full["hash"] = nh
            h.update(cj(full).encode("utf-8") + b"\n")
            prev = nh
    return h.hexdigest()


def raw_sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def selftest(path):
    ceh, cj, gen = _engine()
    recs = [json.loads(l) for l in open(path, "rb").read().split(b"\n") if l.strip()]
    orig = sem_sha(path, ceh, cj, gen)
    fd, tmp = tempfile.mkstemp(suffix=".jsonl"); os.close(fd)

    def write(rs):
        with open(tmp, "w", encoding="utf-8") as f:
            for r in rs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # A) 只改【计量字段】-> 语义投影必须【不变】；并确认样本里确有 "LLM_CALL 后紧跟 TURN_SEAL" 的链级联
    a = copy.deepcopy(recs)
    i = next((k for k, r in enumerate(a) if r.get("type") == "LLM_CALL"), None)
    has_cascade = False
    if i is not None:
        p = a[i]["payload"]
        p["cached"] = not p.get("cached"); p["tokens_in"] = 12345
        p["tokens_out"] = 6789; p["cost_units"] = 42
        has_cascade = any(r.get("type") == "TURN_SEAL" for r in recs[i + 1:i + 40])
    write(a)
    A_ok = sem_sha(tmp, ceh, cj, gen) == orig

    # B) 最小【agent 决策】扰动（只改 1 个值、不改结构）-> 语义投影必须【变】（必要性）
    DECISION = {"NEED_UPDATE", "GOAL_PROGRESS", "RELATION_CHANGE", "ACTIVITY_STARTED",
                "ACTIVITY_COMPLETED", "PLACE_MOVE", "PRODUCE", "CONSUME", "SKILL_PRACTICE",
                "OFFER_CREATED", "MEMORY_WRITE", "MEMORY_FORGET"}
    b = copy.deepcopy(recs)
    j = key = jtype = None
    for k, r in enumerate(b):
        if r.get("type") in DECISION:
            p = r.get("payload") or {}
            kk = next((x for x in p if isinstance(p[x], (int, float)) and not isinstance(p[x], bool)), None)
            if kk is not None:
                j, key, jtype = k, kk, r.get("type"); break
    if j is None:  # fallback：首个"非结构性"记录
        for k, r in enumerate(b):
            if r.get("type") not in ("LLM_CALL", "TURN_SEAL", "WORLD_INIT", "AGENT_BORN", "TIME_MARK"):
                p = r.get("payload") or {}
                kk = next((x for x in p if isinstance(p[x], (int, float)) and not isinstance(p[x], bool)), None)
                if kk is not None:
                    j, key, jtype = k, kk, r.get("type"); break
    if j is not None:
        b[j]["payload"][key] = b[j]["payload"][key] + 1   # 最小决策扰动：单值 +1，不改结构
    write(b)
    B_ok = (j is not None) and (sem_sha(tmp, ceh, cj, gen) != orig)
    B_info = f"{jtype}.{key}" if j is not None else "NONE"
    os.unlink(tmp)
    print(f"[selftest] A 删计量不变={A_ok} (链级联覆盖={has_cascade})  B 改语义变={B_ok} (扰动={B_info})")
    return 0 if (A_ok and B_ok) else 1


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--selftest":
        sys.exit(selftest(args[1]))
    ceh, cj, gen = _engine()
    for p in args:
        print(sem_sha(p, ceh, cj, gen), p)
