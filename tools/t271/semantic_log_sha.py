#!/usr/bin/env python3
"""世界语义投影 sha256（v2：重算哈希链）—— 本门回答『续跑有没有改变【世界语义】』，
不比本地 freeze 缓存命中状态。依据：Leader 2026-10-12 裁定 T299；见 runbook §4。

排除（**白名单式**，仅这 4 个，且仅在 LLM_CALL.payload 内）：
    cached / tokens_in / tokens_out / cost_units
保留（语义/审计字段，其余全部参与比较）：
    cache_key / prompt_hash / meta_digest / engine_version / provider / purpose /
    model / priority / tier / thinking / degraded / TURN_SEAL.state_hash ... 等

【白名单维护规则（T307-i）】
    `EXCLUDE` 是**白名单**，其错误两个方向都致命：
      · 新增【纯计量】字段未入表 ⇒ **假红**（把无关差异当语义差异）；
      · 【语义/配置】字段误入表 ⇒ **假绿**（掩盖真缺陷）。
    ⇒ **规则**：新增**纯计量**字段**必须**同步加入 `EXCLUDE` **并重跑 `--selftest`（A/B 两向）**；
      **语义/配置字段不得加入**。
    ⇒ **如何判"纯计量"**：该字段**只影响本地 freeze 缓存命中 / 计费**（如 `cached`/`tokens_*`/`cost_units`），
      **不影响 world 语义**（不入 `state_hash`、不改变事件流/前向态）。凡拿不准 ⇒ 一律**不排（保留）**。

【为什么"重算链"而不是"简单删字段"】(Leader 预判正确，已由代码证实)
    record["hash"] = compute_event_hash(整条记录含 payload)  （engine/ledger.py:24）
    TURN_SEAL.payload.last_hash = ledger.last_hash() = 上一条记录的 hash（engine/kernel.py:239）
    ⇒ 计量字段在【发射时】已进哈希链 ⇒ 只删"显示层 payload 的 4 字段"不会改写已存的
      hash/prev_hash/last_hash ⇒ 简单删字段的投影仍会报红（不充分）。
    ⇒ 本工具对【规范化后的事件】【重算】prev_hash / hash / TURN_SEAL.last_hash
      （复用引擎 compute_event_hash + canonical_json）⇒ "语义相同 ⇒ 规范化链相同"。
    ⇒ 因此【不排除 last_hash、不靠断言】—— 走的正是"规范化后自然相等"。

用法：
    T271_CODE=<code_dir> semantic_log_sha.py <log> [<log> ...]   # 打印语义投影 sha256
    T271_CODE=<code_dir> semantic_log_sha.py --selftest [<log>]  # A:删计量不变 / B:钉死扰动须变 / 合成样本须压到链级联
    T271_CODE=<code_dir> semantic_log_sha.py --selftest-missing-pin  # 负向用例: 缺字段必须报错 rc=2 (CLI 可直接触发)
"""
from __future__ import annotations
import sys, os, json, hashlib, copy, tempfile

EXCLUDE = {"cached", "tokens_in", "tokens_out", "cost_units"}
CODE = os.environ.get("T271_CODE", "/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/code")
# --- 钉死的语义扰动（T307-ii）：明确类型/字段/增量，跨版本可重复；缺失则报错，不静默换靶 ---
PIN_TYPE = "PLACE_MOVE"
PIN_FIELD = "day"
PIN_DELTA = +1


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


def _cascade(recs):
    """链级联覆盖：存在 LLM_CALL 紧跟 TURN_SEAL（后者 last_hash == 前者 hash）。"""
    for i in range(len(recs) - 1):
        if recs[i].get("type") == "LLM_CALL" and recs[i + 1].get("type") == "TURN_SEAL":
            return True
    return False


def _mk(recs, prev, rnd, phase, actor, typ, payload, ceh):
    seq = len(recs)
    r = {"seq": seq, "round": rnd, "phase": phase, "actor": actor, "type": typ,
         "payload": payload, "mono_ts": seq, "prev_hash": prev}
    r["hash"] = ceh(r)
    recs.append(r)
    return r["hash"]


def build_cascade_sample(ceh, gen, include_pin=True):
    """构造【保证压到哈希链级联】的合成样本：LLM_CALL 紧跟 TURN_SEAL。
    include_pin=False 时**不含 PIN 字段** —— 供负向用例，使"缺字段报错(rc=2)"分支**可达**
    （与搜索常量解耦，避免"存在但从未被走到"）。"""
    recs = []
    prev = _mk(recs, gen, 0, 0, "SYSTEM", "WORLD_INIT",
               {"seed": 1, "fingerprint": "sha256:" + "a" * 64,
                "config_digest": "sha256:" + "b" * 64, "config_components": {}}, ceh)
    if include_pin:
        prev = _mk(recs, prev, 0, 1, "P001", PIN_TYPE,
                   {"agent_id": "P001", PIN_FIELD: 3, "place": "park"}, ceh)
    prev = _mk(recs, prev, 0, 2, "SYSTEM", "LLM_CALL",
               {"purpose": "judge", "provider": "mock", "model": "mock-1",
                "cached": False, "tokens_in": 8, "tokens_out": 8, "cost_units": 0,
                "cache_key": "sha256:" + "c" * 64, "engine_version": "sha256:" + "a" * 64}, ceh)
    prev = _mk(recs, prev, 0, 3, "SYSTEM", "TURN_SEAL",
               {"round": 0, "state_hash": "sha256:" + "d" * 64, "last_hash": prev}, ceh)
    return recs


def selftest(path=None, include_pin=True):
    ceh, cj, gen = _engine()
    fd, tmp = tempfile.mkstemp(suffix=".jsonl"); os.close(fd)

    def write(rs):
        with open(tmp, "w", encoding="utf-8") as f:
            for r in rs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 合成样本（保证压到级联；include_pin=False 用于负向用例）+ 真日志（可选，仅 info）
    syn = build_cascade_sample(ceh, gen, include_pin=include_pin)
    write(syn)
    syn_orig = sem_sha(tmp, ceh, cj, gen)

    # A) 改【计量字段】-> 语义投影必须【不变】（且合成样本保证覆盖链级联）
    a = copy.deepcopy(syn)
    i = next(k for k, r in enumerate(a) if r["type"] == "LLM_CALL")
    p = a[i]["payload"]
    p["cached"] = not p.get("cached"); p["tokens_in"] = 12345
    p["tokens_out"] = 6789; p["cost_units"] = 42
    write(a)
    A_ok = sem_sha(tmp, ceh, cj, gen) == syn_orig
    casc = _cascade(syn)

    # B) 钉死【PLACE_MOVE.day】+1（单值、不改结构）-> 语义投影必须【变】；字段缺失=报错
    b = copy.deepcopy(syn)
    j = next((k for k, r in enumerate(b)
              if r.get("type") == PIN_TYPE and PIN_FIELD in (r.get("payload") or {})), None)
    if j is None:
        os.unlink(tmp)
        print(f"[selftest] ERROR: 钉死扰动字段 {PIN_TYPE}.{PIN_FIELD} 在样本中缺失 -> 报错（不静默换靶）")
        return 2
    b[j]["payload"][PIN_FIELD] = b[j]["payload"][PIN_FIELD] + PIN_DELTA
    write(b)
    B_ok = sem_sha(tmp, ceh, cj, gen) != syn_orig
    os.unlink(tmp)

    info = ""
    if path and os.path.exists(path):
        try:
            rr = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
            info = f" | 真日志 {os.path.basename(path)} 链级联覆盖={_cascade(rr)}(仅info; 若 False=样本未覆盖链, 非红)"
        except Exception as e:
            info = f" | 真日志读取失败: {type(e).__name__}"

    ok = A_ok and B_ok and casc   # 合成样本【必须】压到链级联，否则=门覆盖失败(红)
    print(f"[selftest] 合成样本: A 删计量不变={A_ok}  链级联覆盖={casc}(须True)  "
          f"B 钉死扰动 {PIN_TYPE}.{PIN_FIELD}{PIN_DELTA:+d} 变={B_ok}{info}")
    if not casc:
        print("  ✗ 链覆盖失败（合成样本未压到 LLM_CALL->TURN_SEAL 级联）= 红")
    return 0 if ok else 1


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--selftest":
        sys.exit(selftest(args[1] if len(args) > 1 else None))
    if args and args[0] == "--selftest-missing-pin":
        # 负向用例：构造【不含 PIN 字段】的样本 -> 期望 selftest 走"缺字段报错"分支 rc=2
        rc = selftest(None, include_pin=False)
        if rc == 2:
            print("[selftest-missing-pin] 用例通过：缺字段按预期报错 rc=2（分支可达且行为正确）")
            sys.exit(0)
        print(f"[selftest-missing-pin] 用例失败：意外 normal（rc={rc} ≠ 2）—— 缺字段分支未按预期报错")
        sys.exit(1)
    ceh, cj, gen = _engine()
    for p in args:
        print(sem_sha(p, ceh, cj, gen), p)
