# T92 · freeze 支持 `LLM_CALL.purpose=dialogue`

> 作者：freeze-layer-dev ｜ 日期：2026-10-10
> 范围：冻结层（`code/freeze/`）；life 侧 `_communicate` 属 T94、engine `INTENT.SOCIAL` 属 T93
> 依据：`v2/03-dialogue-llm-plan.md`（T81 诊断）

---

## 1. 结论（TL;DR）

冻结层对 `purpose="dialogue"` 的支持**在 T30 冻结层基线中即已具备**（白名单含 `dialogue`、
`ThinkingPolicy` 默认 `false`）。因此 T92 在 freeze 侧是**确认 + 加固**，不是白名单新增：

- ✅ `purpose=dialogue` 可记账（`LLM_CALL` 带 `purpose/tier/tokens/thinking`）；
- ✅ `dialogue` 默认 `thinking=false`（未列入 `true_purposes`；仅 `judge/narrate/describe` 或 `T2` 为 true）；
- ✅ `thinking` 进缓存键（同 prompt 不同 thinking → 不同键）；
- ✅ 缓存/预算/`degraded` 兜底与既有 purpose 一致；重放 `llm_calls==0`。

**本轮 freeze 侧实际改动**：① `FreezeLLM.call` 新增可选形参 `thinking`（供 T94 显式覆盖，向后兼容）；
② `client.py` 文档更新为完整白名单；③ 新增 2 个 `dialogue` 专项单测。

---

## 2. purpose 白名单前后 diff

### 2.1 `freeze/config.py :: ALLOWED_PURPOSES`（冻结层记账入口）

```diff
  ALLOWED_PURPOSES = {
      "plan",        # 日/周计划内容
      "dialogue",    # 对话正文          <<< 基线已含（T30 即纳入），T92 无增删
      "reflect",     # 反思文本
      "importance",  # 记忆重要性
      "decide_t2",   # T2 决策内容/意图
      "describe",    # 描述性文字
      "judge",       # 软判定层
      "narrate",     # 叙事层
  }
```

- **before == after**（`dialogue` 本就在冻结层白名单内）。
- 反例保护不变：`FORBIDDEN_PURPOSES`（金额/死亡/结算）仍拦截。

### 2.2 `life/llm.py :: ALLOWED_PURPOSES`（life 侧窄接口，属 **T94**，非本任务改动面）

```diff
  ALLOWED_PURPOSES = frozenset({
      "plan", "reflect", "importance", "decide_t2", "describe", "judge", "narrate",
+     "dialogue",     # <<< T94 需补（life-layer-dev 计划 §3 已列）
  })
```

> ⚠️ 该文件属 life 模块（life-layer-dev / T94）。freeze 侧不越界改动；已在其计划中登记。
> freeze 路径（`FreezeLLM.call` → `LLMClient.complete`）**不受 life 白名单影响**，dialogue 已可用。

### 2.3 `config/llm.json :: thinking`（无需改）

`true_purposes=["judge","narrate","describe"]` 不含 `dialogue` → `dialogue` 默认 `thinking=false`（符合“求快”）。

---

## 3. 调用契约（freeze 对外）

`code/scripts`/life 侧统一入口：

```python
from freeze.client import FreezeLLM
freeze.call("dialogue", prompt, tier=Tier.T1, meta={"round": r})        # thinking 默认 False
freeze.call("dialogue", prompt, tier=Tier.T1, meta={"round": r}, thinking=True)  # 显式覆盖
```

- `LLMResult = {text, tokens_in, tokens_out, cache_key, model, degraded}`。
- `tier` 默认 `T1`（对话属短 prompt），`thinking` 未传则按 `ThinkingPolicy`（dialogue→False）。
- 记账：`LLM_CALL{purpose="dialogue", tier, model, tokens_in/out, thinking, cached, degraded}`。
- 重放：读缓存/日志，**零 LLM 调用**（`freeze.llm_calls==0`）。
- 超预算：沿 `T2→T1→T0` 降级；`T0` 由确定性模板兜底并记 `degraded=true`（即当前硬编码正文的等价物）。

---

## 4. 验证证据（`pytest`）

新增/相关单测：
- `test_dialogue_purpose_end_to_end`：白名单通过 → 记账（purpose=dialogue、thinking=false）→ thinking 进缓存键 → 重放 `llm_calls==0` → 预算 0 时 `degraded` 到 `T0`。
- `test_freeze_llm_dialogue_call_signature`：`call("dialogue", …, tier=T1, meta={round})` 形态 → thinking=false；显式 `thinking=True` 改键。
- 既有：`test_thinking_policy_defaults`（dialogue@T1 → False）、`test_cache_key_includes_thinking_and_model`（dialogue）、`test_replay_llm_calls_zero` 等。

```
$ python3 -m pytest -q
229 passed
$ python3 -m pytest -q tests/test_freeze.py
41 passed
```

---

## 5. 与 T93 / T94 的边界

- **T93（kernel-dev）**：`INTENT.SOCIAL` 合法化 + `_do_social`（DM/PUBLIC/GROUP，配额/去重/可见性）——不在 freeze。
- **T94（life-layer-dev）**：`agent._communicate` 调 `llm.call("dialogue", …, tier=T1, meta={round})`；补 `life/llm.py` 白名单；`settlement._m6_specs` 去硬编码正文。
- freeze 侧**就绪，无阻塞**；对话正文为 N 类内容，重放读日志不重调 LLM，确定性不受影响。
