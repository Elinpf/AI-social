#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F-2 尺子自测：`real_message_id` 必须按 `payload.msg_uid` 匹配（而不是 `msg_id`）。

运行：
    cd <repo> && python3 -m pytest tools/public_talk/test_public_talk_metrics_reply_uid.py -q
    # 或直接执行
    cd <repo> && python3 tools/public_talk/test_public_talk_metrics_reply_uid.py

分组：
  T1 匹配口径：`reply_to` 为 msg_uid ⇒ `real_message_id`；
  T2 不误判   ：不命中任何集合 ⇒ `other`（**不得**因集合为空/键名不匹配而算成命中）；
  T3 msg_id 降级：命中不唯一的 msg_id 只记 `real_message_id_legacy_msg_id`，不进分子；
  T4 其它形态 ：missing_key / json_null / string_None / empty_string 互斥且不被吞；
  T5 端到端   ：`scan_extra_log()` 在读真实 r41v ON 臂日志时，`real_message_id` 不再恒 0，
                且 `real_message_id + legacy + other == reply_to 非空条数`（口径闭合）。

数据来源：`v2/evidence/r41v_public_talk_n16r24_s42/{off,on}/run.jsonl`（只读、零 LLM）。
其中 ON 臂 `reply_to` 非空 7 条、OFF 臂 0 条 —— 这两个数**由本测试现算**，不引用他人转述。
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

import public_talk_metrics as PT  # noqa: E402

ON_LOG = REPO / "v2" / "evidence" / "r41v_public_talk_n16r24_s42" / "on" / "run.jsonl"
OFF_LOG = REPO / "v2" / "evidence" / "r41v_public_talk_n16r24_s42" / "off" / "run.jsonl"


# ---------------- T1 匹配口径 ----------------
def test_reply_to_msg_uid_hits_real_message_id():
    payload = {"reply_to": "42:189"}
    assert PT.reply_to_form(payload, set(), {"42:189", "42:200"}) == "real_message_id"


def test_reply_to_dm_or_public_uid_both_count():
    """候选集合取自**任一消息事件**（DM/PUB/GROUP），不限于 PUB。"""
    assert PT.reply_to_form({"reply_to": "42:1075"}, set(), {"42:1075"}) == "real_message_id"


# ---------------- T2 不误判 ----------------
def test_unknown_reply_to_is_other_not_real():
    assert PT.reply_to_form({"reply_to": "42:999999"}, set(), {"42:189"}) == "other"


def test_empty_candidate_sets_must_not_match():
    """集合为空时**不得**命中（旧实现的空转风险：集合放错键名 ⇒ 恒 0 或恒真）。"""
    assert PT.reply_to_form({"reply_to": "42:189"}, set(), set()) == "other"
    assert PT.reply_to_form({"reply_to": "42:189"}, None, None) == "other"


def test_wrong_key_name_regression_guard():
    """回归护栏：把 msg_uid 误当 msg_id 传（旧 bug 形态）时**不能**算命中。"""
    payload = {"reply_to": "42:189"}          # 这是 msg_uid，不是 msg_id
    assert PT.reply_to_form(payload, {"P-0-0"}, set()) == "other"


# ---------------- T3 msg_id 降级 ----------------
def test_msg_id_hit_is_legacy_bucket_not_numerator():
    payload = {"reply_to": "P-0-0"}
    form = PT.reply_to_form(payload, {"P-0-0"}, {"42:189"})
    assert form == "real_message_id_legacy_msg_id"
    assert PT.empty_forms()["real_message_id"] == 0     # 分子默认 0，legacy 单列


def test_msg_uid_wins_over_msg_id():
    """两个集合都命中时以 msg_uid 为准（主键优先）。"""
    payload = {"reply_to": "42:189"}
    assert PT.reply_to_form(payload, {"42:189"}, {"42:189"}) == "real_message_id"


# ---------------- T4 其它形态 ----------------
def test_other_forms_stay_exclusive():
    assert PT.reply_to_form({}, set(), set()) == "missing_key"
    assert PT.reply_to_form({"reply_to": None}, set(), set()) == "json_null"
    assert PT.reply_to_form({"reply_to": "None"}, set(), set()) == "string_None"
    assert PT.reply_to_form({"reply_to": ""}, set(), set()) == "empty_string"
    assert PT.reply_to_form({"reply_to": 123}, set(), set()) == "other"


def test_forms_keys_complete_and_zeroed():
    forms = PT.empty_forms()
    assert forms["real_message_id"] == 0
    assert forms["real_message_id_legacy_msg_id"] == 0
    assert sum(forms.values()) == 0
    assert set(forms) == {
        "missing_key", "json_null", "string_None", "empty_string",
        "real_message_id", "real_message_id_legacy_msg_id", "other",
    }


# ---------------- T5 端到端（真实历史批次，只读） ----------------
def test_scan_extra_log_on_arm_no_longer_zero():
    if not ON_LOG.is_file():
        import pytest
        pytest.skip(f"缺历史批次：{ON_LOG}")
    d = PT.scan_extra_log(ON_LOG)
    forms = d["reply_to_forms"]
    assert d["msg_public_total"] > 0
    assert forms["real_message_id"] > 0, "F-2 未修复时该值恒 0"
    # 口径闭合：非空 reply_to 条数 = uid 命中 + msg_id 回退 + other
    nonnull = d["msg_public_total"] - forms["json_null"] - forms["missing_key"]
    assert (forms["real_message_id"] + forms["real_message_id_legacy_msg_id"]
            + forms["other"]) == nonnull


def test_scan_extra_log_off_arm_still_zero():
    """OFF 臂 reply_to 全为 null ⇒ 修尺子不应凭空造出接话（0 仍是 0）。"""
    if not OFF_LOG.is_file():
        import pytest
        pytest.skip(f"缺历史批次：{OFF_LOG}")
    forms = PT.scan_extra_log(OFF_LOG)["reply_to_forms"]
    assert forms["real_message_id"] == 0
    assert forms["real_message_id_legacy_msg_id"] == 0


def test_uid_beats_msg_id_on_real_log():
    """真实日志里 msg_id 不唯一（PUB 多条共用 `P-0-0`）⇒ 按 msg_id 匹配本就不可能对。"""
    if not ON_LOG.is_file():
        import pytest
        pytest.skip(f"缺历史批次：{ON_LOG}")
    import json

    pub = []
    with ON_LOG.open(encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            ev = json.loads(raw)
            if ev.get("type") == "MSG_PUBLIC":
                pub.append(ev.get("payload") or {})
    uids = {p["msg_uid"] for p in pub if isinstance(p.get("msg_uid"), str)}
    mids = {p["msg_id"] for p in pub if isinstance(p.get("msg_id"), str)}
    assert len(uids) == len(pub)          # msg_uid 一条一个，唯一
    assert len(mids) < len(pub)           # msg_id 复用，不可作主键


if __name__ == "__main__":
    raise SystemExit(__import__("pytest").main([__file__, "-q"]))
