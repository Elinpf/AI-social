"""冻结层单元测试（stdlib unittest，无第三方依赖）。

覆盖任务验收四条：
  ① 重放路径 ``llm_calls == 0``；
  ② 同一 prompt 二次调用命中缓存、不重复计费；
  ③ 冻结判定含四要素 decision/model/context_digest/frozen=true；
  ④ 降级链 T2→T1→T0 可被测试触发。

另含：缓存键含 engine_version/prompt_hash、哈希链、嵌入冻结、金额/死亡/结算
用途拦截、窄接口 FreezeLLM。

运行：``python -m unittest discover -s tests -v``（在 code/ 目录下）。
"""

from __future__ import annotations

import json
import math
import os
import sys
import tempfile
import time
import unittest
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from freeze import (  # noqa: E402
    EventLog,
    FreezeConfig,
    FrozenStore,
    LLMBudget,
    LLMClient,
    MockProvider,
    Mode,
    Priority,
    Tier,
    assert_purpose_allowed,
)
from freeze.client import FreezeLLM  # noqa: E402
from freeze.llm_client import CacheMissError, InvalidDecisionError  # noqa: E402


def make_config(tmp: str, engine_version: str = "v1.1+test", mode: Mode = Mode.RUN) -> FreezeConfig:
    return FreezeConfig(engine_version=engine_version, mode=mode, cache_dir=tmp)


class FreezeLayerTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ------------------------------------------------------------------ #
    # ① 重放路径 llm_calls == 0
    # ------------------------------------------------------------------ #
    def test_replay_llm_calls_zero(self) -> None:
        provider = MockProvider()
        run = LLMClient(make_config(self.tmp), provider=provider, event_log=EventLog())
        r1 = run.complete(purpose="plan", system="sys", user="week plan A")
        self.assertEqual(run.llm_calls, 1)

        # 重放：独立 provider（若被调用，计数会变），共享缓存目录
        replay_provider = MockProvider()
        replay = LLMClient(
            make_config(self.tmp, mode=Mode.REPLAY),
            provider=replay_provider,
            event_log=EventLog(),
        )
        r2 = replay.complete(purpose="plan", system="sys", user="week plan A")
        self.assertEqual(replay.llm_calls, 0)
        self.assertEqual(replay_provider.calls, 0, "重放不得触发 provider 真实调用")
        self.assertTrue(r2.cached)
        self.assertEqual(r1.text, r2.text)
        self.assertEqual(r1.cache_key, r2.cache_key)

    def test_replay_judgment_reads_frozen_zero_calls(self) -> None:
        judge_provider = MockProvider(responder=lambda s, u, e: "formed")
        run = LLMClient(make_config(self.tmp), provider=judge_provider, event_log=EventLog())
        j1 = run.judge(
            judgment_id="J-1",
            dimension="mentor_relation",
            question_ref="q.mentor.v1",
            envelope={"options": ["formed", "not_formed"], "rng_branch": "b0"},
            context={"a": "alice", "b": "bob"},
            rng_branch="b0",
            parties=["alice", "bob"],
        )
        self.assertEqual(j1.decision, "formed")
        self.assertEqual(run.llm_calls, 1)

        replay = LLMClient(
            make_config(self.tmp, mode=Mode.REPLAY),
            provider=MockProvider(responder=lambda s, u, e: "not_formed"),
            event_log=EventLog(),
        )
        # IF-6 读回：绝不重问 LLM
        j2 = replay.get_frozen_judgment("J-1")
        self.assertEqual(j2.decision, "formed")
        self.assertEqual(replay.llm_calls, 0)
        # judge() 在重放模式直接读冻结
        j3 = replay.judge(
            judgment_id="J-1",
            dimension="mentor_relation",
            question_ref="q.mentor.v1",
            envelope={"options": ["formed", "not_formed"]},
            context={},
        )
        self.assertEqual(j3.decision, "formed")
        self.assertEqual(replay.llm_calls, 0)

    def test_replay_cache_miss_raises(self) -> None:
        replay = LLMClient(
            make_config(self.tmp, mode=Mode.REPLAY),
            provider=MockProvider(),
            event_log=EventLog(),
        )
        with self.assertRaises(CacheMissError):
            replay.complete(purpose="plan", system="", user="never seen before")
        self.assertEqual(replay.llm_calls, 0)

    # ------------------------------------------------------------------ #
    # ② 同一 prompt 二次调用命中缓存，不重复计费
    # ------------------------------------------------------------------ #
    def test_second_call_hits_cache_no_double_charge(self) -> None:
        provider = MockProvider()
        budget = LLMBudget(limit=100)
        client = LLMClient(
            make_config(self.tmp), provider=provider, event_log=EventLog(), budget=budget
        )
        r1 = client.complete(purpose="dialogue", system="s", user="hello there")
        r2 = client.complete(purpose="dialogue", system="s", user="hello there")

        self.assertEqual(provider.calls, 1, "同 prompt 只应真实调用一次")
        self.assertEqual(client.llm_calls, 1)
        self.assertFalse(r1.cached)
        self.assertTrue(r2.cached)
        self.assertEqual(r1.text, r2.text)
        self.assertEqual(budget.spent, 3, "只应扣一次 T2 成本")

        # 事件分列：两次 LLM_CALL（一次真实、一次 cached），无重复计费
        calls = client.event_log.of_type("LLM_CALL")
        self.assertEqual(len(calls), 2)
        self.assertFalse(calls[0]["payload"]["cached"])
        self.assertTrue(calls[1]["payload"]["cached"])
        self.assertEqual(calls[1]["payload"]["cost_units"], 0)

    # ------------------------------------------------------------------ #
    # ③ 冻结判定含四要素
    # ------------------------------------------------------------------ #
    def test_mock_judge_decision_in_options(self) -> None:
        """回归（T54）：MockProvider 的 judge 必须**确定性地**落在 envelope.options 内。"""
        client = LLMClient(make_config(self.tmp), provider=MockProvider(), event_log=EventLog())
        for i, opts in enumerate([["a", "b", "c"], ["formed", "not_formed"], ["x", "y"]]):
            env = {"options": opts}
            j1 = client.judge(judgment_id=f"J{i}", dimension="mentor_relation",
                              question_ref="q", envelope=env, context={"i": i})
            self.assertIn(j1.decision, opts, f"mock judge 越界：{j1.decision} ∉ {opts}")
            # 可复现：相同 envelope/context → 相同 decision
            j2 = client.judge(judgment_id=f"J{i}b", dimension="mentor_relation",
                              question_ref="q", envelope=env, context={"i": i})
            self.assertEqual(j1.decision, j2.decision)

    def test_frozen_judgment_four_elements(self) -> None:
        provider = MockProvider(responder=lambda s, u, e: "formed")
        client = LLMClient(make_config(self.tmp), provider=provider, event_log=EventLog())
        j = client.judge(
            judgment_id="J-42",
            dimension="mentor_relation",
            question_ref="q.mentor.v1",
            envelope={"options": ["formed", "not_formed"], "rng_branch": "b1"},
            context={"who": ["alice", "bob"], "reason": "shared work"},
            rng_branch="b1",
            parties=["alice", "bob"],
        )
        ev = client.event_log.of_type("LLM_JUDGMENT")
        self.assertEqual(len(ev), 1)
        payload = ev[0]["payload"]
        # 四要素
        self.assertEqual(payload["decision"], "formed")
        self.assertEqual(payload["model"], provider.model)
        self.assertTrue(payload["context_digest"])
        self.assertIs(payload["frozen"], True)
        # 分列：判定与成本分别是两类事件
        self.assertEqual(j.decision, "formed")
        self.assertTrue(client.event_log.of_type("LLM_CALL"))

    def test_judgment_normalizes_json_decision(self) -> None:
        provider = MockProvider(responder=lambda s, u, e: '{"mentor_relation":"not_formed"}')
        client = LLMClient(make_config(self.tmp), provider=provider, event_log=EventLog())
        j = client.judge(judgment_id="J-json", dimension="mentor_relation", question_ref="q",
                         envelope={"options": ["formed", "not_formed"]}, context={"x": 1})
        self.assertEqual(j.decision, "not_formed")

    def test_invalid_decision_rejected(self) -> None:
        provider = MockProvider(responder=lambda s, u, e: "nonsense")
        client = LLMClient(make_config(self.tmp), provider=provider, event_log=EventLog())
        with self.assertRaises(InvalidDecisionError):
            client.judge(
                judgment_id="J-bad",
                dimension="mentor_relation",
                question_ref="q",
                envelope={"options": ["formed", "not_formed"]},
                context={"x": 1},
            )
        self.assertTrue(client.event_log.of_type("SYSTEM_ERROR"))

    # ------------------------------------------------------------------ #
    # ④ 降级链可被测试触发
    # ------------------------------------------------------------------ #
    def test_degradation_chain_triggered(self) -> None:
        # limit=1：T2(成本3) 不可负担 → 降到 T1(成本1)
        budget = LLMBudget(limit=1)
        provider = MockProvider()
        client = LLMClient(
            make_config(self.tmp), provider=provider, event_log=EventLog(), budget=budget
        )
        r = client.complete(purpose="plan", system="", user="degrade me", tier=Tier.T2)
        self.assertEqual(r.tier, Tier.T1.value)
        self.assertTrue(r.degraded)
        self.assertEqual(client.llm_calls, 1)
        call = client.event_log.of_type("LLM_CALL")[-1]["payload"]
        self.assertTrue(call["degraded"])
        self.assertEqual(call["tier"], Tier.T1.value)

    def test_degradation_to_t0_no_llm_call(self) -> None:
        # limit=0：T2/T1 都不可负担 → T0（确定性兜底，零 LLM 调用）
        budget = LLMBudget(limit=0)
        provider = MockProvider()
        client = LLMClient(
            make_config(self.tmp),
            provider=provider,
            event_log=EventLog(),
            budget=budget,
            fallback=lambda **kw: "RULE_FALLBACK",
        )
        r = client.complete(purpose="plan", system="", user="force t0", tier=Tier.T2)
        self.assertEqual(r.tier, Tier.T0.value)
        self.assertTrue(r.degraded)
        self.assertEqual(r.text, "RULE_FALLBACK")
        self.assertEqual(client.llm_calls, 0)
        self.assertEqual(provider.calls, 0)
        call = client.event_log.of_type("LLM_CALL")[-1]["payload"]
        self.assertTrue(call["degraded"])
        # 缓存已落盘 → 二次调用命中缓存
        r2 = client.complete(purpose="plan", system="", user="force t0", tier=Tier.T2)
        self.assertTrue(r2.cached)

    def test_resolve_chain_direct(self) -> None:
        from freeze.config import Tier as T

        self.assertEqual(LLMBudget(limit=None).resolve(T.T2).tier, T.T2)
        self.assertEqual(LLMBudget(limit=3).resolve(T.T2).tier, T.T2)
        d = LLMBudget(limit=1).resolve(T.T2)
        self.assertEqual(d.tier, T.T1)
        self.assertTrue(d.degraded)
        d0 = LLMBudget(limit=0).resolve(T.T1)
        self.assertEqual(d0.tier, T.T0)
        # CRITICAL 绕过预算
        crit = LLMBudget(limit=0).resolve(T.T2, Priority.CRITICAL)
        self.assertEqual(crit.tier, T.T2)
        self.assertFalse(crit.degraded)

    # ------------------------------------------------------------------ #
    # 缓存键：含 engine_version 与 prompt_hash
    # ------------------------------------------------------------------ #
    def test_cache_key_depends_on_engine_version_and_prompt(self) -> None:
        c1 = LLMClient(make_config(self.tmp, "ev-A"), provider=MockProvider(), event_log=EventLog())
        c2 = LLMClient(make_config(self.tmp, "ev-B"), provider=MockProvider(), event_log=EventLog())
        ph = c1._prompt_hash("s", "u", {})
        k1 = c1.make_cache_key(ph, kind="plan", model="m", tier="T2")
        k1b = c1.make_cache_key(ph, kind="plan", model="m", tier="T2")
        k2 = c2.make_cache_key(ph, kind="plan", model="m", tier="T2")
        self.assertEqual(k1, k1b, "同输入键应确定")
        self.assertNotEqual(k1, k2, "engine_version 变化必须改变缓存键")

        # prompt 变化 → prompt_hash 变化 → 缓存键变化
        ph2 = c1._prompt_hash("s", "u2", {})
        self.assertNotEqual(ph, ph2)
        self.assertNotEqual(k1, c1.make_cache_key(ph2, kind="plan", model="m", tier="T2"))

        # 事件载荷显式携带 engine_version 与 prompt_hash（可审计）
        c1.complete(purpose="plan", system="s", user="u")
        call = c1.event_log.of_type("LLM_CALL")[0]["payload"]
        self.assertEqual(call["engine_version"], "ev-A")
        self.assertTrue(call["prompt_hash"].startswith("sha256:"))
        self.assertNotEqual(call["prompt_hash"], c1._prompt_hash("s", "u2", {}))

    # ------------------------------------------------------------------ #
    # 哈希链
    # ------------------------------------------------------------------ #
    def test_event_hash_chain(self) -> None:
        log = EventLog()
        log.append("A", {"x": 1}, round=0, phase=2)
        log.append("B", {"y": 2}, round=0, phase=2)
        log.append("C", {"z": 3}, round=1, phase=2)
        self.assertTrue(log.verify())
        # 篡改即失效
        log.records[1]["payload"]["y"] = 999
        self.assertFalse(log.verify())

    # ------------------------------------------------------------------ #
    # 嵌入冻结
    # ------------------------------------------------------------------ #
    def test_embedding_freeze_and_replay(self) -> None:
        provider = MockProvider(embed_dim=4)
        run = LLMClient(make_config(self.tmp), provider=provider, event_log=EventLog())
        v1 = run.embed("memory text")
        v2 = run.embed("memory text")  # 命中缓存
        self.assertEqual(run.embed_calls, 1)
        self.assertEqual(v1, v2)
        self.assertEqual(provider.embed_calls, 1)

        replay_provider = MockProvider(embed_dim=4)
        replay = LLMClient(
            make_config(self.tmp, mode=Mode.REPLAY),
            provider=replay_provider,
            event_log=EventLog(),
        )
        v3 = replay.embed("memory text")
        self.assertEqual(v3, v1)
        self.assertEqual(replay.embed_calls, 0)
        self.assertEqual(replay_provider.embed_calls, 0)

    def test_embedding_key_includes_model_version(self) -> None:
        provider = MockProvider(embed_model="mock-embed-1")
        c = LLMClient(make_config(self.tmp), provider=provider, event_log=EventLog())
        k = c.embedder.make_cache_key("t", model="mock-embed-1")
        self.assertNotEqual(k, c.embedder.make_cache_key("t", model="other-embed"))
        self.assertNotEqual(k, c.embedder.make_cache_key("t2", model="mock-embed-1"))

    # ------------------------------------------------------------------ #
    # 金额/死亡/结算用途拦截
    # ------------------------------------------------------------------ #
    def test_forbidden_purposes_rejected(self) -> None:
        for p in ["settle", "apply_tax", "check_death", "mint", "transfer_amount"]:
            with self.assertRaises(ValueError):
                assert_purpose_allowed(p)
        client = LLMClient(make_config(self.tmp), provider=MockProvider(), event_log=EventLog())
        with self.assertRaises(ValueError):
            client.complete(purpose="check_death", system="", user="")
        self.assertEqual(client.llm_calls, 0)

    # ------------------------------------------------------------------ #
    # 叙事层：不改状态
    # ------------------------------------------------------------------ #
    def test_narrative_affects_state_false(self) -> None:
        client = LLMClient(make_config(self.tmp), provider=MockProvider(), event_log=EventLog())
        client.narrate(fact_event_seqs=[0, 1, 2], narrative_id="N-1", body_ref="side://N-1")
        narr = client.event_log.of_type("NARRATIVE")
        self.assertEqual(len(narr), 1)
        self.assertIs(narr[0]["payload"]["affects_state"], False)
        self.assertTrue(narr[0]["payload"]["anchor_digest"])

    def test_anchor_digest_deterministic(self) -> None:
        a = LLMClient.compute_anchor_digest([1, 2, 3])
        b = LLMClient.compute_anchor_digest([1, 2, 3])
        c = LLMClient.compute_anchor_digest([1, 2, 4])
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    # ------------------------------------------------------------------ #
    # 窄接口 FreezeLLM
    # ------------------------------------------------------------------ #
    def test_freeze_llm_narrow_interface(self) -> None:
        client = LLMClient(make_config(self.tmp), provider=MockProvider(), event_log=EventLog())
        freeze = FreezeLLM(client)
        r = freeze.call("plan", "plan for tomorrow", meta={"agent_id": "a1"})
        self.assertIsInstance(r.text, str)
        self.assertEqual(r.tokens_in, 8)
        self.assertEqual(r.tokens_out, 8)
        self.assertTrue(r.cache_key)
        self.assertTrue(r.model)
        self.assertFalse(r.degraded)
        self.assertEqual(freeze.llm_calls, 1)
        # 二次命中缓存
        r2 = freeze.call("plan", "plan for tomorrow", meta={"agent_id": "a1"})
        self.assertEqual(r.cache_key, r2.cache_key)
        self.assertEqual(freeze.llm_calls, 1)

    def test_freeze_llm_call_uses_meta_round(self) -> None:
        """回归：life 经 FreezeLLM.call 时，round 应取自 meta['round']（非 0）。"""
        client = LLMClient(make_config(self.tmp), provider=MockProvider(), event_log=EventLog())
        freeze = FreezeLLM(client)
        freeze.call("plan", "p", meta={"agent_id": "P001", "round": 7})
        freeze.call("importance", "x", meta={"agent_id": "P001"})  # 无 round → 0（权威由内核兜底）
        calls = client.event_log.of_type("LLM_CALL")
        rounds = {c["payload"]["purpose"]: c["round"] for c in calls}
        self.assertEqual(rounds["plan"], 7)
        self.assertEqual(rounds["importance"], 0)

    def test_freeze_llm_replay(self) -> None:
        client = LLMClient(make_config(self.tmp), provider=MockProvider(), event_log=EventLog())
        FreezeLLM(client).call("reflect", "reflect on today")
        replay = LLMClient(
            make_config(self.tmp, mode=Mode.REPLAY),
            provider=MockProvider(),
            event_log=EventLog(),
        )
        freeze2 = FreezeLLM(replay)
        freeze2.call("reflect", "reflect on today")
        self.assertEqual(freeze2.llm_calls, 0)

    # ------------------------------------------------------------------ #
    # 存储一致性
    # ------------------------------------------------------------------ #
    def test_store_roundtrip(self) -> None:
        store = FrozenStore(self.tmp)
        store.put_response("k1", {"text": "x", "model": "m"})
        self.assertTrue(store.has_response("k1"))
        self.assertEqual(store.get_response("k1")["text"], "x")
        self.assertEqual(store.response_keys(), ["k1"])

    # ------------------------------------------------------------------ #
    # 确定性词法相关度（T48 方案②）
    # ------------------------------------------------------------------ #
    def test_lexical_provider_deterministic(self) -> None:
        from freeze import LexicalProvider

        p = LexicalProvider()
        v1 = p.embed("老李托我修锄头")
        v2 = p.embed("老李托我修锄头")
        self.assertEqual(v1, v2, "同文本必须同向量（可复现）")
        self.assertEqual(len(v1), p.dim)
        self.assertNotEqual(v1, p.embed("银行申请贷款"))

    def test_lexical_ranking_prefers_overlap(self) -> None:
        from freeze import LexicalProvider, RelevanceRanker

        mem = ["老李托我修锄头", "银行申请贷款", "广场晒谷物", "锄头修好了给老李"]
        r = RelevanceRanker(LexicalProvider().embed).rank("锄头的约定", mem, top_k=2)
        got = {x.index for x in r}
        self.assertTrue(got & {0, 3}, "词面相关的记忆应排进 top-2")
        self.assertNotIn(1, got)

    def test_cosine_basic(self) -> None:
        from freeze.relevance import cosine

        self.assertAlmostEqual(cosine([1, 0], [1, 0]), 1.0, places=6)
        self.assertAlmostEqual(cosine([1, 0], [0, 1]), 0.0, places=6)
        self.assertEqual(cosine([0, 0], [1, 1]), 0.0)

    def test_embedding_freeze_with_lexical_provider(self) -> None:
        from freeze import LexicalProvider

        run = LLMClient(make_config(self.tmp), provider=MockProvider(),
                        event_log=EventLog())
        run.embedder.provider = LexicalProvider()
        run.embedder.model = "frozen://lexical-relevance-v1"
        v1 = run.embed("记忆正文")
        v2 = run.embed("记忆正文")
        self.assertEqual(v1, v2)
        self.assertEqual(run.embed_calls, 1, "二次命中缓存不重算")

        replay = LLMClient(make_config(self.tmp, mode=Mode.REPLAY),
                           provider=MockProvider(), event_log=EventLog())
        replay.embedder.provider = LexicalProvider()
        replay.embedder.model = "frozen://lexical-relevance-v1"
        self.assertEqual(replay.embed("记忆正文"), v1)
        self.assertEqual(replay.embed_calls, 0, "重放不重算嵌入")

    def test_lexical_embed_model_in_key(self) -> None:
        from freeze import LexicalProvider

        p = LexicalProvider()
        c = LLMClient(make_config(self.tmp), provider=p, event_log=EventLog())
        # EmbeddingFreezer 默认取 provider.embed_model
        self.assertEqual(c.embedder.model, "frozen://lexical-relevance-v1")

    # ------------------------------------------------------------------ #
    # IF-2c 审计桥（audit_sink）
    # ------------------------------------------------------------------ #
    def test_audit_sink_receives_events_on_run(self) -> None:
        seen = []
        client = LLMClient(
            make_config(self.tmp), provider=MockProvider(responder=lambda s, u, e: "formed"),
            event_log=EventLog(),
            audit_sink=lambda kind, payload, rnd, ph: seen.append((kind, rnd, ph)),
        )
        client.complete(purpose="dialogue", system="", user="hi", round=1, phase=2)
        client.judge(judgment_id="J1", dimension="d", question_ref="q",
                     envelope={"options": ["formed", "not_formed"]}, context={"x": 1},
                     round=2, phase=2)
        client.narrate(fact_event_seqs=[0], narrative_id="N1", body_ref="side://N1",
                       round=3, phase=2)
        kinds = [k for k, _, _ in seen]
        self.assertIn("LLM_CALL", kinds)
        self.assertIn("LLM_JUDGMENT", kinds)
        self.assertIn("NARRATIVE", kinds)
        self.assertEqual([r for _, r, _ in seen], [1, 2, 2, 3, 3])  # judge/narrate 各含内部 LLM_CALL

    def test_audit_sink_not_called_on_replay(self) -> None:
        # 先 run 落缓存
        LLMClient(make_config(self.tmp), provider=MockProvider(), event_log=EventLog()).complete(
            purpose="dialogue", system="", user="hi", round=1)
        seen = []
        replay = LLMClient(
            make_config(self.tmp, mode=Mode.REPLAY), provider=MockProvider(),
            event_log=EventLog(),
            audit_sink=lambda kind, payload, rnd, ph: seen.append(kind),
        )
        replay.complete(purpose="dialogue", system="", user="hi", round=1)
        self.assertEqual(seen, [], "重放绝不回调 audit_sink")

    # ------------------------------------------------------------------ #
    # T92：purpose="dialogue"（M6 对话正文，N 类内容）
    # ------------------------------------------------------------------ #
    def test_dialogue_purpose_end_to_end(self) -> None:
        from freeze import assert_purpose_allowed

        assert_purpose_allowed("dialogue")  # 白名单通过，不被禁

        run = LLMClient(make_config(self.tmp), provider=MockProvider(),
                        event_log=EventLog(), budget=LLMBudget(limit=100))
        r1 = run.complete(purpose="dialogue", system="s", user="你好", tier=Tier.T1)
        self.assertFalse(r1.cached)
        call = run.event_log.of_type("LLM_CALL")[-1]["payload"]
        self.assertEqual(call["purpose"], "dialogue")     # 可记账
        self.assertIs(call["thinking"], False)            # dialogue 默认 thinking=false
        # thinking 进缓存键（防错命中）
        r_t = run.complete(purpose="dialogue", system="s", user="你好",
                           tier=Tier.T1, thinking=True)
        self.assertNotEqual(r_t.cache_key, r1.cache_key)

        # 重放：读缓存，零 LLM 调用
        replay = LLMClient(make_config(self.tmp, mode=Mode.REPLAY),
                           provider=MockProvider(), event_log=EventLog())
        r2 = replay.complete(purpose="dialogue", system="s", user="你好", tier=Tier.T1)
        self.assertTrue(r2.cached)
        self.assertEqual(replay.llm_calls, 0)

        # 预算兜底：degraded → T0（确定性模板，零 LLM 调用）
        c0 = LLMClient(make_config(self.tmp + "-d"), provider=MockProvider(),
                       event_log=EventLog(), budget=LLMBudget(limit=0),
                       fallback=lambda **kw: "TPL")
        rd = c0.complete(purpose="dialogue", system="s", user="hi", tier=Tier.T1)
        self.assertEqual(rd.tier, Tier.T0.value)
        self.assertTrue(rd.degraded)
        self.assertEqual(rd.text, "TPL")
        self.assertEqual(c0.llm_calls, 0)

    def test_freeze_llm_dialogue_call_signature(self) -> None:
        """T94 调用形态：call("dialogue", prompt, tier=T1, meta={round}) → thinking=false。"""
        client = LLMClient(make_config(self.tmp), provider=MockProvider(), event_log=EventLog())
        freeze = FreezeLLM(client)
        r = freeze.call("dialogue", "你好呀", tier=Tier.T1, meta={"round": 3})
        self.assertTrue(r.text)
        call = client.event_log.of_type("LLM_CALL")[-1]["payload"]
        self.assertEqual(call["purpose"], "dialogue")
        self.assertEqual(call["tier"], "T1")
        self.assertIs(call["thinking"], False)
        # 显式 thinking 覆盖 → 不同缓存键
        r2 = freeze.call("dialogue", "你好呀", tier=Tier.T1, meta={"round": 3}, thinking=True)
        self.assertNotEqual(r.cache_key, r2.cache_key)

    # ------------------------------------------------------------------ #
    # T132：purpose="negotiation"（议价/条款内容，N 类）
    # ------------------------------------------------------------------ #
    def test_negotiation_purpose_end_to_end(self) -> None:
        from freeze import assert_purpose_allowed

        assert_purpose_allowed("negotiation")  # 白名单通过，不被禁

        run = LLMClient(make_config(self.tmp), provider=MockProvider(),
                        event_log=EventLog(), budget=LLMBudget(limit=100))
        # 居民议价：T1 → thinking=false
        r1 = run.complete(purpose="negotiation", system="s", user="议价：木料多少",
                          tier=Tier.T1)
        c1 = run.event_log.of_type("LLM_CALL")[-1]["payload"]
        self.assertEqual(c1["purpose"], "negotiation")
        self.assertEqual(c1["tier"], "T1")
        self.assertIs(c1["thinking"], False)
        # 世界 LLM：T2 → thinking=true
        r2 = run.complete(purpose="negotiation", system="s", user="议价：木料多少",
                          tier=Tier.T2)
        c2 = run.event_log.of_type("LLM_CALL")[-1]["payload"]
        self.assertIs(c2["thinking"], True)
        # thinking/tier 进缓存键
        self.assertNotEqual(r1.cache_key, r2.cache_key)

        # 重放：读缓存，零 LLM 调用
        replay = LLMClient(make_config(self.tmp, mode=Mode.REPLAY),
                           provider=MockProvider(), event_log=EventLog())
        r3 = replay.complete(purpose="negotiation", system="s", user="议价：木料多少",
                             tier=Tier.T1)
        self.assertTrue(r3.cached)
        self.assertEqual(replay.llm_calls, 0)

        # obs 可统计（同 dialogue/judge 同构）
        from obs.llmcost import llm_cost_from_records

        out = llm_cost_from_records(run.event_log.records)
        self.assertGreaterEqual(out["by_purpose"]["negotiation"]["calls"], 1)

    def test_unknown_purpose_still_rejected(self) -> None:
        """不要放水：未登记 purpose 仍 fail（negotiation 加入不影响该底线）。"""
        from freeze import assert_purpose_allowed

        with self.assertRaises(ValueError):
            assert_purpose_allowed("not_registered_purpose")
        client = LLMClient(make_config(self.tmp), provider=MockProvider(), event_log=EventLog())
        with self.assertRaises(ValueError):
            client.complete(purpose="bogus", system="", user="")
        self.assertEqual(client.llm_calls, 0)

    def test_negotiation_whitelists_aligned(self) -> None:
        from freeze.config import ALLOWED_PURPOSES as F
        from life.llm import ALLOWED_PURPOSES as L

        content_purposes = {"plan", "dialogue", "negotiation", "reflect", "importance",
                            "decide_t2", "describe"}
        self.assertIn("negotiation", F)
        self.assertIn("negotiation", L)
        self.assertTrue(content_purposes <= F)
        self.assertTrue(content_purposes <= L)

    # ------------------------------------------------------------------ #
    # 集成：life 层窄接口自动采用 freeze.client.FreezeLLM
    # ------------------------------------------------------------------ #
    def test_no_arg_freeze_llm_offline(self) -> None:
        os.environ["FREEZE_CACHE_DIR"] = self.tmp
        try:
            freeze = FreezeLLM()
            r = freeze.call("plan", "hello")
            self.assertEqual(r.model, "mock-1")
            self.assertFalse(r.degraded)
        finally:
            os.environ.pop("FREEZE_CACHE_DIR", None)

    def test_life_layer_resolves_freeze_client(self) -> None:
        os.environ["FREEZE_CACHE_DIR"] = self.tmp
        try:
            import life.llm as life_llm

            client = life_llm.get_llm_client()
        finally:
            os.environ.pop("FREEZE_CACHE_DIR", None)
        self.assertIsInstance(client, FreezeLLM)
        r = client.call("reflect", "reflect on today")
        self.assertTrue(r.text)


    # ------------------------------------------------------------------ #
    # thinking 策略（按 purpose/tier 集中裁决）
    # ------------------------------------------------------------------ #
    def test_thinking_policy_defaults(self) -> None:
        from freeze import ThinkingPolicy

        pol = ThinkingPolicy()
        # 常规居民决策/对话（T1）→ 关
        self.assertFalse(pol.resolve("dialogue", Tier.T1))
        self.assertFalse(pol.resolve("plan", Tier.T1))
        self.assertFalse(pol.resolve("reflect", Tier.T1))
        self.assertFalse(pol.resolve("importance", Tier.T1))
        # 软判定 / 叙事 → 恒开
        self.assertTrue(pol.resolve("judge", Tier.T1))
        self.assertTrue(pol.resolve("narrate", Tier.T1))
        self.assertTrue(pol.resolve("describe", Tier.T1))
        # T2 重大决策 → 开
        self.assertTrue(pol.resolve("decide_t2", Tier.T2))
        # 策略指纹可查（纳入 engine_version）
        self.assertIn("true_purposes", pol.fingerprint())

    def test_thinking_flag_threads_into_event(self) -> None:
        client = LLMClient(make_config(self.tmp), provider=MockProvider(), event_log=EventLog())
        client.complete(purpose="dialogue", system="", user="hi", tier=Tier.T1)
        client.complete(purpose="judge", system="", user="j", tier=Tier.T1)
        calls = client.event_log.of_type("LLM_CALL")
        self.assertIs(calls[0]["payload"]["thinking"], False)
        self.assertIs(calls[1]["payload"]["thinking"], True)

    def test_engine_version_with_thinking_fingerprint(self) -> None:
        cfg = make_config(self.tmp, "evX")
        self.assertTrue(cfg.engine_version_with_policy().startswith("evX|thinking="))

    def test_cache_key_includes_thinking_and_model(self) -> None:
        """同一 prompt 在 thinking/model 不同时必须是不同缓存键（防错命中）。"""
        client = LLMClient(make_config(self.tmp), provider=MockProvider(), event_log=EventLog())
        r_false = client.complete(purpose="dialogue", system="s", user="u",
                                  tier=Tier.T1, thinking=False)
        r_true = client.complete(purpose="dialogue", system="s", user="u",
                                 tier=Tier.T1, thinking=True)
        self.assertNotEqual(r_false.cache_key, r_true.cache_key,
                            "thinking 必须进缓存键")
        # model 进缓存键
        ph = client._prompt_hash("s", "u", {"thinking": False})
        k_a = client.make_cache_key(ph, kind="dialogue", model="m-A", tier="T1",
                                    params={"thinking": False})
        k_b = client.make_cache_key(ph, kind="dialogue", model="m-B", tier="T1",
                                    params={"thinking": False})
        self.assertNotEqual(k_a, k_b, "model 必须进缓存键")

    def test_default_safety_budget_limits(self) -> None:
        from freeze import (
            DEFAULT_ROUND_CALL_LIMIT,
            DEFAULT_RUN_CALL_LIMIT,
            default_safety_budget,
        )

        b = default_safety_budget()
        self.assertEqual(b.call_limit, DEFAULT_RUN_CALL_LIMIT)
        self.assertEqual(b.round_call_limit, DEFAULT_ROUND_CALL_LIMIT)

    def test_run_call_cap_safety_valve(self) -> None:
        budget = LLMBudget(call_limit=1)
        client = LLMClient(make_config(self.tmp), provider=MockProvider(),
                           event_log=EventLog(), budget=budget)
        client.complete(purpose="dialogue", system="", user="a1", round=0)
        r2 = client.complete(purpose="dialogue", system="", user="a2", round=0)
        self.assertEqual(r2.tier, Tier.T0.value)
        self.assertTrue(r2.degraded)
        self.assertEqual(client.llm_calls, 1, "触顶后不得再真实调用")

    def test_round_call_cap_safety_valve(self) -> None:
        budget = LLMBudget(round_call_limit=1)
        client = LLMClient(make_config(self.tmp), provider=MockProvider(),
                           event_log=EventLog(), budget=budget)
        client.complete(purpose="dialogue", system="", user="b1", round=5)
        r2 = client.complete(purpose="dialogue", system="", user="b2", round=5)
        self.assertEqual(r2.tier, Tier.T0.value)  # 同回合触顶
        r3 = client.complete(purpose="dialogue", system="", user="b3", round=6)
        self.assertNotEqual(r3.tier, Tier.T0.value)  # 新回合恢复

    def test_openai_provider_body_includes_thinking(self) -> None:
        from freeze.providers import OpenAICompatProvider

        captured = {}

        def fake_post(self, path, body):
            captured["body"] = body
            return {"choices": [{"message": {"content": "ok"}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                    "model": body["model"]}

        prov = OpenAICompatProvider("http://x/v1", "k", "m")
        prov._post = fake_post.__get__(prov, OpenAICompatProvider)
        prov.complete(system="s", user="u", extra={"purpose": "dialogue", "thinking": False})
        self.assertEqual(captured["body"]["chat_template_kwargs"], {"thinking": False})
        prov.complete(system="s", user="u", extra={"purpose": "judge", "thinking": True})
        self.assertEqual(captured["body"]["chat_template_kwargs"], {"thinking": True})

    # ------------------------------------------------------------------ #
    # T222：judge_discriminative（受限选择 + thinking=false + margin）
    # ------------------------------------------------------------------ #
    def test_judge_discriminative_end_to_end(self) -> None:
        provider = MockProvider()
        run = LLMClient(make_config(self.tmp), provider=provider, event_log=EventLog())
        fj = run.judge_discriminative(
            judgment_id="DJ-1", dimension="mentor_relation", question_ref="q.mentor.v1",
            envelope={"options": ["formed", "not_formed"], "threshold": 0.5, "rng_branch": "b0"},
            context={"a": "alice", "b": "bob"}, rng_branch="b0", parties=["alice", "bob"],
        )
        self.assertIn(fj.decision, ["formed", "not_formed"])
        self.assertIsNotNone(fj.margin)          # 回传候选分差
        self.assertIsNotNone(fj.label_probs)
        # LLM_JUDGMENT：四要素 + margin（只增不改）
        ev = run.event_log.of_type("LLM_JUDGMENT")[-1]["payload"]
        self.assertIs(ev["frozen"], True)
        self.assertEqual(ev["model"], provider.model)
        self.assertTrue(ev["context_digest"])
        self.assertIn("margin", ev)
        # thinking=false（判别式路径）
        call = run.event_log.of_type("LLM_CALL")[-1]["payload"]
        self.assertEqual(call["purpose"], "judge")
        self.assertIs(call["thinking"], False)

        # 重放：读冻结判定，零 LLM 调用
        replay = LLMClient(make_config(self.tmp, mode=Mode.REPLAY),
                           provider=MockProvider(), event_log=EventLog())
        fj2 = replay.judge_discriminative(
            judgment_id="DJ-1", dimension="mentor_relation", question_ref="q.mentor.v1",
            envelope={"options": ["formed", "not_formed"]}, context={},
        )
        self.assertEqual(fj2.decision, fj.decision)
        self.assertEqual(replay.llm_calls, 0)

    def test_judge_discriminative_invalid_raises(self) -> None:
        provider = MockProvider(responder=lambda s, u, e: "nonsense")
        run = LLMClient(make_config(self.tmp), provider=provider, event_log=EventLog())
        with self.assertRaises(InvalidDecisionError):
            run.judge_discriminative(
                judgment_id="DJ-bad", dimension="d", question_ref="q",
                envelope={"options": ["formed", "not_formed"]}, context={"x": 1},
            )
        self.assertTrue(run.event_log.of_type("SYSTEM_ERROR"))

    def test_judge_discriminative_method_optional(self) -> None:
        run = LLMClient(make_config(self.tmp), provider=MockProvider(), event_log=EventLog())
        run.judge_discriminative(
            judgment_id="DJ-m", dimension="d", question_ref="q",
            envelope={"options": ["formed", "not_formed"]}, context={},
            method="discriminative",
        )
        ev = run.event_log.of_type("LLM_JUDGMENT")[-1]["payload"]
        self.assertEqual(ev.get("method"), "discriminative")
        # 不传 method → 不加字段
        run.judge_discriminative(
            judgment_id="DJ-m2", dimension="d", question_ref="q",
            envelope={"options": ["formed", "not_formed"]}, context={"y": 2},
        )
        ev2 = run.event_log.of_type("LLM_JUDGMENT")[-1]["payload"]
        self.assertNotIn("method", ev2)

    def test_option_probs_helper(self) -> None:
        from freeze.llm_client import LLMClient as _C

        lp = {"content": [{"token": "formed", "logprob": math.log(0.9),
                           "top_logprobs": [{"token": "formed", "logprob": math.log(0.9)},
                                            {"token": "not_formed", "logprob": math.log(0.1)}]}]}
        probs = _C._option_probs(lp, ["formed", "not_formed"])
        self.assertAlmostEqual(probs["formed"], 0.9, places=6)
        self.assertAlmostEqual(probs["not_formed"], 0.1, places=6)
        self.assertIsNone(_C._option_probs(None, ["formed"]))

    # ------------------------------------------------------------------ #
    # T227：可选 prompt 正文落盘（默认关 + 抽样 + 容量上限 + 脱敏硬门）
    # ------------------------------------------------------------------ #
    def _capture_path(self):
        return os.path.join(self.tmp, "prompts", "prompts.jsonl")

    def test_capture_default_off_no_write(self) -> None:
        client = LLMClient(make_config(self.tmp), provider=MockProvider(), event_log=EventLog())
        client.complete(purpose="dialogue", system="s", user="u")
        self.assertFalse(client.capture.is_active())
        self.assertFalse(os.path.exists(self._capture_path()))
        self.assertEqual(client.capture.stats()["written"], 0)

    def test_capture_purpose_selective(self) -> None:
        import base64
        import zlib

        from freeze.capture import CaptureConfig

        cfg = make_config(self.tmp)
        cfg.capture = CaptureConfig(enabled=True, mode="purpose")
        client = LLMClient(cfg, provider=MockProvider(), event_log=EventLog())
        client.complete(purpose="dialogue", system="s", user="u1")
        client.complete(purpose="judge", system="s", user="u2")   # 排除
        lines = open(self._capture_path(), encoding="utf-8").read().strip().splitlines()
        self.assertEqual(len(lines), 1)
        rec = json.loads(zlib.decompress(base64.b64decode(json.loads(lines[0])["z"])))
        self.assertEqual(rec["purpose"], "dialogue")
        self.assertEqual(rec["user"], "u1")

    def test_capture_sample_deterministic(self) -> None:
        from freeze.capture import CaptureConfig, PromptCapture

        cap = PromptCapture(CaptureConfig(enabled=True, mode="sample", sample_rate=0.5), root=self.tmp)
        a = [cap.should_capture("dialogue", sample_key=f"k{i}") for i in range(20)]
        cap2 = PromptCapture(CaptureConfig(enabled=True, mode="sample", sample_rate=0.5), root=self.tmp)
        b = [cap2.should_capture("dialogue", sample_key=f"k{i}") for i in range(20)]
        self.assertEqual(a, b, "抽样必须确定性可复现")

    def test_capture_redaction_reverse_verification(self) -> None:
        from freeze.capture import CaptureConfig

        secret = "sk-supersecret-1234567890"
        cfg = make_config(self.tmp)
        cfg.capture = CaptureConfig(enabled=True, mode="purpose")
        client = LLMClient(cfg, provider=MockProvider(), event_log=EventLog())
        client.capture.redact_terms = [secret]
        client.complete(purpose="dialogue", system=f"sys key={secret}",
                        user=f"see https://172.16.3.41:31809/v1 with {secret}")
        txt = open(self._capture_path(), encoding="utf-8").read()
        self.assertNotIn(secret, txt)                 # 反向验证：key 不得入盘
        self.assertNotIn("172.16.3.41:31809", txt)    # 端点不得入盘

    def test_capture_refusal_gate(self) -> None:
        from freeze.capture import CaptureConfig, PromptCapture

        cap = PromptCapture(CaptureConfig(enabled=True, mode="purpose"), root=os.path.join(self.tmp, "prompts"))
        cap.redact = lambda t: t                        # 模拟 redact 失效 → 扫描必须拦住
        ok = cap.write({"purpose": "dialogue", "user": "https://x/v1", "output": "y"})
        self.assertFalse(ok)
        self.assertEqual(cap.refused, 1)
        self.assertFalse(os.path.exists(self._capture_path()))

    def test_capture_scan_clean(self) -> None:
        from freeze.capture import CaptureConfig, PromptCapture

        cap = PromptCapture(CaptureConfig(), root=self.tmp)
        self.assertFalse(cap.scan_clean("see https://h/v1"))
        self.assertFalse(cap.scan_clean("Authorization: Bearer abcdef123456"))
        self.assertFalse(cap.scan_clean("sk-abcdef123456"))
        self.assertTrue(cap.scan_clean("clean town dialogue"))

    def test_capture_capacity_cap(self) -> None:
        from freeze.capture import CaptureConfig

        cfg = make_config(self.tmp)
        cfg.capture = CaptureConfig(enabled=True, mode="purpose", max_bytes=200)
        client = LLMClient(cfg, provider=MockProvider(), event_log=EventLog())
        for i in range(50):
            client.complete(purpose="dialogue", system="s", user=f"u{i}" * 20)
        self.assertGreater(client.capture.capped, 0, "超容量上限应停写并计数")
        self.assertTrue(client.capture.truncated, "触顶必须显式标记，不得静默停写")
        txt = open(self._capture_path(), encoding="utf-8").read()
        self.assertIn("capture_truncated", txt)      # 文件内 marker
        self.assertLessEqual(os.path.getsize(self._capture_path()), 200 + 1024)

    def test_capture_ttl_cleanup(self) -> None:
        from freeze.capture import CaptureConfig, PromptCapture

        cap = PromptCapture(CaptureConfig(enabled=True, mode="purpose", ttl_seconds=1), root=os.path.join(self.tmp, "prompts"))
        cap.write({"purpose": "dialogue", "user": "u", "output": "o"})
        p = self._capture_path()
        self.assertTrue(os.path.exists(p))
        os.utime(p, (time.time() - 10, time.time() - 10))   # 变旧
        cap._maybe_cleanup()
        self.assertFalse(os.path.exists(p))

    def test_capture_fingerprint_in_engine_version(self) -> None:
        from freeze.capture import CaptureConfig

        cfg_off = make_config(self.tmp, "evCap")
        cfg_on = make_config(self.tmp, "evCap")
        cfg_on.capture = CaptureConfig(enabled=True, mode="purpose")
        self.assertIn("capture=", cfg_off.engine_version_with_policy())
        self.assertNotEqual(cfg_off.engine_version_with_policy(),
                            cfg_on.engine_version_with_policy())

    # ------------------------------------------------------------------ #
    # T228（freeze 侧）：side 分档契约 + 降级标记 schema
    # ------------------------------------------------------------------ #
    def test_side_persist_vec_switch(self) -> None:
        from freeze import side

        os.environ.pop(side.PERSIST_VEC_ENV, None)
        self.assertTrue(side.resolve_persist_vec())          # 缺省=True（行为不变）
        os.environ[side.PERSIST_VEC_ENV] = "0"
        self.assertFalse(side.resolve_persist_vec())
        os.environ[side.PERSIST_VEC_ENV] = "1"
        self.assertTrue(side.resolve_persist_vec())
        os.environ.pop(side.PERSIST_VEC_ENV, None)

    def test_side_fingerprint_and_marker(self) -> None:
        from freeze import side

        self.assertEqual(side.side_fingerprint(True), {"persist_vec": True})
        m_off = side.degradation_marker(vec_available=False)
        self.assertFalse(m_off[side.VEC_AVAILABLE_FIELD])
        self.assertEqual(m_off[side.RETRIEVAL_MODE_FIELD], "lexical")   # 显式降级
        m_on = side.degradation_marker(vec_available=True)
        self.assertEqual(m_on[side.RETRIEVAL_MODE_FIELD], "vector")
        with self.assertRaises(ValueError):
            side.degradation_marker(vec_available=False, retrieval_mode="bogus")

    def test_embed_for_side_respects_switch(self) -> None:
        from freeze import side

        prov = MockProvider(embed_dim=4)
        on = side.embed_for_side("t", prov, persist_vec=True)
        self.assertIsNotNone(on.vector)
        self.assertTrue(on.vec_available)
        off = side.embed_for_side("t", prov, persist_vec=False)
        self.assertIsNone(off.vector)                     # 不产 .vec
        self.assertFalse(off.vec_available)
        self.assertEqual(off.retrieval_mode, "lexical")
        self.assertEqual(prov.embed_calls, 1)             # 关闭时不调用嵌入


if __name__ == "__main__":
    unittest.main(verbosity=2)
