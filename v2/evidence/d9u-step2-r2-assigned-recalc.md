# D9u 第二步 · `R2 assigned` 实测复算（D9u 主判据的唯一实测依据）

> **件头自标：设计者侧，非中性**——D9e/D9g/D9h/D9i/D9s/D9u 相关判读均出自我手。
> **只读、零跑批、不改代码**；本件不含任何 LLM 调用。
> **用途**：D9u 主判据（三份 coverage 均 ≥80%）的实测依据。供判定件引用。

## 0. 一行口径（R-12 要求同屏）

```
lexicon_sha      = c9e8924c0b0f170540deb1ef5758e8da261ffe2a44770f980262532909fad859   （v2.0，43 词）
instrument_sha   = narration_family.py  ba645ea6f0c49b350d529350fd8bc1ae065427b19a32871b6d2985855662414c
                   syntax_shape.py       ca54572380ee53824528c4c31a3e1ff45321dd345c3fd1be90e42d9e169ad1fd
分母             = 该臂**片段数**（`PAIRED_RE` 命中的括号内非空文本条数），不是 MSG 数
参照系           = 守卫门槛 threshold_abs = 19.3171%（频表自带）；主判据 = 三份均 ≥80%
```

## 1. 输入三值（实测）

| 臂 | 路径 | `sha256`（前 16） | 片段数 |
|---|---|---|---|
| `OFF_run1` | `v2/evidence/d9s-syntax-off_n16r24_s42/run.jsonl` | `ba6812a1828c3c8f` | **194** |
| `ON2` | `v2/evidence/d9s-on2_n16r24_s42/run.jsonl` | `912ee0776a5a3eee` | **174** |
| `A+B` | `v2/evidence/d9m-ab-on_n16r24_s42/run.jsonl` | `2edc751c5a32d132` | **196** |

## 2. 结果（两种口径并列）

| 臂 | 片段数 | ① 包含即算（任一 V_judge 词出现） | ② **R2 后 `assigned=True`** | 差 |
|---|---|---|---|---|
| `OFF_run1` | 194 | 156 = **80.41%** | **156 = 80.41%** | **0** |
| `ON2` | 174 | 147 = **84.48%** | **147 = 84.48%** | **0** |
| `A+B` | 196 | 166 = **84.69%** | **166 = 84.69%** | **0** |

**⇒ 三份均 ≥80% ⇒ D9u 主判据「实测达成」。**

## 3. 三行脚本（可逐字复跑）

```python
nf = ss.load_nf()                                                  # 按路径导入 narration_family
lex = nf.load_lexicon(ss.DEFAULT_LEXICON); v = nf.v_judge(lex)      # v2.0：closed8+rotation13+expansion22
parts, objs = list(lex["parts_6"]), list(lex["objs_13"])
assigned = sum(1 for s in blocks if nf.assign_family(s, v, parts, objs)["assigned"])
```
（`blocks` = 三臂 `run.jsonl` 逐 MSG 取 `nf.PAIRED_RE.findall(body)` 的括号内非空文本。）

## 4. 两条限定（必须同屏引用）

**限定一｜余量极薄**：`OFF_run1` 只高出门槛 **0.41pp = 156 − 155（1 条片段）**。
⇒ 再多拒掉 1 个覆盖该片段的词，即掉到 **79.9%**。**"实测达成"不等于"有余量"。**

**限定二｜差 0 ≠ R2 规则无效**：
差为 0 只说明**本语料里凡含已收动词的片段都能通过位置规则**（可能 `parts`/`objs` 允缺省）。
⇒ **换一批"动词在句尾 / 作名词"更多的语料，两种口径会重新分开**；**该等价性不可外推**，更不得据此论证"归族规则可简化"。

## 5. 一条自我推翻（照实记）

本人在上一轮曾预测：「真实 `assign_family` 还须过位置规则 ⇒ 实际 coverage 会更低，那 0.41pp 很可能被吃掉」。
**实测差为 0，该预测未兑现。** ⇒ 主判据口径由"宽松上界"改为"**实测达成**"。

## 6. 边界

1. 本件不含 LLM 调用、不改 `code/`、不改词表、不动 `run.jsonl`。
2. `assign_family` 的"该不该这么宽松"属**仪器定义问题**（`dialogue-core-dev`），本件不表态。
3. 本件不判"扩表是否改善了表达"——只回答"扩表后能否量到 ≥80%"。
4. 未 commit（提交权归 Leader）。
