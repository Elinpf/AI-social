# D9m 判定基线裁定：H0 格应填 `ON_CONST`，不是 `OFF`

> 性质：**只读核算 + 判据裁定**（零跑批、零改动）。作者：Leader。
> 触发：两臂已齐（`d9m-ab-on` / `d9m-ab-off` 各 191 MSG），在出正式判定前，必须先钉死"跟谁比"。
> 若不先钉死，`OFF` 会被当成"没改善的基线"，从而把 `(d)(b2′)(e)` 的**全部不可判**误读成**通过**。

## 1. 事实（同一仪器 `tools/d9n/narration_family.py`，同词表 `01e55338…`，只换 `--log`）

| 臂 | run.jsonl | msgs | blocks | 密度 | max_v | dupMax | max_k | b2′违例族 | (a) | (d) | (e) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `OFF`（`LIFE_PROMPT_NARRATION=0`） | `d9m-ab-off_n16r24_s42` | 191 | **0** | 0.000 | — | 0 | 0 | 0 | 不可判 | 不可判 | 不可判 |
| `ON_CONST`（D9i，示例=2 句常量） | `narr-on-20261030` | 191 | 205 | 1.073 | **31（蹭）** | 3 | 2 | **7** | 失败 | 失败 | 成立 |
| `A_ONLY_ROT`（D9n，示例=9 句轮换） | `d9n-rot-20261030` | 191 | 202 | 1.058 | **24（蹭）** | 3 | 3 | 7 | 失败 | 失败 | 失败 |
| **`A+B`（D9m，本次）** | `d9m-ab-on_n16r24_s42` | 191 | 196 | 1.026 | **12（蹭）** | **2** | **2** | **4** | **成立** | 失败 | **成立** |

**开关自证**（`d9m-ab-off_n16r24_s42/switch_proof.txt`，取自 `/proc/<pid>/environ` 真值，非 `echo`）：
```
bash pid=2754932      LIFE_PROMPT_NARRATION=0  LIFE_PROMPT_NARRATION_ROTATION=1  LIFE_PROMPT_NARRATION_ACTION=1
python child pid=2755032 同上 + HITT_LLM_PROVIDER=openai_compat
```
⇒ `OFF` 的 `blocks=0` **是开关生效的结果**，不是数据缺失。两臂同参（n16r24、seed42、真 LLM `openai_compat`）。

## 2. 裁定：`OFF` 不能作 `(d)(b2′)(e)` 的基线（根 2 · H0 格失守）

三条判据的分子都是"**旁白片段**"的统计量：

| 判据 | 定义 | `OFF` 取值 | 该取值对变量有效/无效有区分力吗 |
|---|---|---|---|
| `(d)` | `max_v ≤ 5`（单动词最高） | **无片段 ⇒ 无定义** | **无** |
| `(b2′)` | 每族 `total ≤ 3` 且 `n_ge2 ≤ 1` | **无片段 ⇒ 无定义** | **无** |
| `(e)` | `max_k ≤ 2`（单条 MSG 片段数） | **无片段 ⇒ 无定义** | **无** |

⇒ `OFF` 是一个**按构造取端的臂**（`NARRATION=0` ⇒ 旁白率恒 0）。**用端值臂作基线，等于用"没有这个通道"去证明"这个通道变好了"**。这与今天上午已入库的 `two-arms-not-same-config-narration-ban.md` 是同一族错误（拿不同配置臂当同变量对照）。

**裁定（三条，须写进 D9m 判定件）**：

1. **`(d)(b2′)(e)` 的 H0 基线 = `ON_CONST`（D9i 常量 2 句臂）**，取值为 `max_v=31 / b2′违例族=7 / max_k=2`。理由：它在"旁白开启、示例未改"的条件下测，正是"若 A/B 无效"时应当看到的取值。
2. **`OFF` 只承担一件事**：证明 `LIFE_PROMPT_NARRATION=0` 下旁白为 0（本轮 `0/191` 成立）。**不得**用 `OFF` 计算任何 `(d)(b2′)(e)` 的差值、改善幅度或通过与否。
3. **`(a)` 精确串 ≤2 同理**：`OFF` 的 `dupMax=0` 是"无片段"，不是"无重复"。

## 3. 当前相对 H0 的三条读数（描述性，非最终判定）

| 判据 | H0（`ON_CONST`） | `A_ONLY_ROT` | **`A+B`** | 现状 |
|---|---|---|---|---|
| `(d)` max_v ≤ 5 | 31 | 24（−22.6%） | **12（−61.3%）** | **三步均失败**（12 仍为阈值 2.4 倍） |
| `(b2′)` 违例族 ≤ 1 | 7 | 7（0） | **4（−42.9%）** | **三步均失败**（4 仍 > 1） |
| `(e)` max_k ≤ 2 | **2（成立）** | 3（**失败**） | **2（成立）** | **回到 H0 水平** |
| `(a)` dupMax ≤ 2 | 3（失败） | 3（失败） | **2（成立）** | **优于 H0** |

⇒ 按"三条同看"的判据（`max_v ≤ 5` ∧ `max_k ≤ 2` ∧ `b2′违例族 ≤ 1`）：
**`A+B` 满足 1/3 ⇒ 判定为「部分有效（不足以通关）」。** 不得写成「有效」，也不得写成「无效」（`max_v` 31→12 与 `b2′` 7→4 是真实下降，只是未达阈）。

## 4. 两个必须同屏声明的限定（防越证）

1. **`12` 的绝对阈值争议**：`(d) max_v ≤ 5` 是 D9j 预登记的绝对条数阈值，本件不改判据。但须同时写：**`12` 是在 191 MSG / 196 片段上测得的**，若换更大规模，绝对条数会随暴露面变化（R-1/R-6）。**因此"距阈值 2.4 倍"只在同规模下可比**，跨规模必须改用率（每 100 MSG 的 `蹭` = 6.28）。
2. **这条线仍未触及根因**：`A+B` 把"过渡动作"压下去了，但 `b2′ 违例族 = 4` 且 `max_v = 12` 说明**同族动作仍在被反复使用**。按 D9k 的纵横诊断：**横向（模板同构）已由 B 削弱，纵向（角色内固化）未动**——下一步必须走**人设层**（把"某人习惯性做某动作"写进角色档案），而不是继续加提示词禁令。

## 5. 复算命令

```bash
for p in "OFF:.worktrees/narration-action-diversity/runs/d9m-ab-off_n16r24_s42/run.jsonl" \
         "ON_CONST:v2/evidence/narr-on-20261030/run.jsonl" \
         "A_ONLY_ROT:v2/evidence/d9n-rot-20261030/run.jsonl" \
         "AB:.worktrees/narration-action-diversity/runs/d9m-ab-on_n16r24_s42/run.jsonl"; do
  n=${p%%:*}; f=${p#*:}
  python3 tools/d9n/narration_family.py --log "$f" --out /tmp/f_$n.json --arm "$n"
done
```
仪器 `tools/d9n/narration_family.py` sha256 `3dbca76f1f387cd7df6bd1810cb1a0dcd1e347fb17c26d9f23ea9654628ee636`；
词表 `tools/d9n/narration_family_lexicon.json` sha256 `01e5533870f0f6b43300e6be6422130d958a01497a90d610620916f454489ed0`。
臂 run.jsonl sha256：`OFF` 见 `d9m-ab-off_n16r24_s42/` 落盘时补；`ON_CONST` `fdb31c7e2ca64b4dac1466fd4c81770dc0198ced4904584a3faf59939fd663ee`；`A_ONLY_ROT` `e4fd6db7f863fe2f6bcf6e06753600783ce57505b48a10d5c97247bf5866ece1`。
