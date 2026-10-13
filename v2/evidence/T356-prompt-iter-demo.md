# T356 演示：一次真实「改提示词 → 跑 → 比」（`prompt_iter` 回路）

## 演示设置（同 seed/同配置，只差提示词）
- 工具：`tools/prompt_iter/prompt_iter.py`（复用 `T227` capture）；样本 `n=8 × 24 回合 × seed=7`（默认配置）。
- **v0_baseline**：`prompt_sha=a242146926cef105`
- **v1_tone**：在 `life/agent.py::_dialogue_prompt` 追加一句
  「语气口语化、带一点个人情绪与态度（可含动作/神态），不要客套套话。」
  ⇒ `prompt_sha=9e52f3686b7c8db6`
- **`life/agent.py` 改动已还原**（演示后 `git status` 干净、`grep 语气口语化` = 0；HEAD `4ac8807`）。

## 回路读数（`compare v0_baseline v1_tone`）
- **行为差异（事件类型计数 A→B）**：**无**；**首个 `state_hash` 不等回合**：**无（全等）**。
- **正文并排**：`dialogue/negotiation/plan/reflect` 逐条可并排（工具输出）；两版 llm_calls 均 435、cached 201、captured 67。
- **观察**：**mock 下正文取自 provider 词池、且按 `hash(system+user)` 选取** ⇒ 改提示词**改变了"选到哪条"**（A/B 文本顺序不同），但**不是"更人格化"的语义变化**。

## ⚠️ 关键口径（必须写清）
1. **mock 迭代的边界**：mock **不读懂提示词**（从池里按 hash 选句子）⇒ **"改了提示词文本却没变好"在 mock 下无意义**；**真正的提示词迭代需真 LLM**（`HITT_LLM_PROVIDER=openai_compat` + `code/.env.local`），或先用 `T325` 的 mock 保真度改进。
2. **缓存/指纹**：改提示词 ⇒ `prompt_hash` 变 ⇒ `cache_key` 变 ⇒ **全部新答案**（`freeze/llm_client.py::_cache_key` 必含 `engine_version`+`prompt_hash`）⇒ **与改配置同族**；**不得用整周跑批试提示词**、**不得污染 `T300`/`T355` 基线**。
3. **本演示证明的是"回路可用"**（改→跑→比、版本号、并排、行为/成本对照），**不是**"v1 更好"。

## 复现
```
python3 tools/prompt_iter/prompt_iter.py run <tag> --n 8 --rounds 24 --seed 7
python3 tools/prompt_iter/prompt_iter.py compare <tagA> <tagB>
```
