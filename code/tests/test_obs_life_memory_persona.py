"""T233：`metrics.life.memory`（睡眠/遗忘/整合）与 `metrics.life.persona` 口径测试。

口径来源：`v1.1/08-engine-stats-extension.md` §1.2 S（新事件字段）与建议统计口径
  `metrics.life.memory{ forget_count_by_level, retention_hist, protected_kept, consolidate_count }`
  `metrics.life.persona{ drift_permille, pf0, pf_t }`
纪律：只读日志、纯函数、确定性、llm_calls == 0；obs **不复刻 life 的保护规则**，只 count 事件。
"""

import json

from obs.life import life_metrics, memory_metrics, persona_metrics


def _rec(t, **payload):
    return {"type": t, "payload": payload, "round": 0, "phase": 35, "actor": "SYSTEM",
            "seq": 0, "mono_ts": 0, "prev_hash": "x", "hash": "y"}


def _base_log():
    return [
        _rec("AGENT_BORN", agent_id="P001"),
        _rec("AGENT_BORN", agent_id="P002"),
        # 写入/检索/反思（既有口径）
        _rec("MEMORY_WRITE", agent_id="P001", importance=6, mem_id="M-1"),
        _rec("MEMORY_WRITE", agent_id="P002", importance=4, mem_id="M-2"),
        _rec("MEMORY_RETRIEVE", agent_id="P001", selected_mem_ids=["M-1"], scores=[0.9]),
        _rec("MEMORY_RETRIEVE", agent_id="P002", selected_mem_ids=[], scores=[]),
        _rec("MEMORY_REFLECT", agent_id="P001", produced_mem_id="R-1"),
        # 遗忘（三级 + 保护）
        _rec("MEMORY_FORGET", agent_id="P001", mem_id="M-9", level="demote",
             retention_permille=520, protected=True, protection_reason="importance"),
        _rec("MEMORY_FORGET", agent_id="P001", mem_id="M-8", level="merge",
             retention_permille=250, protected=False, protection_reason=None),
        _rec("MEMORY_FORGET", agent_id="P002", mem_id="M-7", level="drop",
             retention_permille=40, protected=False, protection_reason=None),
        _rec("MEMORY_FORGET", agent_id="P002", mem_id="M-6", level="drop",
             retention_permille=1000, protected=True, protection_reason="access"),
        # 整合
        _rec("MEMORY_CONSOLIDATE", agent_id="P001", source_mem_ids=["M-1", "M-2"],
             produced_mem_id="S-1", subject="P007"),
        # 人格：睡眠携带指纹视图 + 漂移
        _rec("SLEEP_COMPLETED", agent_id="P001", pf0="pf0-P001", pf_t="pfT-P001",
             drift_permille=120),
        _rec("PERSONA_DRIFT", agent_id="P001", dim="openness", before=55, after=56,
             anchor=55, pf0="pf0-P001", pf_t="pfT-P001b", drift_permille=130),
        _rec("SLEEP_COMPLETED", agent_id="P002", pf0="pf0-P002", pf_t="pfT-P002",
             drift_permille=40),
    ]


def test_memory_metrics_include_forget_and_consolidate():
    m = memory_metrics(_base_log())
    # 既有键保留
    assert m["mem_write_count"] == 2 and m["mem_reflect_count"] == 1
    assert m["retrieval_hit_rate"] == 0.5
    # 遗忘
    assert m["forget_count"] == 4
    assert m["forget_count_by_level"] == {"demote": 1, "merge": 1, "drop": 2}
    assert m["protected_kept"] == 2
    assert m["protected_by_reason"] == {"access": 1, "importance": 1}
    hist = m["retention_hist"]
    assert hist["0-99"] == 1        # 40
    assert hist["200-299"] == 1     # 250
    assert hist["500-599"] == 1     # 520
    assert hist["1000"] == 1        # 1000
    assert sum(hist.values()) == 4
    # 整合
    assert m["consolidate_count"] == 1
    assert m["consolidate_source_count"] == 2
    assert m["consolidate_by_subject"] == {"P007": 1}


def test_persona_metrics_drift_and_fingerprint():
    p = persona_metrics(_base_log())
    assert p["n_drift_events"] == 1
    assert p["drift_by_dim"]["openness"] == 1
    # P001 最新指纹取 PERSONA_DRIFT（后于其 SLEEP_COMPLETED）；P002 取 SLEEP_COMPLETED
    assert p["n_fingerprint_views"] == 2
    assert p["pf0"] == {"P001": "pf0-P001", "P002": "pf0-P002"}
    assert p["pf_t"]["P001"] == "pfT-P001b"
    assert p["drift_permille"] == {"mean": 85.0, "max": 130, "min": 40}
    assert p["drift_coverage"] == 1.0  # 2/2 alive


def test_life_metrics_has_persona_namespace_and_is_deterministic():
    a = life_metrics(_base_log())
    b = life_metrics(_base_log())
    assert "persona" in a and "memory" in a
    assert json.dumps(a, sort_keys=True, ensure_ascii=False) == \
           json.dumps(b, sort_keys=True, ensure_ascii=False)


def test_empty_log_is_defined():
    m = memory_metrics([])
    assert m["forget_count"] == 0 and m["consolidate_count"] == 0
    assert m["retention_hist"] and sum(m["retention_hist"].values()) == 0
    p = persona_metrics([])
    assert p["n_drift_events"] == 0 and p["drift_permille"]["max"] == 0
