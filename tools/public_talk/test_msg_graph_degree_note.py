#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""看板 A-4 回归测试：`msg_graph_degree.note` / 图注文案必须由实测值生成。

运行：
    cd <repo> && python3 -m pytest tools/public_talk/test_msg_graph_degree_note.py -q
    cd <repo> && python3 tools/public_talk/test_msg_graph_degree_note.py

背景（CYCLE-47 §159 / N-1 / 看板 A-3→A-4）
-------------------------------------------
旧 `note` 是一段**写死**的人话：「公开消息在消息图里入度 0、**出边 0**，是孤立节点」。
在 `v2/evidence/d47-ruler-f2-20261101_n16r24_s42/readings/readings_d47_newruler.json`
这批里，同对象的实测是 `isolated_nodes=false`、`pub_out_degree_reply_nonnull=4`
⇒ **同一份 JSON 里文案与数字互相打脸**。修法：note 由纯函数
`public_talk_metrics.msg_graph_degree_note()` 按实测计数拼接，孤立判定与
`isolated_nodes_any` 同口径；`tools/metrics/round_figures.py` 的图注同理。

T1 纯函数：全零 ⇒ 「判为孤立节点」；任一非零 ⇒ 「不是孤立节点」，且数字齐全。
T2 端到端：真实 d47 证据上，note 的孤立判定 == `isolated_nodes_any`（不再矛盾）。
T3 端到端：真实全零臂（r41v off）上，note 的孤立判定同样 == `isolated_nodes_any`。
T4 图注：`round_figures._diag_extract` 入度优先取主口径 `pub_in_degree_total_any`。
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "tools" / "metrics"))

import public_talk_metrics as PT  # noqa: E402

D47 = REPO / "v2" / "evidence" / "d47-ruler-f2-20261101_n16r24_s42"
OFF_ARM = REPO / "v2" / "evidence" / "r41v_public_talk_n16r24_s42" / "off"

_SAYS_ISO = "判为孤立节点"
_SAYS_NOT = "不是孤立节点"


def _run_ruler(log: Path, meta: Path | None) -> dict:
    out = Path(tempfile.mkdtemp()) / "readings.json"
    cmd = [sys.executable, str(HERE / "public_talk_metrics.py"), "--log", str(log), "--out", str(out)]
    if meta is not None and meta.exists():
        cmd += ["--meta", str(meta)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return json.loads(out.read_text(encoding="utf-8"))["msg_graph_degree"]


# ---------------------------------------------------------------- T1 纯函数

def test_t1_note_isolated_when_all_zero():
    note = PT.msg_graph_degree_note(n_dm_reply=10, dm_hit_dm=10, dm_hit_pub=0,
                                    pub_in_total_any=0, in_by_channel={},
                                    pub_out_reply=0, pub_out_refs=0)
    assert _SAYS_ISO in note and _SAYS_NOT not in note, note
    assert "出边 0" in note, note


def test_t1_note_not_isolated_when_out_edges_nonzero():
    """核心回归：出边非零时**不得**再说「孤立节点」。"""
    note = PT.msg_graph_degree_note(n_dm_reply=117, dm_hit_dm=117, dm_hit_pub=0,
                                    pub_in_total_any=4, in_by_channel={"MSG_PUBLIC": 4},
                                    pub_out_reply=4, pub_out_refs=0)
    assert _SAYS_NOT in note and _SAYS_ISO not in note, note
    for num in ("117", "4"):
        assert num in note, note


def test_t1_note_in_degree_nonzero_only():
    note = PT.msg_graph_degree_note(n_dm_reply=5, dm_hit_dm=5, dm_hit_pub=0,
                                    pub_in_total_any=2, in_by_channel={"MSG_DM": 2},
                                    pub_out_reply=0, pub_out_refs=0)
    assert _SAYS_NOT in note, note


# ---------------------------------------------------------------- T2/T3 端到端

def test_t2_real_evidence_note_matches_isolated_flag():
    log = D47 / "run.jsonl"
    if not log.exists():
        print(f"[skip] 缺证据：{log}", file=sys.stderr)
        return
    g = _run_ruler(log, D47 / "meta.json")
    iso = g["isolated_nodes_any"]
    if iso:
        assert _SAYS_ISO in g["note"] and _SAYS_NOT not in g["note"], g["note"]
    else:
        assert _SAYS_NOT in g["note"] and _SAYS_ISO not in g["note"], g["note"]
    assert g["note_consistency"]["note_says_isolated"] == g["note_consistency"]["isolated_nodes_any"]
    # 本批实测：isolated_nodes=false 而旧 note 说「孤立节点」——正是被修掉的那种矛盾
    assert iso is False, iso
    assert g["pub_out_degree_reply_nonnull"] == 4, g["pub_out_degree_reply_nonnull"]


def test_t3_zero_arm_note_matches_isolated_flag():
    log = OFF_ARM / "run.jsonl"
    if not log.exists():
        print(f"[skip] 缺证据：{log}", file=sys.stderr)
        return
    g = _run_ruler(log, OFF_ARM / "meta.json")
    iso = g["isolated_nodes_any"]
    assert g["note_consistency"]["note_says_isolated"] == iso
    assert (_SAYS_ISO in g["note"]) == bool(iso), g["note"]


# ---------------------------------------------------------------- T4 图注

def test_t4_diag_extract_prefers_main_in_degree_field():
    import round_figures as RF  # 需要 matplotlib；缺失即视为环境不支持，跳过
    d47 = D47 / "readings" / "readings_d47_newruler.json"
    if not d47.exists():
        print(f"[skip] 缺读数：{d47}", file=sys.stderr)
        return
    d = RF._diag_extract(str(d47))
    # 老读数只有 dm-only 字段 ⇒ 走兼容分支，但必须显式标注所用字段
    assert d["in_deg_field"] in ("pub_in_degree_total_any", "pub_in_degree_total"), d
    # 主口径存在时必须优先（用一份含主口径的 JSON 验证）
    tmp = Path(tempfile.mkdtemp()) / "with_any.json"
    tmp.write_text(json.dumps({"msg_graph_degree": {"pub_in_degree_total_any": 4,
                                                    "pub_in_degree_total": 0,
                                                    "pub_out_degree_reply_nonnull": 4,
                                                    "isolated_nodes": False,
                                                    "isolated_nodes_any": False}}),
                   encoding="utf-8")
    d2 = RF._diag_extract(str(tmp))
    assert d2["in_deg"] == 4 and d2["in_deg_field"] == "pub_in_degree_total_any", d2
    assert d2["isolated_nodes"] is False, d2


if __name__ == "__main__":
    try:
        import pytest
        raise SystemExit(pytest.main([__file__, "-q"]))
    except ImportError:
        fails = 0
        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                try:
                    fn()
                    print(f"[ok] {name}")
                except Exception as exc:  # noqa: BLE001
                    fails += 1
                    print(f"[FAIL] {name}: {exc}", file=sys.stderr)
        raise SystemExit(1 if fails else 0)
