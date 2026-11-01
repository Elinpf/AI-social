"""L2b「通道接通计数门」工具：不看配置值，数**运行期真的进去了几次**。

清单来源：`v2/refs/D9z-launch-checklist.md` L2b。

## 为什么需要它
配置 `=1` 只证明环境变量存在；`/proc` 里 `grep '=1'` 有输出也只证明同一件事。
本工具改为在**验证进程**里 monkeypatch 各通道的**入口函数**，数调用次数，并给每个计数配**阳性对照**。

## 四条口径（每一条都对应一个已踩过的坑）
1. **patch 打在「调用方查找的位置」**：`life/agent.py` 以同模块全局名直接调用
   `narration_tail` / `narration_example` / `openings_clause` / `syntax_clause`，
   故必须 patch **`life.agent.<name>`**。若 patch 定义模块，计数恒 0 而机制在跑
   ⇒ 会把「`narration_example()==0`」误判成「短路成立」。
   本脚本**显式断言** patch 目标属于 `life.agent`，并做「patch 后强制调用一次、计数 0→1」的自检。
2. **`drop_s1` 记「真的让位」而非实参**：`syntax_clause(..., drop_s1=True)` 应返回**只含 S-2** 的串。
   双计 `drop_s1_true_calls` 与 `drop_s1_effective_calls`（返回串不含 `S1_CLAUSE`），**两者相等才算命中**。
3. **`openings_clause()` 按 `kind` 分组**：`narration_tail` 有 `initiate` / `reply` 两条路径，
   只报总数 >0 会掩盖其中一路全 0（"某一路没走"恰恰最该被发现）。
4. **`HITT_INTRA_ROUND_VISIBILITY` 双口径互证**：`Adapter._pending_view()` 返回非 `None` 的次数
   与 `VisibilityIndex.visible(extra≠空)` 的次数**必须相等**才叫"对得上"。

## verdict 只有两态（PASS / CANNOT-VERIFY）
**不得出现 PASS 而无阳性对照**：任何"分子为 0"的结论，必须先证明装置能出声
（外层调用数 > 0），否则一律 `CANNOT-VERIFY(未触达)`。
为避免把"明确的反例"伪装成"无法验证"，另给 `detail` 字段（`ok` / `not_reached` / `channel_off`
/ `zero_but_reached` / `mismatch`），`zero_but_reached` 与 `mismatch` 表示**实为不成立**。

## 用法（`code/` 目录下）
    python3 ../tools/d9z/channel_counts.py                # 双臂：全关 / 全开
    python3 ../tools/d9z/channel_counts.py --n 6 --rounds 4
    python3 ../tools/d9z/channel_counts.py --arm off      # 只跑一臂

**mock provider**（脚本内部强制 `pop("HITT_LLM_PROVIDER")`），不调真 LLM，不改 `code/` 任何文件。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (os.path.join(_ROOT, "code"), _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

#: DR 相关 env（仅 DR 臂使用；`off/on/mixed` 三臂不动它们）
DR_ENV_KEYS = ("HITT_DIALOGUE_REPAIR", "HITT_DR_REPAIR_ASK", "HITT_DR_RECORD_ONLY", "HITT_DR_PICK_MARK")

ENV_KEYS = (
    "LIFE_PROMPT_NARRATION",
    "LIFE_PROMPT_NARRATION_ROTATION",
    "LIFE_PROMPT_NARRATION_ACTION",
    "LIFE_PROMPT_NARRATION_SYNTAX",
    "LIFE_PROMPT_NARRATION_OPENINGS",
    "HITT_INTRA_ROUND_VISIBILITY",
)

# 打 patch 的目标：**必须是调用点模块属性**（life.agent.*）
#: 臂 → env 组合。`mixed` 故意只开 ROTATION 不开 OPENINGS，用来验证
#: "example==0 不可归因于 OPENINGS 短路"这条前提判断真的会拦人。
MODES = {
    "off": {},
    "on": {k: "1" for k in ENV_KEYS},
    "mixed": {
        "LIFE_PROMPT_NARRATION": "1",
        "LIFE_PROMPT_NARRATION_ROTATION": "1",
        "LIFE_PROMPT_NARRATION_SYNTAX": "1",
        "HITT_INTRA_ROUND_VISIBILITY": "1",
    },
    # ---- DR 两臂（T-DR-L2B-CHANNELS）：只开 DR，用来数 `context_line` / `repair_ask` ----
    # `dr_msg`：`enabled=1`、`repair_ask` 取默认三态 `null`（跟随 enabled）⇒ 两段都可能注入；
    # `dr_noask`：`enabled=1` + `repair_ask=0` ⇒ **动作要求那一段必须为 0（正向证据）**。
    "dr_msg": {"HITT_DIALOGUE_REPAIR": "1"},
    "dr_noask": {"HITT_DIALOGUE_REPAIR": "1", "HITT_DR_REPAIR_ASK": "0"},
}

PATCH_TARGETS = {
    "narration_tail": "life.agent.narration_tail",
    "narration_example": "life.agent.narration_example",
    "openings_clause": "life.agent.openings_clause",
    "syntax_clause": "life.agent.syntax_clause",
    "pending_view": "orchestration.integration.KernelAdapter._pending_view",
    "visibility_visible": "orchestration.visibility_index.VisibilityIndex.visible",
    # T-DR-L2B-CHANNELS：DR 两处提示词注入点（`agent.py` 里写的是 `DR.context_line(...)` /
    # `DR.repair_ask(...)`，`DR` 即 `life.dialogue_repair` 模块对象 ⇒ patch 该模块属性即调用点）
    "context_line": "life.dialogue_repair.context_line",
    "repair_ask": "life.dialogue_repair.repair_ask",
}


def _run_arm(mode: str, n: int, rounds: int, seed: int) -> dict:
    """在指定开关组合下跑一个 mock 世界，返回计数与 verdict。"""
    import life.agent as A
    import life.dialogue_repair as DRm
    from orchestration.integration import KernelAdapter, build_world
    from orchestration.visibility_index import VisibilityIndex

    # ---- 开关：全关 / 全开（只动这六个 env，其余配置一律不碰）----
    saved = {k: os.environ.get(k) for k in (ENV_KEYS + DR_ENV_KEYS)}
    os.environ.pop("HITT_LLM_PROVIDER", None)          # 强制 mock
    for k in (ENV_KEYS + DR_ENV_KEYS):
        os.environ.pop(k, None)
    for k, v in MODES[mode].items():
        os.environ[k] = v
    # ⚠ `dialogue_repair.load_params()` 有模块级 `_cache`：不清会让**第一臂**（off，enabled=False）
    # 的值被后续 dr_* 臂继承 ⇒ 出现"开了却 calls=0"的假象。每臂开始清一次。
    DRm._cache = None
    DRm.set_override(None)

    counts = {
        "narration_tail_calls": {"total": 0, "initiate": 0, "reply": 0, "other": 0},
        "narration_example_calls": 0,
        "openings_clause_calls": 0,
        "openings_clause_nonempty_calls": {"total": 0, "initiate": 0, "reply": 0, "other": 0},
        "syntax_clause_calls": 0,
        "syntax_drop_s1_true_calls": 0,
        "syntax_drop_s1_effective_calls": 0,
        "pending_view_calls": 0,
        "pending_view_non_none": 0,
        "visibility_visible_calls": 0,
        "visible_extra_nonempty": 0,
        # ---- T-DR-L2B-CHANNELS：DR 两条提示词通道 ----
        "context_line_calls": 0,
        "context_line_nonempty_calls": {"total": 0, "peer_nonempty": 0, "peer_empty": 0},
        # 阳性对照①：调用时**台账确实有旧账且 peer 非空**的次数（否则"非空为 0"分不清
        # "机制没接通"与"本来就没有旧账可叙"）
        "context_line_rifts_nonempty_calls": 0,
        "repair_ask_calls": 0,
        "repair_ask_nonempty_calls": 0,
        # 阳性对照②：调用时**台账里确有该线程旧账**的次数（`repair_ask=False` 的 0 要有它才成立）
        "repair_ask_rifts_nonempty_calls": 0,
    }
    ctx = {"kind": None, "tail": ""}       # 当前 narration_tail 的 kind / 其返回串

    orig = {
        "narration_tail": A.narration_tail,
        "narration_example": A.narration_example,
        "openings_clause": A.openings_clause,
        "syntax_clause": A.syntax_clause,
        "pending_view": KernelAdapter._pending_view,
        "visibility_visible": VisibilityIndex.visible,
        "context_line": DRm.context_line,
        "repair_ask": DRm.repair_ask,
    }

    # ---- ① patch 位置断言：这六个名字都必须存在于调用点模块上 ----
    patch_target_proof = {}
    for key, dotted in PATCH_TARGETS.items():
        mod_path, attr = dotted.rsplit(".", 1)
        mod = sys.modules.get(mod_path)
        patch_target_proof[key] = {
            "target": dotted,
            "module_imported": mod is not None,
            "has_attr": mod is not None and hasattr(mod, attr),
            "attr_is_callable": mod is not None and callable(getattr(mod, attr, None)),
        }
    for key in ("narration_tail", "narration_example", "openings_clause", "syntax_clause",
                "context_line", "repair_ask"):
        assert patch_target_proof[key]["has_attr"], f"patch 目标不存在于调用点：{PATCH_TARGETS[key]}"

    def w_narration_tail(kind, *a, **kw):
        prev = ctx["kind"]
        ctx["kind"] = kind
        try:
            out = orig["narration_tail"](kind, *a, **kw)
        finally:
            ctx["kind"] = prev
        ctx["tail"] = out
        counts["narration_tail_calls"]["total"] += 1
        counts["narration_tail_calls"][kind if kind in ("initiate", "reply") else "other"] += 1
        return out

    def w_narration_example(*a, **kw):
        counts["narration_example_calls"] += 1
        return orig["narration_example"](*a, **kw)

    def w_openings_clause(*a, **kw):
        counts["openings_clause_calls"] += 1
        out = orig["openings_clause"](*a, **kw)
        if out:
            counts["openings_clause_nonempty_calls"]["total"] += 1
            k = ctx["kind"] if ctx["kind"] in ("initiate", "reply") else "other"
            counts["openings_clause_nonempty_calls"][k] += 1
        return out

    def w_syntax_clause(*a, **kw):
        drop = bool(kw.get("drop_s1", a[3] if len(a) > 3 else False))
        out = orig["syntax_clause"](*a, **kw)
        counts["syntax_clause_calls"] += 1
        if drop:
            counts["syntax_drop_s1_true_calls"] += 1
            # **真的让位**：返回串里不再有 S-1 的禁令句
            if A.S1_CLAUSE not in (out or ""):
                counts["syntax_drop_s1_effective_calls"] += 1
        return out

    def w_pending_view(self):
        out = orig["pending_view"](self)
        counts["pending_view_calls"] += 1
        if out is not None:
            counts["pending_view_non_none"] += 1
        return out

    def w_visible(self, agent_id, upto_round, **kw):
        counts["visibility_visible_calls"] += 1
        if kw.get("extra"):
            counts["visible_extra_nonempty"] += 1
        return orig["visibility_visible"](self, agent_id, upto_round, **kw)

    # ---- T-DR-L2B-CHANNELS：DR 两条提示词通道的计数 wrapper ----
    def w_context_line(rifts, peer=None, round_no=0, name=None, params=None, *a, **kw):
        counts["context_line_calls"] += 1
        peer_ok = bool(peer)
        counts["context_line_nonempty_calls"]["peer_nonempty" if peer_ok else "peer_empty"] += 1
        if peer_ok and isinstance(rifts, dict) and rifts:
            counts["context_line_rifts_nonempty_calls"] += 1     # 阳性对照①
        out = orig["context_line"](rifts, peer, round_no, name, params, *a, **kw)
        if out:
            counts["context_line_nonempty_calls"]["total"] += 1
        return out

    def w_repair_ask(rifts, thread_id=None, peer=None, round_no=0, params=None, *a, **kw):
        counts["repair_ask_calls"] += 1
        if thread_id and isinstance(rifts, dict) and rifts:
            counts["repair_ask_rifts_nonempty_calls"] += 1        # 阳性对照②
        out = orig["repair_ask"](rifts, thread_id, peer, round_no, params, *a, **kw)
        if out:
            counts["repair_ask_nonempty_calls"] += 1
        return out

    A.narration_tail = w_narration_tail
    A.narration_example = w_narration_example
    A.openings_clause = w_openings_clause
    A.syntax_clause = w_syntax_clause
    KernelAdapter._pending_view = w_pending_view
    VisibilityIndex.visible = w_visible
    DRm.context_line = w_context_line
    DRm.repair_ask = w_repair_ask

    # ---- ① 自检：patch 后强制调用一次，计数必须 0→1（证明"装置能出声"）----
    selfcheck = {}
    try:
        for name, mod, attr, call in (
            ("narration_example", A, "narration_example",
             lambda: A.narration_example("initiate", "P001", 0)),
            ("openings_clause", A, "openings_clause", lambda: A.openings_clause()),
            ("syntax_clause", A, "syntax_clause",
             lambda: A.syntax_clause("P001", 0, None, True)),
            ("narration_tail", A, "narration_tail",
             lambda: A.narration_tail("initiate", "P001", 0, None)),
        ):
            before = (counts["narration_example_calls"] if name == "narration_example"
                      else counts["openings_clause_calls"] if name == "openings_clause"
                      else counts["syntax_clause_calls"] if name == "syntax_clause"
                      else counts["narration_tail_calls"]["total"])
            call()
            after = (counts["narration_example_calls"] if name == "narration_example"
                     else counts["openings_clause_calls"] if name == "openings_clause"
                     else counts["syntax_clause_calls"] if name == "syntax_clause"
                     else counts["narration_tail_calls"]["total"])
            selfcheck[name] = {"before": before, "after": after, "delta": after - before,
                               "ok": after - before == 1}
        # 自检会污染计数 ⇒ 归零，正式计数从 0 起
        counts["narration_example_calls"] = 0
        counts["openings_clause_calls"] = 0
        counts["openings_clause_nonempty_calls"] = {"total": 0, "initiate": 0, "reply": 0, "other": 0}
        counts["syntax_clause_calls"] = 0
        counts["syntax_drop_s1_true_calls"] = 0
        counts["syntax_drop_s1_effective_calls"] = 0
        counts["narration_tail_calls"] = {"total": 0, "initiate": 0, "reply": 0, "other": 0}
        ctx["kind"], ctx["tail"] = None, ""

        # 开关真值必须在 env 生效期间快照：`finally` 会恢复 env，之后读就全是"未设"
        switches = {
            "narration": bool(A.narration_enabled()),
            "openings": bool(A.openings_enabled()),
            "syntax": bool(A.syntax_enabled()),
            "intra": os.environ.get("HITT_INTRA_ROUND_VISIBILITY", "").strip().lower()
                     in {"1", "true", "yes", "on"},
            # T-DR-L2B-CHANNELS：DR 的三态/布尔值（同样在 env 生效期间快照）
            "dr_enabled": bool(DRm.load_params().get("enabled")),
            "repair_ask": DRm.load_params().get("repair_ask"),   # None/True/False
            "record_only": bool(DRm.load_params().get("record_only")),
        }
        w = build_world(seed=seed, n=n)
        eng = w["engine"]
        for r in range(rounds):
            eng.run_round(r)
        events = len(eng.ledger.records)
        msg_events = sum(1 for r in eng.ledger.records if str(r.get("type", "")).startswith("MSG"))
        dialogue_calls = sum(1 for r in eng.ledger.records
                            if r.get("type") == "LLM_CALL"
                            and (r.get("payload") or {}).get("purpose") == "dialogue")
        activity = {"msg_events": msg_events, "dialogue_llm_calls": dialogue_calls}

        # ---- T-DR-L2B-CHANNELS：**函数级注入 probe** ----------------------------------
        # 为什么需要它：mock 回复体不含负向词 ⇒ 世界里的 rift 恒为 0 ⇒ `context_line` /
        # `repair_ask` 的"非空"永远为 0，无法判断这个 0 是"机制没接通"还是"本来没旧账"。
        # 这里用**构造台账**直接调这两个函数，验证 wrapper 能区分"非空 / 为空 / 显式关闭"。
        # 只在 wrapper 仍生效时跑；跑批统计已累计完，故 x0/x1 差值即 probe 自身的效果。
        _rifts_probe = {"R|t-probe|m1": {"rift_id": "R|t-probe|m1", "with": "P002",
                                         "thread_id": "t-probe", "msg_uid": "m1",
                                         "seq": 5, "round": 0, "topic": "工钱", "day": 1, "slot": "am"}}
        _p_on = dict(DRm.DEFAULTS); _p_on["enabled"] = True
        _p_off = dict(DRm.DEFAULTS); _p_off["enabled"] = False
        _p_noask = dict(_p_on); _p_noask["repair_ask"] = False
        _snap = lambda: (counts["context_line_calls"], counts["context_line_nonempty_calls"]["total"],
                         counts["repair_ask_calls"], counts["repair_ask_nonempty_calls"])
        # **probe 前后回滚**：`counts` 必须只反映"跑批世界"里的调用，probe 单独报，
        # 否则"全关时两条新通道计数必须为 0"这条会被 probe 自身污染。
        _bak = {"context_line_calls": counts["context_line_calls"],
                "context_line_nonempty_calls": dict(counts["context_line_nonempty_calls"]),
                "context_line_rifts_nonempty_calls": counts["context_line_rifts_nonempty_calls"],
                "repair_ask_calls": counts["repair_ask_calls"],
                "repair_ask_nonempty_calls": counts["repair_ask_nonempty_calls"],
                "repair_ask_rifts_nonempty_calls": counts["repair_ask_rifts_nonempty_calls"]}
        _s0 = _snap()
        _ctx_empty = DRm.context_line({}, "P002", 5, name="老周", params=_p_on)
        _ctx_disabled = DRm.context_line(_rifts_probe, "P002", 5, name="老周", params=_p_off)
        _s1 = _snap()
        _ctx_on = DRm.context_line(_rifts_probe, "P002", 5, name="老周", params=_p_on)
        _ask_on = DRm.repair_ask(_rifts_probe, "t-probe", "P002", 5, _p_on)
        _s2 = _snap()
        _ask_noask = DRm.repair_ask(_rifts_probe, "t-probe", "P002", 5, _p_noask)
        _s3 = _snap()
        _probe_isolated = {
            "context_line_calls_in_arm": _bak["context_line_calls"],
            "context_line_nonempty_in_arm": _bak["context_line_nonempty_calls"]["total"],
            "repair_ask_calls_in_arm": _bak["repair_ask_calls"],
            "repair_ask_nonempty_in_arm": _bak["repair_ask_nonempty_calls"],
        }
        counts.update(_bak)          # 回滚：探针不计入本臂统计
        counts["context_line_nonempty_calls"] = dict(_bak["context_line_nonempty_calls"])
        function_probe = {
            "note": "构造台账直调两函数：wrapper 生效；探针增量已从本臂统计回滚，单独列于此处",
            "arm_counts_before_probe": _probe_isolated,
            "context_line_empty_rifts_is_none": _ctx_empty is None,
            "context_line_disabled_is_none": _ctx_disabled is None,
            "context_line_with_rifts_nonempty": bool(_ctx_on),
            "repair_ask_default_nonempty": bool(_ask_on),
            "repair_ask_false_is_none": _ask_noask is None,
            "context_line_calls_after_two_probes": _s1[0] - _s0[0],
            "context_line_nonempty_after": _s1[1] - _s0[1],
            "context_line_nonempty_delta_after_with_rifts": _s2[1] - _s1[1],
            "repair_ask_calls_after": _s2[2] - _s1[2],
            "repair_ask_nonempty_delta": _s2[3] - _s1[3],
            "repair_ask_nonempty_delta_when_false": _s3[3] - _s2[3],
            "counter_distinguishes": (_s1[1] - _s0[1]) == 0 and (_s2[1] - _s1[1]) == 1
                                    and (_s2[3] - _s1[3]) == 1 and (_s3[3] - _s2[3]) == 0,
        }
    finally:
        A.narration_tail = orig["narration_tail"]
        A.narration_example = orig["narration_example"]
        A.openings_clause = orig["openings_clause"]
        A.syntax_clause = orig["syntax_clause"]
        KernelAdapter._pending_view = orig["pending_view"]
        VisibilityIndex.visible = orig["visibility_visible"]
        DRm.context_line = orig["context_line"]
        DRm.repair_ask = orig["repair_ask"]
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        DRm._cache = None

    verdict = _verdict(mode, counts, switches, activity)
    return {
        "arm": {
            "mode": mode,
            "env": {k: MODES[mode].get(k, "unset") for k in ENV_KEYS},
            "provider": "mock（HITT_LLM_PROVIDER 已 pop）",
            "n": n, "rounds": rounds, "seed": seed, "events": events,
            "dr_enabled": switches.get("dr_enabled"),
            "repair_ask": switches.get("repair_ask"),
            "record_only": switches.get("record_only"),
            **activity,
        },
        "patch_targets": patch_target_proof,
        "patch_selfcheck": selfcheck,
        "function_level_probe": function_probe,
        "counts": counts,
        "verdict": verdict,
    }


def _v(detail: str, reason: str) -> dict:
    return {"verdict": "PASS" if detail == "ok" else "CANNOT-VERIFY",
            "detail": detail, "reason": reason}


def _verdict(mode: str, c: dict, sw: dict, act: dict) -> dict:
    out = {}
    tail = c["narration_tail_calls"]
    # ---- ROTATION：短路是否成立（0 必须有阳性对照 + 前提成立才可归因）----
    if tail["total"] == 0:
        out["ROTATION_shortcircuit"] = _v(
            "not_reached", "narration_tail() 从未被调用，narration_example()==0 无意义")
    elif not sw["narration"]:
        out["ROTATION_shortcircuit"] = _v(
            "channel_off", "旁白通道整体关闭（NARRATION 未开）：example==0 不可归因于 OPENINGS 短路")
    elif not sw["openings"]:
        out["ROTATION_shortcircuit"] = _v(
            "channel_off", "OPENINGS 未开，短路前提不成立（此时 example==0 才是正常旋转关闭）")
    elif c["narration_example_calls"] == 0:
        out["ROTATION_shortcircuit"] = _v(
            "ok", f"短路成立：narration_tail()={tail['total']}>0 而 narration_example()==0，"
                  "且 NARRATION 与 OPENINGS 均开")
    else:
        out["ROTATION_shortcircuit"] = _v(
            "zero_but_reached", f"未短路：narration_example() 被调用 {c['narration_example_calls']} 次")

    # ---- OPENINGS：按 kind 分组的非空计数 ----
    ne = c["openings_clause_nonempty_calls"]
    if tail["total"] == 0:
        out["OPENINGS_clause"] = _v("not_reached", "narration_tail() 从未被调用")
    elif not sw["openings"]:
        out["OPENINGS_clause"] = _v(
            "channel_off", "OPENINGS 未开：非空次数为 0 属预期，不构成「通道正常」的证据")
    elif not (tail["initiate"] > 0 and tail["reply"] > 0):
        out["OPENINGS_clause"] = _v(
            "not_reached",
            f"阳性对照不全：narration_tail 按 kind = initiate {tail['initiate']} / "
            f"reply {tail['reply']} ⇒ 至少一条路径未被调用，无法判「全通道」")
    elif ne["initiate"] > 0 and ne["reply"] > 0:
        out["OPENINGS_clause"] = _v(
            "ok", f"两条路径都有非空追加：initiate={ne['initiate']}、reply={ne['reply']}")
    elif ne["total"] > 0:
        out["OPENINGS_clause"] = _v(
            "zero_but_reached",
            f"只有一条路径命中（initiate={ne['initiate']}、reply={ne['reply']}）"
            "⇒ 另一条路径未触达，不能报全通道 PASS")
    else:
        out["OPENINGS_clause"] = _v(
            "zero_but_reached",
            f"OPENINGS 已开且 narration_tail()={tail['total']}>0，但非空追加 0 次 ⇒ 通道没接通")

    # ---- SYNTAX drop_s1：真值 vs 生效 ----
    t, e = c["syntax_drop_s1_true_calls"], c["syntax_drop_s1_effective_calls"]
    if tail["total"] == 0:
        out["SYNTAX_drop_s1"] = _v("not_reached", "narration_tail() 从未被调用")
    elif not sw["syntax"]:
        out["SYNTAX_drop_s1"] = _v(
            "channel_off", "SYNTAX 未开：drop_s1 传了也不会进 _apply_syntax_clause")
    elif t == 0:
        out["SYNTAX_drop_s1"] = _v(
            "zero_but_reached", f"SYNTAX 已开但 syntax_clause(drop_s1=True) 调用 0 次")
    elif t == e:
        out["SYNTAX_drop_s1"] = _v(
            "ok", f"drop_s1_true={t} == effective={e}（返回串均不含 S1_CLAUSE）")
    else:
        out["SYNTAX_drop_s1"] = _v(
            "mismatch", f"drop_s1_true={t} != effective={e} ⇒ 传了但没生效（配置≠生效）")

    # ---- INTRA_ROUND：双口径互证 ----
    pv, pn = c["pending_view_calls"], c["pending_view_non_none"]
    vv, ve = c["visibility_visible_calls"], c["visible_extra_nonempty"]
    if pv == 0 and vv == 0:
        out["INTRA_ROUND_pending_view"] = _v(
            "not_reached", "perceive 从未被调用（pending_view / visible 都是 0）")
    elif not sw["intra"]:
        out["INTRA_ROUND_pending_view"] = _v(
            "channel_off", f"开关未开：pending_view 调用 {pv} 次、非 None {pn} 次（应为 0）")
    elif pn == 0 and act["msg_events"] == 0:
        out["INTRA_ROUND_pending_view"] = _v(
            "not_reached", f"开关已开但本臂 MSG 事件 =0 ⇒ 缓冲区里没有消息可并入"
                           f"（pending_view 调用 {pv} 次）")
    elif pn == 0:
        out["INTRA_ROUND_pending_view"] = _v(
            "zero_but_reached", f"开关已开但 pending_view 非 None 为 0（调用 {pv} 次）")
    elif pn != ve:
        out["INTRA_ROUND_pending_view"] = _v(
            "mismatch", f"双口径不等：pending_view 非 None={pn} vs visible(extra≠空)={ve}")
    else:
        out["INTRA_ROUND_pending_view"] = _v(
            "ok", f"双口径互证：pending_view 非 None={pn} == visible(extra≠空)={ve}"
                  f"（调用 {pv}/{vv}）")

    # ---- T-DR-L2B-CHANNELS：DR 两条提示词通道 -----------------------------------
    # 硬规则（Leader 卡面）：每个 0 必须带 `why_zero` 且**可核**，否则当未采集；
    # 且必须带 `positive_control`（否则分不清"机制没接通"与"本来没东西可注入"）。
    def _dr_v(kind: str) -> dict:
        if kind == "context_line":
            calls = c["context_line_calls"]
            nonempty = c["context_line_nonempty_calls"]["total"]
            rifts_nn = c["context_line_rifts_nonempty_calls"]
            blocked = "record_only" if sw.get("record_only") else None
        else:
            calls = c["repair_ask_calls"]
            nonempty = c["repair_ask_nonempty_calls"]
            rifts_nn = c["repair_ask_rifts_nonempty_calls"]
            blocked = ("repair_ask=False" if sw.get("repair_ask") is False
                       else ("record_only" if sw.get("record_only") else None))
        pc = f"calls={calls}; 台账非空且 peer/thread 匹配的调用={rifts_nn} 次"
        # ---- ① 根因优先：总开关关着时，**即使 calls==0** 也要写"enabled=0"而不是"未触达" ----
        # （`enabled=0` 时 agent 根本不会调用该函数，"未触达"只是它的后果，不是原因）
        if not sw["dr_enabled"]:
            return {"verdict": "CANNOT-VERIFY", "detail": "channel_off", "value": nonempty,
                    "why_zero": "DR 总开关 enabled=0（机制整体关闭；该档本就不该有调用）",
                    "positive_control": pc,
                    "reason": "enabled 关闭 ⇒ 0 属预期，不是通道故障"}
        if blocked == "record_only":
            return {"verdict": "CANNOT-VERIFY", "detail": "channel_off", "value": nonempty,
                    "why_zero": "record_only=1：只录台账，显式不注入提示词",
                    "positive_control": pc, "reason": "record_only 下 0 属预期"}
        # ---- ② `repair_ask=False`：0 是**正向证据**，但必须有阳性对照（台账非空且被调用）----
        if kind == "repair_ask" and blocked == "repair_ask=False":
            if nonempty > 0:
                return {"verdict": "CANNOT-VERIFY", "detail": "mismatch", "value": nonempty,
                        "why_zero": "不应为 0：已显式关掉该段却仍注入", "positive_control": pc,
                        "reason": "repair_ask=False 但出现注入 ⇒ 配置≠生效"}
            if rifts_nn > 0:
                return {"verdict": "PASS", "detail": "ok", "value": 0,
                        "why_zero": "repair_ask=False 显式关闭该段（**0 是正向证据**）",
                        "positive_control": pc,
                        "reason": f"台账非空 {rifts_nn} 次、被调用 {calls} 次，仍不注入 ⇒ 短路成立"}
            return {"verdict": "CANNOT-VERIFY", "detail": "not_reached", "value": 0,
                    "why_zero": "无旧账（台账为空）**且**该段已显式关闭 ⇒ 两个原因同时存在，"
                                "不能报「短路成立」",
                    "positive_control": pc,
                    "reason": "缺阳性对照：没有旧账时 0 无法归因于 repair_ask=False"}
        if calls == 0:
            return {"verdict": "CANNOT-VERIFY", "detail": "not_reached", "value": nonempty,
                    "why_zero": "未触达：enabled 已开但跑批里该函数未被调用（calls=0）",
                    "positive_control": pc,
                    "reason": "函数未被调用，计数 0 不携带信息"}
        if rifts_nn == 0:
            return {"verdict": "CANNOT-VERIFY", "detail": "not_reached", "value": nonempty,
                    "why_zero": "无旧账：调用时 agent 台账为空（rifts_nonempty_calls=0，**可核**）",
                    "positive_control": pc,
                    "reason": "没有旧账可叙 ⇒ 0 属预期（mock 回复不含负向词时必然如此）"}
        if nonempty > 0:
            return {"verdict": "PASS", "detail": "ok", "value": nonempty,
                    "why_zero": None, "positive_control": pc,
                    "reason": f"台账非空 {rifts_nn} 次中注入 {nonempty} 次"}
        return {"verdict": "CANNOT-VERIFY", "detail": "zero_but_reached", "value": 0,
                "why_zero": "台账非空且被调用，却一次都没注入 ⇒ 真异常（不是「没有旧账」）",
                "positive_control": pc, "reason": "该注入未注入"}

    out["DR_context_line"] = _dr_v("context_line")
    out["DR_repair_ask"] = _dr_v("repair_ask")

    if not sw["intra"]:
        out["INTRA_ROUND_visibility_extra"] = _v(
            "channel_off", f"开关未开：visible(extra≠空)={ve}（应为 0，阳性对照 visible 调用 {vv} 次）"
            if vv else "perceive 从未被调用")
    elif ve == 0 and act["msg_events"] == 0:
        out["INTRA_ROUND_visibility_extra"] = _v(
            "not_reached", f"开关已开但本臂 MSG 事件 =0 ⇒ extra 恒空（visible 调用 {vv} 次）")
    elif ve == 0:
        out["INTRA_ROUND_visibility_extra"] = _v(
            "zero_but_reached", f"开关已开但 visible(extra≠空) 为 0（visible 调用 {vv} 次）")
    else:
        out["INTRA_ROUND_visibility_extra"] = _v(
            "ok", f"visible(extra≠空)={ve} >0（visible 总调用 {vv} 次作阳性对照）")
    return out


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description="L2b 通道接通计数门")
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--arm", choices=["off", "on", "mixed", "dr_msg", "dr_noask", "both", "all", "dr"], default="both")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv[1:])

    if args.arm == "both":
        arms = ["off", "on"]
    elif args.arm == "all":
        arms = list(MODES)
    elif args.arm == "dr":
        arms = ["dr_msg", "dr_noask"]
    else:
        arms = [args.arm]
    result = {"tool": "tools/d9z/channel_counts.py", "l2b": True,
              "arms": [_run_arm(m, args.n, args.rounds, args.seed) for m in arms]}
    # ---- 三档自测汇总（T-DR-L2B-CHANNELS）----
    # 档1：enabled=0 ⇒ 两计数 0，why_zero = enabled 关闭
    # 档2：enabled=1 无 rift ⇒ 两计数 0，why_zero = 无旧账（且 rifts_nonempty_calls==0 可核）
    # 档3：有 rift + repair_ask=false ⇒ repair_ask 仍 0（正向证据）、context_line > 0；对照 repair_ask=true > 0
    #      档3 在 mock 世界里不可得（回复体不含负向词 ⇒ rift 恒 0），故由**函数级注入 probe** 给出。
    by_mode = {v["arm"]["mode"]: v for v in result["arms"]}
    tiers = {}
    if "off" in by_mode:
        cl, ra = by_mode["off"]["counts"], by_mode["off"]["verdict"]
        tiers["tier1_enabled0"] = {
            "source": "arm=off",
            "context_line_value": cl["context_line_calls"] and cl["context_line_nonempty_calls"]["total"] or 0,
            "repair_ask_value": cl["repair_ask_nonempty_calls"],
            "why_zero": ra["DR_context_line"]["why_zero"],
            "positive_control": ra["DR_context_line"]["positive_control"],
            "ok": ra["DR_context_line"]["detail"] == "channel_off" and ra["DR_repair_ask"]["detail"] == "channel_off",
        }
    if "dr_msg" in by_mode:
        cl = by_mode["dr_msg"]["counts"]
        tiers["tier2_enabled1_no_rift"] = {
            "source": "arm=dr_msg（mock 回复不含负向词 ⇒ 真实 rift 恒 0）",
            "context_line_value": cl["context_line_nonempty_calls"]["total"],
            "repair_ask_value": cl["repair_ask_nonempty_calls"],
            "rifts_nonempty_calls": cl["context_line_rifts_nonempty_calls"],
            "why_zero": by_mode["dr_msg"]["verdict"]["DR_context_line"]["why_zero"],
            "positive_control": by_mode["dr_msg"]["verdict"]["DR_context_line"]["positive_control"],
            "ok": (cl["context_line_nonempty_calls"]["total"] == 0
                   and cl["repair_ask_nonempty_calls"] == 0
                   and cl["context_line_rifts_nonempty_calls"] == 0),
        }
    probes = [v["function_level_probe"] for v in result["arms"] if v.get("function_level_probe")]
    if probes:
        pr = probes[0]
        tiers["tier3_with_rift_repair_ask_false"] = {
            "source": "function_level_probe（构造台账直调两函数；mock 世界里拿不到 rift）",
            "context_line_with_rift_nonempty": pr["context_line_with_rifts_nonempty"],
            "repair_ask_default_nonempty": pr["repair_ask_default_nonempty"],
            "repair_ask_false_is_none": pr["repair_ask_false_is_none"],
            "counter_distinguishes": pr["counter_distinguishes"],
            "why_zero": "repair_ask=False 显式关闭该段（0 是正向证据）",
            "positive_control": "同一构造台账下 repair_ask 默认（null/True）时非空，且 repair_ask=False 时为空",
            "ok": bool(pr["context_line_with_rifts_nonempty"] and pr["repair_ask_default_nonempty"]
                       and pr["repair_ask_false_is_none"] and pr["counter_distinguishes"]),
        }
    result["three_tier_selftest"] = tiers

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    print(text)
    # 允许"全关臂出现 CANNOT-VERIFY"（那是预期），只在 on 臂出现非 PASS 且非 not_reached 时失败

    on_arm = [v for v in result["arms"] if v["arm"]["mode"] == "on"]
    # DR 两通道只在 `dr_*` 臂有意义（`on` 臂 DR 是关的）⇒ 不作为 `on` 臂的 rc 判据
    bad = [k for v in on_arm for k, vd in v["verdict"].items()
           if not k.startswith("DR_") and vd["detail"] in ("zero_but_reached", "mismatch")]
    thin = [k for v in on_arm for k, vd in v["verdict"].items()
            if not k.startswith("DR_") and vd["detail"] == "not_reached"]
    if bad:
        return 1                      # 真异常（开了但没接通 / 双口径不等）
    if not all(t.get("ok") for t in result.get("three_tier_selftest", {}).values()):
        return 1                      # 三档自测未全过
    if thin:
        return 2                      # 活动不足：规模太小，判不了（不是不合格）
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
