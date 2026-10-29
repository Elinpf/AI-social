# D9i 预登记 · amendment 1：**mock 验不了这个开关** —— 取消两臂 mock，改单测

> 立此件：Leader（team-leader）｜2026-10-30 01:40
> 上游：`D9i-prereg-narration-toggle.md`（`0555c2c8…` / 88 行 / `fc836b8`，已公示不覆盖）
> 由来：派卡后我核查 mock 实现，发现**预登记 §2 的主判据在 mock 下不可变**。

## 1. 发现（`code/life/llm.py:74-76`）

```python
elif purpose == "dialogue":
    tpl = (meta or {}).get("template", "")
    out = f"（{tpl or '闲聊'}）今天见到你真好，最近可好？"
```

⇒ `RuleBasedLLM` 的 dialogue 输出**完全由 `meta["template"]` 决定，`prompt` 一个字都不读**。

**反证**：若真走 `RuleBasedLLM`，每条 dialogue 都应带 `（template）` 前缀 ⇒ 旁白率 **100%**；但实测 `mock_d9c_recent` 旁白率 **0.00%**。
⇒ 说明 mock 臂**实际走 `freeze.client.FreezeLLM`**（`get_llm_client(prefer_freeze=True)` 先试它）——body 来自**冻结缓存**，缓存是"某条源臂"的产物，**不会因改 prompt 而重算**。

**结论：`LIFE_PROMPT_NARRATION` 对 mock 完全无效，两臂 mock 必然逐字节相同。**

## 2. 因此撤回与替换

| 预登记原文 | 处置 |
|---|---|
| §1「两臂固定 … `provider=mock`」+ 跑批 | **撤回跑批**（省 12 分钟，且必然给出"零差异"这个无信息结果） |
| §2 量 1「含成对括号旁白的 MSG 条数/占比」作**主判据** | **降级**：mock 下不可变 ⇒ 不能作主判据；改由**单测**验 prompt 字符串 |
| §2 量 2/3/4/5（台词字数 / L-7 / MSG·线程·≥3轮 / 旁白内动作类占比） | **全部降级为"需真 LLM 臂"**，本卡不产 |
| §3 判定四档 | **本卡不适用**（无跑批则无"触达"可判）；改为**接线验收**，判定留给真 LLM 批 |

## 3. 本卡改为「接线验收」——三条单测（写死）

| # | 断言 | 判据 |
|---|---|---|
| **T1** | `LIFE_PROMPT_NARRATION` 未设 / `=0` ⇒ 取到的 prompt 字符串**与改动前 master 的字面量逐字节相同** | `assert new == OLD_LITERAL`（把旧字符串固化为测试常量） |
| **T2** | `=1` ⇒ prompt **不含**「不要用括号、方括号或星号写动作、神态或心理旁白」，**且仍含**「只写台词本身」「一句家常话」 | 半句被去掉，其余一字未改 |
| **T3** | `_reply_prompt` 同理（`:1523`） | 同上 |

**另附**：`git diff --stat` 必须**只含 `code/life/agent.py` 的二处改动**（不得顺手改其它措辞）。

## 4. 这条 amendment 暴露的通用问题（要进恒真清单）

我在预登记 §2 写「主判据 = 旁白率（H0 = 0/686）」，**却没先确认"mock 能不能产生旁白"**。

⇒ 这正是 `invariant-true-checklist.md` 自检第一问的漏答：**"这个量在 H0 下能不能变？"** —— 对 mock 而言，**任何只改 prompt 的变量，其"输出文本类"指标恒不变**。

**一般化规则（新增到恒真清单）**：
> **凡改 prompt / 改措辞的实验，在 `provider=mock` 下"输出文本类"指标一律恒不变**（mock 不读 prompt，或读的是冻结缓存）。此类实验的 mock 只能验**接线**（字符串断言、调用次数、分支可达），**不能验任何文本指标**。

## 5. 真 LLM 臂（本卡不批，需预算）

| 项 | 估算 |
|---|---|
| 两臂（`NARRATION=0` vs `=1`），同 `code_sha`，唯一变量 | ≈2,598 次网络调用 / ≈80 min 串行 |
| 这是**唯一**能验"旁白通道值多少"的做法 | 变量干净、成本已知 |

**本卡范围内不跑真 LLM。**
