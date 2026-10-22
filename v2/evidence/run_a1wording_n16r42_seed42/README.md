# A1 措辞臂（`run_a1wording_n16r42_seed42`）—— **实际窗口 34 轮 / 非 42 轮**

> ⚠️ **引用规则（先读这条）**：本目录**不得按「42 轮」引用**。
> 实际窗口 = **34 轮**（`TURN_SEAL` 覆盖 `round 0..33`，无重复）。
> 任何与本目录相关的对照，必须显式声明「**窗口 34 轮**」，并只与 **A0 前缀 `round 0..33`** 比较。

## 1. 实际内容（全部由日志复算）

| 项 | 值 |
|---|---|
| 事件行数 | **51,426**（可解析 51,426，解析失败 0） |
| `TURN_SEAL` | **34**，覆盖 `round 0..33`，**无重复 round** |
| 消息 | **MSG 284**（`MSG_DM 255` + `MSG_PUBLIC 29` + `MSG_GROUP 0`） |
| `LLM_CALL` | **2,389**，`provider` 全 **`openai_compat`** |
| `cached` | **1,415 / 2,389 = 59.2%** |
| `SYSTEM_ERROR` | **0** |
| `dialogue_rift`（F4） | **0**（F4 默认关，未激活） |
| `sha256(run.jsonl)` | `800ab1f8490c73341857e6efd31a60df6a6ec56ae4140227a161a4dd1a7d6037`（sha8 `800ab1f8`） |

## 2. 配置与单变量说明

- 代码：`a637371`（A1 措辞提交）的**只读副本** `/tmp/t271-a1wording`（`git archive` 解出，非工作树）；
- **运行期 override**：`life_v2.dialogue.reply_window_rounds=2`
  —— `a637371` 里该常量为 `4`（D9 实验），而对照臂 A0 是 `2`；用 `--override` 在内存里恢复成 `2`，
  **不落盘、不改 `engine_version` 指纹**（两臂指纹均为 `sha256:a871e36c…`）。
  ⇒ A1 相对 A0 的行为差异**只剩两行提示词**（`_dialogue_prompt` / `_reply_prompt` 收尾指令）。
- 冷/热缓存：段1（`round 0–13`，**冷缓存**）**3.0 分钟/回合**；段2/段3（热缓存）**0.4–1.2 分钟/回合**。
  同一批内差 3–7 倍 ⇒ **墙钟与调用数不可与 A0（51% 热缓存）直接比较，只比内容读数**。

## 3. 为什么只有 34 轮、且没有 `meta.json`

- 计划为 42 轮、分三段续跑（`14 + 14 + 14`），前两段 `rc=0`；
- **段3 在实际到 `round 33` 后未正常收尾**（环境反复清扫后台会话，之前已有多次），
  因此 **`meta.json` 未生成**，`run.jsonl` 停在最后一个 `TURN_SEAL`（`round 33`）——
  这是**合法的不完整前缀**，不是被截断的脏文件（`round` 单调、seal 无重复、无解析失败）。

## 4. 与本次交付相关的校验

```bash
# round 单调 + seal 无重复 + 全文可解析（= 证明 --resume-from 是「截断到最后一个 seal 再续写」，不是 append）
python3 - <<'PY'
import json
rs=[json.loads(l) for l in open('v2/evidence/run_a1wording_n16r42_seed42/run.jsonl')]
seals=[r['round'] for r in rs if r['type']=='TURN_SEAL']
assert seals==sorted(seals) and len(seals)==len(set(seals)), "seal 非单调或有重复"
assert seals==list(range(0, seals[-1]+1)), "seal 有跳号"
print("OK seals", len(seals), "covers 0..%d" % seals[-1])
PY
# 真跑判定（运行期 provider）
cd code && python3 -m obs llm-cost --log ../v2/evidence/run_a1wording_n16r42_seed42/run.jsonl \
  --require-provider openai_compat     # 本机实测 ok=true，2389/2389 openai_compat，degraded=0
sha256sum v2/evidence/run_a1wording_n16r42_seed42/run.jsonl
```

**已实测结果**：`OK seals 34 covers 0..33`；`provider_guard.ok=true`（2389/2389 `openai_compat`，`degraded=0`）；按 purpose：`dialogue 284 次`、`judge 435 次（全 thinking）`、`importance 1523 次`、`reflect 112`、`plan 16`、`negotiation 19`。

**`--resume-from` 语义（一句话）**：它把前缀**截断到最后一个 `TURN_SEAL`**，再从那里**续写**同一个文件
（**不是 append 拼接**）；因此同一 `out` 路径被三段复用不会产生重复 `round`。

## 5. 准入结论（D5 口径）

- **`REJECTED / probe`**：窗口 34 轮、无 `meta.json` ⇒ **不进证据级对照表**；
- 允许用途：**同窗口（34 轮）probe 级对照**、原文抽查、交叉验证；
- **A1 完整 42 轮不再补跑**（Leader 裁决 2026-10-22）：结论形态已定（形式改善、代价方向为负），补跑只补尾巴、不改结论。

## 6. 相关 SHA（引用时请一并给出）

| 文件 | 说明 |
|---|---|
| `v2/evidence/run_a1wording_n16r42_seed42/run.jsonl` | 本臂日志（34 轮，51,426 行）；sha256 见 `sha256sum` 输出 |
| 对照 | **A0 前缀 `round 0..33`**（由 `v2/evidence/run_d2_after_n16_seed42/run.jsonl`，sha8 `643f13a5`，按 `round<=33` 过滤后重算，非估算） |
| 代码 | `a637371`（+ 上述 override） |
