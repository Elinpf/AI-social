"""T222: M2b「受限选择」路径（life 侧）单元测试。

覆盖：候选枚举单一真源/逃生项、默认关=旧生成式逐项一致、判别式分派、逃生回退、
失败可见回退、escape_rate/fallback_rate 聚合、mentor_relation inert（无调用点）。
"""
from __future__ import annotations

import re
from pathlib import Path

import life.constants as C
import life.policy as P
from life.soft import SoftLayer, rng_branch
from obs.admission import judge_method_rates

LIFE_DIR = Path(__file__).resolve().parents[1] / "life"  # code/life


# ---- fake freeze inner (mimics freeze.llm_client.LLMClient surface) -----------
class _Judg:
    def __init__(self, decision, model="m", digest="d", margin=None):
        self.decision, self.model, self.context_digest, self.margin = decision, model, digest, margin


class _Inner:
    def __init__(self, disc_decision=None, disc_margin=None, disc_raises=False,
                 gen_decision="not_formed"):
        self._dd, self._dm, self._dr, self._gd = disc_decision, disc_margin, disc_raises, gen_decision
        self.emitted: list = []

    def judge(self, **kw):
        return _Judg(self._gd)

    def judge_discriminative(self, **kw):
        if self._dr:
            raise RuntimeError("provider/parse failure")
        return _Judg(self._dd, margin=self._dm)


class _Base:
    def __init__(self, inner):
        self.client = inner


def _soft(inner):
    return SoftLayer(_Base(inner))


def _kwargs(**over):
    base = dict(judgment_id="J1", dimension="rel_affinity", question_ref="q",
                envelope={"options": ["formed", "not_formed", "undecidable"]},
                rng_branch="formed", parties=["P1", "P2"], context={"x": 1}, round_no=5)
    base.update(over)
    return base


# ---- 1. candidate-enumeration single source -----------------------------------
def test_judgment_options_complete_and_escaped():
    for dim, opts in C.JUDGMENT_OPTIONS.items():
        assert len(opts) >= 2, f"{dim}: 需要 ≥2 候选"
        assert len(set(opts)) == len(opts), f"{dim}: 候选必须互斥（去重后不等）"
        assert C.ESCAPE_OPTION in opts, f"{dim}: 必须有逃生项 {C.ESCAPE_OPTION}"
    assert set(C.ESCAPE_FALLBACK) == set(C.JUDGMENT_OPTIONS), "每个维度都要有逃生兜底"
    for dim, fb in C.ESCAPE_FALLBACK.items():
        assert fb in C.JUDGMENT_OPTIONS[dim], f"{dim}: 兜底值 {fb!r} 必须是合法候选"


def test_judgment_options_cover_emitted_dims():
    src = (LIFE_DIR / "agent.py").read_text(encoding="utf-8")
    m = re.search(r"if\s+dim\s+not\s+in\s*\(([^)]*)\)\s*:", src)
    rel = [f"rel_{d}" for d in re.findall(r'"([a-z_]+)"', m.group(1))]
    app = re.findall(r'\(\s*"(stance|respect|affection)"\s*,\s*\[', src)
    emitted = set(rel) | set(app) | {"weekly_focus"}
    missing = emitted - set(C.JUDGMENT_OPTIONS)
    assert not missing, f"已发射维度缺候选表: {missing}"


# ---- 2. switch: default OFF == old generative path ---------------------------
def test_m2b_default_is_generative():
    P.set_m2b_config(None)
    assert P.m2b_judge_mode() == "generative"
    assert P.m2b_importance_mode() == "generative"
    P.set_m2b_config(None)


def test_generative_payload_has_no_method_key():
    inner = _Inner(gen_decision="formed")
    payload, emitted = _soft(inner).judge(**_kwargs())  # default mode=generative
    assert payload["decision"] == "formed" and emitted is True
    assert "method" not in payload, "默认（旧路径）payload 不得新增字段（逐项一致）"


# ---- 3. discriminative dispatch + escape resolution ---------------------------
def test_discriminative_dispatch_basic():
    inner = _Inner(disc_decision="formed", disc_margin=0.4)
    payload, emitted = _soft(inner).judge(**_kwargs(mode="discriminative"))
    assert payload["decision"] == "formed" and payload["method"] == "discriminative"
    assert payload["margin"] == 0.4 and payload["resolved"] == "formed"


def test_escape_option_resolves_to_fallback():
    innel = _Inner(disc_decision=C.ESCAPE_OPTION)
    payload, _ = _soft(innel).judge(**_kwargs(mode="discriminative"))
    assert payload["decision"] == C.ESCAPE_OPTION                 # 日志保留模型原话（escape 可聚合）
    assert payload["resolved"] == C.ESCAPE_FALLBACK["rel_affinity"]  # 下游消费兜底值


def test_discriminative_failure_visible_rng_fallback():
    inner = _Inner(disc_raises=True)
    payload, _ = _soft(inner).judge(**_kwargs(mode="discriminative", rng_branch="formed"))
    assert payload["decision"] == "formed"       # rng 分支兜底
    assert payload["method"] == "rng-branch" and payload.get("fallback") is True


# ---- 4. observability: escape_rate / fallback_rate (obs 唯一口径) -------------
def test_judgment_rates_aggregation():
    recs = [
        {"type": "LLM_JUDGMENT", "payload": {"dimension": "rel_affinity", "decision": "formed", "method": "discriminative"}},
        {"type": "LLM_JUDGMENT", "payload": {"dimension": "rel_affinity", "decision": C.ESCAPE_OPTION, "method": "discriminative"}},
        {"type": "LLM_JUDGMENT", "payload": {"dimension": "rel_affinity", "decision": "not_formed", "method": "rng-branch"}},
        {"type": "LLM_JUDGMENT", "payload": {"dimension": "respect", "decision": "high", "method": "discriminative"}},
        {"type": "LLM_JUDGMENT", "payload": {"dimension": "mentor_relation", "decision": "formed", "method": "discriminative"}},
    ]
    r = judge_method_rates(recs)
    assert r["rel_affinity"]["n"] == 3
    assert abs(r["rel_affinity"]["escape_rate"] - 1 / 3) < 1e-6
    assert abs(r["rel_affinity"]["fallback_rate"] - 1 / 3) < 1e-6
    assert r["respect"]["escape_rate"] == 0.0
    assert r["mentor_relation"]["inert"] is True   # inert 单列、不进 mainline


# ---- 5. mentor_relation is registered but INERT ------------------------------
def test_mentor_relation_inert_no_call_site():
    assert C.MENTOR_DIMENSION_WIRED is False
    assert "mentor_relation" in C.JUDGMENT_OPTIONS  # 已登记
    src = (LIFE_DIR / "agent.py").read_text(encoding="utf-8")
    assert 'dimension="mentor_relation"' not in src, "life 不应自称已接线 mentor_relation"


# ---- 6. end-to-end: discriminative ON runs and tags method -------------------
def test_e2e_discriminative_runs_and_tags_method(tmp_path):
    from orchestration.integration import build_world
    from engine import conservation

    P.set_m2b_config({"judge_mode": "discriminative", "importance_mode": "discriminative",
                      "fallback": "none", "margin_theta": 0.0})
    try:
        w = build_world(seed=7, n=3, side_root=str(tmp_path / "side"))
        eng = w["engine"]
        for r in range(12):
            eng.run_round(r)
    finally:
        P.set_m2b_config(None)

    recs = eng.ledger.records
    methods = {rec["payload"].get("method") for rec in recs if rec["type"] == "LLM_JUDGMENT"}
    assert "discriminative" in methods, f"M2b 开启后应产出 method=discriminative，实际 {methods}"
    # decisions must stay within their envelope options (约束解码 + 二次校验)
    for rec in recs:
        if rec["type"] != "LLM_JUDGMENT":
            continue
        opts = (rec["payload"].get("envelope") or {}).get("options")
        if opts:
            assert rec["payload"]["decision"] in opts
    assert conservation.check_conservation(eng.state, eng.config) == []
    assert eng.ledger.verify_chain()[0] is True

