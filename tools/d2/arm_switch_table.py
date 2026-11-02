#!/usr/bin/env python3
"""臂开关登记表（表驱动）+ 声明值提取器 + 运行期反推探针。

背景（看板 A-4，R53 第三次复现）
--------------------------------
`tools/d2/emit_run_meta.py` 原来把每个臂开关**写死**成单独分支（`_declared_switch("X")`
+ `meta["switch_effective"].update(...)` + 末尾一条 print）。每加一个新臂（R52 的
`HITT_SCENE_FRESH`、R53 的 `HITT_SCHEDULE_OFFSET`…）都要手改三处且没有任何守卫，
漏一处 ⇒ `meta.json.switch_effective` 里**根本没有这个键** ⇒ 「这一臂跑批时到底开没开」
无法从 meta 取证，两臂对照不可复算。R53 两臂 meta 只有 4 个键、不含 `HITT_SCHEDULE_OFFSET`，
就是这条缺口的第三次复现。

本模块把「登记 + 声明值提取 + 运行期反推探针」收成**一张表**：
  * 加臂 = 表里加一行（`ARM_SWITCHES`），不用再改 `emit_run_meta.py`；
  * 未登记 ⇒ 结构性不存在该键，而不是「被人忘了」（`--selftest` 会断言必覆盖集合）。

三态：`unset` / `empty` / `set`
------------------------------
`unset`（环境里根本没这个变量）与 `empty`（设了但值是空串，如 `HITT_SCHEDULE_OFFSET=`）
在排障时是两条不同线索（谁 export 的？是不是某个 `set -a; . .env.local` 带进来的？）。
旧实现 `os.environ.get()` 把两者都压成 None/False，无法区分。这里显式给出 `state`。

离线可用（零跑批、零 LLM、零真跑）
--------------------------------
  # 1) 直接吃 arm_inner.sh 落的 env_manifest.txt（`<unset>` 视为未设）
  python3 tools/d2/arm_switch_table.py --env-manifest v2/evidence/<run>/env_manifest.txt
  # 2) 机器可读
  python3 tools/d2/arm_switch_table.py --env-manifest <...> --json
  # 3) 表 + 三态 + 探针的自测断言（无需任何输入文件）
  python3 tools/d2/arm_switch_table.py --selftest

探针口径（运行期事实，一律来自 run.jsonl 的结构化审计键，绝不来自 env/人声明）
------------------------------------------------------------------------------
见每个 `probe` 的 `evidence_field`。四态融合规则与 `emit_run_meta._fuse_state` 一致：
  命中>0 ⇒ on（声明 OFF 则 contradiction）；命中==0 ⇒ off（声明 ON 则 cannot-verify）。
`probe=None` 表示该开关**只改提示词文本、无结构字段可反推** ⇒ `effective` 恒
`cannot-verify`（绝不可当成「开关没开」的证据）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

#: 与 code/life/weather.py::enabled 同口径的真值集合
TRUTHY = {"1", "true", "yes", "on"}

#: env_manifest.txt 里「未设置」的占位符（tools/r5x/arm_inner.sh 写入）
UNSET_MARKER = "<unset>"

# 探针 spec 的四种形态（见 probe_runtime）：
#   {"kind": "ctx_key",            "key": <ctx 子键>}                        → MSG payload.ctx[key] 命中数
#   {"kind": "ctx_subkey",         "key": <ctx 子键>, "sub": <子键>,
#                                  "equals": <值>}                            → ctx[key][sub] == 值 的命中数
#   {"kind": "payload_key_any",    "keys": [<顶层键>, ...]}                   → payload 顶层任一键命中数
#   {"kind": "schedule_slots_key", "key": <slot 子键>}                        → SCHEDULE_PLANNED.slots[*][key] 命中数

ARM_SWITCHES: list[dict] = [
    # ---------------- 已登记且可从 run.jsonl 反推（强证据） ----------------
    {
        "name": "HITT_WEATHER",
        "kind": "bool",
        "probe": {"kind": "ctx_key", "key": "weather"},
        "note": "W-1 天气臂（R28 起）；ctx.weather 由 code/life/agent.py::_ctx_snapshot 仅 ON 时写。",
    },
    {
        "name": "HITT_DIALOGUE_EMOTION_ECHO",
        "kind": "bool",
        "probe": {"kind": "ctx_key", "key": "echo"},
        "note": ("F-3 情绪呼应（impl-101）；命中==0 属结构性可观测上限（本槽无情感词/无入站 mood），"
                 "不代表开关没开 ⇒ 声明 ON 时判 cannot-verify。"),
    },
    {
        "name": "HITT_DIALOGUE_REPAIR",
        "kind": "bool",
        "probe": {"kind": "payload_key_any", "keys": ["dialogue_rift", "dialogue_repair"]},
        "note": ("F-4 误会与和解；rift 由 DR.ingest 从入站负面词入账，mock/无冲突句时 0 条入账，"
                 "同属结构性可观测上限。"),
    },
    {
        "name": "HITT_SCHEDULE_OFFSET",
        "kind": "bool",
        "probe": {"kind": "schedule_slots_key", "key": "schedule_offset"},
        "note": ("R53 作息个体差异/错峰臂（看板 A-4 缺口本体）。ON 时 code/life/agent.py::_weekly_slots "
                 "给每个 SCHEDULE_PLANNED.slots[*] 加 additive 审计键 schedule_offset={ticks,activity_changed}；"
                 "OFF ⇒ 该键恒不出现（逐字节等价要求）。R53 实测 ON 臂 448/448 slots 命中、OFF 臂 0/448。"),
    },
    {
        "name": "HITT_SCENE_FRESH",
        "kind": "bool",
        "probe": {"kind": "ctx_subkey", "key": "scene", "sub": "place_src", "equals": "live"},
        "note": ("R52 / B-8 处境锚取值时点修复；ON 时 ctx.scene 多一个 place_src=\"live\""
                 "（code/life/scene_anchor.py::audit 仅 place_src 非空时写入）。"),
    },
    {
        "name": "HITT_NEED_SPEECH",
        "kind": "bool",
        "probe": {"kind": "ctx_key", "key": "need_speech"},
        "note": "R51 需求入话臂；ON 时 ctx.need_speech={dim,value,injected} 仅在有 _need_speech 时写。",
    },
    {
        "name": "HITT_DIALOGUE_PUBLIC_REPLY",
        "kind": "bool",
        "probe": {"kind": "ctx_key", "key": "public_reply"},
        "note": ("R41 公开面接话臂；ON 且命中时 code/life/agent.py 写 payload.ctx.public_reply"
                 "=public_talk.audit(...)；OFF ⇒ 该键不出现。tools/public_talk/launch_r41v.sh 也从"
                 "prev meta 的 switch_effective 读这个键做上臂比对。"),
    },
    # ---------------- 已登记但只能 cannot-verify（纯提示词开关） ----------------
    {
        "name": "LIFE_PROMPT_ADDR_EVOLVE",
        "kind": "bool",
        "probe": None,
        "cannot_verify_reason": ("恒 cannot-verify：本开关只改提示词文本，称呼文本不进 MSG payload，"
                                 "无结构字段可反推；ON/OFF 判定只认 M2(prompt 渲染 sha)/"
                                 "M3(prompt_hash 集合)/M4(/proc/<pid>/environ)。"
                                 "**不得**用 effective=cannot-verify 反推「开关没开」。"),
        "note": "N-15 称呼演化臂（R01）。",
    },
    {
        "name": "HITT_D12_DETAIL",
        "kind": "bool",
        "probe": None,
        "cannot_verify_reason": ("恒 cannot-verify：D12-A「具体性插槽」只在提示词里追加一段文字"
                                 "（code/life/agent.py::_d12_detail_block），不产生任何 payload 键。"),
        "note": "D12-A 具体性插槽臂（默认关）。",
    },
    {
        "name": "HITT_LIVING_SLOT",
        "kind": "bool",
        "probe": None,
        "cannot_verify_reason": ("恒 cannot-verify：F-5 生活气息臂只改 planner 的候选集与选中结果"
                                 "（code/life/planner.py::living_enabled），不写任何审计键；"
                                 "ON/OFF 判定只能靠「同一 seed 下 SCHEDULE_PLANNED 的活动类型分布是否有"
                                 "合法生活类 item」这类间接推断，不能当 hard evidence。"),
        "note": ("F-5 生活气息臂（R53 两臂均不设，arm_inner.sh 显式记录 HITT_LIVING_SLOT=<unset>）。"
                 "登记它以保证 meta 里能看到「本臂是否设过」。"),
    },
    # ---------------- 已登记（声明侧），不是「臂差异」本体 ----------------
    {
        "name": "LIFE_PROMPT_SCENE",
        "kind": "bool",
        "probe": {"kind": "ctx_key", "key": "scene"},
        "note": "处境锚臂总开关（R32 起，两臂共同打开）；ctx.scene 命中数可视作「场景行是否真下发」。",
    },
    {
        "name": "HITT_WORLD_SEED",
        "kind": "int",
        "probe": None,
        "in_effective": False,
        "note": ("种子不是开关：只产出 parsed_int（同 code/life/weather.py::world_seed：缺失/非法 ⇒ 0），"
                 "故不写入 switch_effective（写 bool 会误导）。"),
    },
]


def table_names(*, only_effective: bool = False) -> list[str]:
    """表内开关名（`only_effective=True` ⇒ 只取会写进 switch_effective 的）。"""
    return [s["name"] for s in ARM_SWITCHES
            if (not only_effective) or s.get("in_effective", True)]


def parse_env_manifest_detailed(path: str | Path) -> dict:
    """读 env_manifest.txt → 三件事分开记：`env` / `explicit_unset` / `keys`。

    为什么要 detailed 版（看板 A-2/A-4）：manifest 由 `tools/r53/arm_inner.sh` 一类的启动器
    **只登记它自己关心的那几个键**。于是「清单里没这个键」与「清单里明确写了
    `<unset>`」是**两种不同强度的证据**：
      * 明确 `<unset>` ⇒ 该臂**确证未导出**该变量（本臂声明值 = 关）；
      * 清单里压根没出现 ⇒ **声明侧未知**（既不能断言开、也不能断言关）。
    旧 `parse_env_manifest()` 把两者压成同一个「不在 dict 里」，用于「回放取证」会把
    「不知道」冒充成「关」，故这里补 detailed 版（旧函数语义保持不变，向后兼容）。
    """
    env: dict[str, str] = {}
    explicit_unset: list[str] = []
    keys: list[str] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            if not k or " " in k or "\t" in k:
                continue
            keys.append(k)
            if v == UNSET_MARKER:
                explicit_unset.append(k)
                continue  # 未设 ⇒ 不出现在 env 里（与真实进程环境一致）
            env[k] = v
    return {
        "path": str(path),
        "env": env,
        "explicit_unset": sorted(set(explicit_unset)),
        "keys": sorted(set(keys)),
    }


def parse_env_manifest(path: str | Path) -> dict:
    """读 arm_inner.sh 落盘的 env_manifest.txt → {NAME: raw}；`<unset>` 不进 dict（= 未设）。

    只认 `KEY=VALUE` 形态的行（含值带空格的如 INLINE_ENV，无害：我们只按名精确查）。
    需要区分「明确 <unset>」与「清单里没出现」时用 `parse_env_manifest_detailed()`。
    """
    return parse_env_manifest_detailed(path)["env"]


def declared_switch(name: str, env: dict | None = None, kind: str = "bool",
                    source: str | None = None) -> dict:
    """开关的**声明值**（弱证据：本进程/清单文件读到的值，非运行期事实）。

    `state` 区分三态（本模块修补的第二件事）：
      * `unset` 环境里没有这个变量（raw=None）
      * `empty` 有变量但值为空串/纯空白（raw=""/"  "）—— 例如 `HITT_X=` 或 `.env.local` 里空赋值
      * `set`   有变量且值非空
    `kind` 决定归一口径（**别把非布尔 env 硬塞进布尔口径**）：
      * `bool`：`normalized_effective` = 是否 ∈ {1,true,yes,on}
      * `int` ：给 `parsed_int`（缺失/非法 ⇒ 0），不产出 `normalized_effective`
    """
    if env is None:
        present = name in os.environ
        raw = os.environ.get(name) if present else None
        src = source or f"os.environ[{name!r}] @ emit_run_meta 进程"
    else:
        present = name in env
        raw = env.get(name) if present else None
        src = source or "env_manifest.txt（离线声明值；<unset> 视为未设）"

    if not present:
        state = "unset"
    elif not (raw or "").strip():
        state = "empty"
    else:
        state = "set"

    out = {"raw": raw, "state": state, "present": present, "source": src}
    if kind == "int":
        try:
            out["parsed_int"] = int((raw or "").strip()) if (raw or "").strip() else 0
        except (TypeError, ValueError):
            out["parsed_int"] = 0
        out["parse_rule"] = "同 code/life/weather.py::world_seed：缺失/非法 ⇒ 0"
    else:
        out["normalized_effective"] = (raw or "").strip().lower() in TRUTHY
        out["parse_rule"] = ("bool：strip().lower() ∈ {1,true,yes,on} ⇒ 真"
                             "（与 code/life/weather.py::enabled 同口径）")
    return out


def declared_switch_from_manifest(name: str, manifest: dict, kind: str = "bool") -> dict:
    """按 env_manifest **回放**取声明值（离线取证用；manifest 见 `parse_env_manifest_detailed`）。

    与 live 模式（读 `os.environ`）的差别只有一处、但很关键：`declared_known`。
      * 清单里出现该键（有值 或 明确 `<unset>`）⇒ `declared_known=True`，
        `declared_state` 仍走 unset/empty/set 三态（`explicit_unset` 显式标出）；
      * 清单里没出现 ⇒ `declared_known=False`、`declared_state="absent-from-manifest"`：
        **声明侧未知**（manifest 只登记启动器关心的键，缺键 ≠ 未设），
        此时 `normalized_effective` 仍给出兼容用的 False，但**禁止**把它当真值引用。
    """
    st = declared_switch(name, env=manifest["env"], kind=kind,
                         source=f"env_manifest[{manifest['path']}]")
    mentioned = name in manifest["keys"] or name in manifest["explicit_unset"]
    st["declared_known"] = mentioned
    st["declared_state"] = st["state"]
    if name in manifest["explicit_unset"]:
        st["explicit_unset"] = True
    if not mentioned:
        st["declared_state"] = "absent-from-manifest"
        st["absent_from_manifest"] = True
    return st


def _msg_recs(recs):
    for r in recs:
        if str(r.get("type", "")).startswith("MSG"):
            yield r


def probe_runtime(recs, spec: dict) -> dict:
    """按 spec 从 run.jsonl 记录里数结构化审计键命中数（运行期事实，强证据）。"""
    kind = spec["kind"]
    hits = 0
    by_type: dict[str, int] = {}
    evidence = ""

    if kind == "ctx_key":
        key = spec["key"]
        for r in _msg_recs(recs):
            ctx = (r.get("payload") or {}).get("ctx")
            if isinstance(ctx, dict) and ctx.get(key) is not None:
                hits += 1
                by_type[r["type"]] = by_type.get(r["type"], 0) + 1
        evidence = f"run.jsonl[*].payload.ctx.{key}"

    elif kind == "ctx_subkey":
        key, sub, want = spec["key"], spec["sub"], spec.get("equals")
        for r in _msg_recs(recs):
            ctx = (r.get("payload") or {}).get("ctx")
            if not isinstance(ctx, dict):
                continue
            v = ctx.get(key)
            if not isinstance(v, dict):
                continue
            got = v.get(sub)
            if got is None:
                continue
            if want is not None and str(got) != str(want):
                continue
            hits += 1
            by_type[r["type"]] = by_type.get(r["type"], 0) + 1
        evidence = f"run.jsonl[*].payload.ctx.{key}.{sub} == {want!r}"

    elif kind == "payload_key_any":
        keys = list(spec["keys"])
        for r in _msg_recs(recs):
            payload = r.get("payload") or {}
            if any(isinstance(payload.get(k), dict) for k in keys):
                hits += 1
                by_type[r["type"]] = by_type.get(r["type"], 0) + 1
        evidence = "run.jsonl[*].payload." + " | .".join(keys)

    elif kind == "schedule_slots_key":
        key = spec["key"]
        for r in recs:
            if r.get("type") != "SCHEDULE_PLANNED":
                continue
            for slot in ((r.get("payload") or {}).get("slots") or []):
                if isinstance(slot, dict) and slot.get(key) is not None:
                    hits += 1
                    by_type["SCHEDULE_PLANNED"] = by_type.get("SCHEDULE_PLANNED", 0) + 1
        evidence = f"run.jsonl[type==SCHEDULE_PLANNED][*].payload.slots[*].{key}"

    else:  # pragma: no cover - 表写错时立刻炸，别静默
        raise ValueError(f"未知 probe kind: {kind!r}")

    return {
        "hits": hits,
        "hits_by_event": {k: v for k, v in sorted(by_type.items())},
        "evidence_field": evidence,
        "probe_spec": spec,
    }


def fuse_state(hits: int, declared_on: bool, declared_known: bool = True) -> str:
    """四态融合（与 emit_run_meta 同口径）：on/off/cannot-verify/contradiction。

    `declared_known=False`（清单里没登记该键 ⇒ 声明侧未知）时的额外纪律：
      * 命中>0 ⇒ `on`（**不**判 contradiction —— 拿「未知的声明值」去否决运行期硬证据是错的）；
      * 命中==0 ⇒ `cannot-verify`（**不**判 off —— 未知不是「关」）。
    """
    if hits > 0:
        if declared_known and not declared_on:
            return "contradiction"
        return "on"
    if not declared_known:
        return "cannot-verify"
    return "off" if not declared_on else "cannot-verify"


# ---------------------------------------------------------------- CLI / 自测

def _fmt_value(st: dict) -> str:
    if st["state"] == "unset":
        return UNSET_MARKER
    if st["state"] == "empty":
        return "''"
    return str(st["raw"])


def _selftest() -> int:
    fails: list[str] = []

    def chk(cond, msg):
        if not cond:
            fails.append(msg)

    # 1) 必覆盖集合（看板 A-4 明确点名的历史臂变量）
    required = {"HITT_SCHEDULE_OFFSET", "HITT_SCENE_FRESH", "HITT_NEED_SPEECH",
                "HITT_D12_DETAIL", "HITT_DIALOGUE_EMOTION_ECHO", "HITT_DIALOGUE_REPAIR",
                "HITT_WEATHER", "LIFE_PROMPT_ADDR_EVOLVE",
                "HITT_DIALOGUE_PUBLIC_REPLY", "HITT_LIVING_SLOT", "LIFE_PROMPT_SCENE"}
    chk(required <= set(table_names()), f"表缺键：{sorted(required - set(table_names()))}")
    chk(len(set(table_names())) == len(table_names()), "表内 name 重复")

    # 2) 三态：unset / empty / set 必须两两可区分
    unset_st = declared_switch("HITT_SCHEDULE_OFFSET", env={}, source="test")
    empty_st = declared_switch("HITT_SCHEDULE_OFFSET", env={"HITT_SCHEDULE_OFFSET": ""}, source="test")
    one_st = declared_switch("HITT_SCHEDULE_OFFSET", env={"HITT_SCHEDULE_OFFSET": "1"}, source="test")
    chk(unset_st["state"] == "unset" and unset_st["raw"] is None, "unset 态判错")
    chk(empty_st["state"] == "empty" and empty_st["raw"] == "", "empty 态判错（未与 unset 区分）")
    chk(one_st["state"] == "set" and one_st["raw"] == "1", "set 态判错")
    chk(unset_st["raw"] != empty_st["raw"], "unset/empty 的 raw 未区分")
    chk(one_st["normalized_effective"] is True, "bool 归一口径判错")

    # 3) int 口径不产出 normalized_effective
    seed_st = declared_switch("HITT_WORLD_SEED", env={"HITT_WORLD_SEED": "42"}, kind="int", source="test")
    chk(seed_st["parsed_int"] == 42 and "normalized_effective" not in seed_st, "int 口径判错")

    # 4) env_manifest 解析：`<unset>` = 未设
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
        fh.write("# comment\nHITT_SCHEDULE_OFFSET=<unset>\nHITT_WEATHER=1\n")
        tmp = fh.name
    try:
        env = parse_env_manifest(tmp)
        chk("HITT_SCHEDULE_OFFSET" not in env, "env_manifest 的 <unset> 未被当成未设")
        chk(env.get("HITT_WEATHER") == "1", "env_manifest 正常键解析失败")
    finally:
        os.unlink(tmp)

    # 5) 探针：四种 spec 各自数得到
    recs = [
        {"type": "MSG_PUBLIC", "payload": {"ctx": {"weather": {"day": 1}, "echo": {"sign": 1},
                                                   "need_speech": {"dim": "x"},
                                                   "scene": {"place_src": "live"}}}},
        {"type": "MSG_DM", "payload": {"ctx": {"scene": {"place_src": "snapshot"}},
                                        "dialogue_repair": {"k": 1}}},
        {"type": "SCHEDULE_PLANNED", "payload": {"slots": [{"schedule_offset": {"ticks": 1}}, {}]}},
    ]
    got = {
        "weather": probe_runtime(recs, {"kind": "ctx_key", "key": "weather"})["hits"],
        "echo": probe_runtime(recs, {"kind": "ctx_key", "key": "echo"})["hits"],
        "need_speech": probe_runtime(recs, {"kind": "ctx_key", "key": "need_speech"})["hits"],
        "scene_live": probe_runtime(recs, {"kind": "ctx_subkey", "key": "scene",
                                           "sub": "place_src", "equals": "live"})["hits"],
        "repair": probe_runtime(recs, {"kind": "payload_key_any",
                                       "keys": ["dialogue_rift", "dialogue_repair"]})["hits"],
        "sched": probe_runtime(recs, {"kind": "schedule_slots_key", "key": "schedule_offset"})["hits"],
    }
    want = {"weather": 1, "echo": 1, "need_speech": 1, "scene_live": 1, "repair": 1, "sched": 1}
    chk(got == want, f"探针计数不符：got={got} want={want}")

    # 6) 四态融合
    chk(fuse_state(3, False) == "contradiction", "fusion 判错 contradiction")
    chk(fuse_state(0, True) == "cannot-verify", "fusion 判错 cannot-verify")
    chk(fuse_state(0, False) == "off", "fusion 判错 off")
    # 声明侧未知（declared_known=False）：既不判 off、也不判 contradiction
    chk(fuse_state(0, False, declared_known=False) == "cannot-verify",
        "声明未知 + 命中 0 应判 cannot-verify（不得冒充 off）")
    chk(fuse_state(5, False, declared_known=False) == "on",
        "声明未知 + 命中>0 应判 on（不得用未知声明值否掉运行期硬证据）")

    # 7) env_manifest 回放：明确 <unset> = 声明已知且关；清单缺键 = 声明未知
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
        fh.write("# manifest\nLIFE_PROMPT_SCENE=1\nHITT_SCHEDULE_OFFSET=<unset>\n")
        tmp2 = fh.name
    try:
        man = parse_env_manifest_detailed(tmp2)
        chk("HITT_SCHEDULE_OFFSET" in man["explicit_unset"], "explicit_unset 未记录 <unset> 键")
        off_st = declared_switch_from_manifest("HITT_SCHEDULE_OFFSET", man)
        on_st = declared_switch_from_manifest("LIFE_PROMPT_SCENE", man)
        unk_st = declared_switch_from_manifest("HITT_WEATHER", man)
        chk(off_st["declared_known"] is True and off_st["normalized_effective"] is False
            and off_st["state"] == "unset", f"manifest 显式 <unset> 判错：{off_st}")
        chk(on_st["declared_known"] is True and on_st["normalized_effective"] is True,
            f"manifest 有值键判错：{on_st}")
        chk(unk_st["declared_known"] is False
            and unk_st["declared_state"] == "absent-from-manifest",
            f"manifest 缺键应判声明未知：{unk_st}")
        # 端到端：off 臂显式 <unset> + 命中 0 ⇒ off；on 臂有值 ⇒ on
        chk(fuse_state(0, off_st["normalized_effective"],
                       declared_known=off_st["declared_known"]) == "off",
            "manifest off 臂应判 off")
        chk(fuse_state(448, on_st["normalized_effective"],
                       declared_known=on_st["declared_known"]) == "on",
            "manifest on 臂应判 on")
    finally:
        os.unlink(tmp2)

    if fails:
        for f in fails:
            print(f"[selftest] FAIL: {f}", file=sys.stderr)
        return 1
    print(f"[selftest] OK: {len(ARM_SWITCHES)} 个开关登记；三态/探针/融合断言全通过")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="臂开关登记表：声明值提取 / 运行期探针自测（离线）")
    ap.add_argument("--env-manifest", help="arm_inner.sh 落的 env_manifest.txt（<unset> = 未设）")
    ap.add_argument("--json", action="store_true", help="机器可读输出")
    ap.add_argument("--selftest", action="store_true", help="跑内置断言（无需任何输入）")
    a = ap.parse_args(argv)

    if a.selftest:
        return _selftest()

    env = None
    src = None
    if a.env_manifest:
        env = parse_env_manifest(a.env_manifest)
        src = f"env_manifest[{a.env_manifest}]"

    out = {}
    for sw in ARM_SWITCHES:
        st = declared_switch(sw["name"], env=env, kind=sw["kind"], source=src)
        st["in_switch_effective"] = sw.get("in_effective", True)
        st["probe"] = sw.get("probe")
        out[sw["name"]] = st

    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    print(f"# 臂开关声明值（source={src or '当前进程 os.environ'}）")
    for name, st in out.items():
        eff = ("parsed_int=%s" % st["parsed_int"]) if "parsed_int" in st \
            else ("effective=%s" % ("on" if st["normalized_effective"] else "off"))
        print(f"{name}={_fmt_value(st)}\tstate={st['state']}\t{eff}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
