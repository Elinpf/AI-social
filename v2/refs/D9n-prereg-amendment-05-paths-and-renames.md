# D9n 预登记 · 增补 05（路径与编号对照表 + 改名留痕）

> 立件：exp-designer｜时刻：2026-10-30 08:24 +08:00（**跑前**）
> 目的：Leader 2026-10-30 08:18 指示「两份增补件文件名仍是 `D9m-*` 必须 rename 为 `D9n-*`；lexicon 路径改 `tools/d9n/`」。**只增不改**：所有被改名文件**内容一个字节未动**，sha256 前后逐一相同（见下表）。
> 本件同时给 verifier 要求的「路径(D9n) ↔ 内文编号(D9m) ↔ 实际交付路径」对照表。

---

## E-1 顺延映射（**四列一一对应，逐行可核**；内容未动，sha256 不变）

| 新编号 | 新路径 | 原文件名 | 内容 sha256（**改名前 = 改名后**） |
|---|---|---|---|
| **01** | `v2/refs/D9n-prereg-amendment-01.md` | *（新建，无原名）* | `3b055ffa518e07e61375d2f2b0c1c9259c4ec47d21f8fdd46100a4afc602bbd9` |
| **02** | `v2/refs/D9n-prereg-amendment-02-guard-thresholds.md` | `v2/refs/D9m-prereg-amendment-01.md` | `401617edc2bbb5dcb04e8291df30e8df315200bd9af676146a4108b959988095` |
| **03** | `v2/refs/D9n-prereg-amendment-03-family-lexicon.md` | `v2/refs/D9m-prereg-amendment-02-family-lexicon.md` | `fa5af47dc53f8a272dde9238b741db67a69fa9ac00537ad8bf6cb944862898cf` |
| **04** | `v2/refs/D9n-prereg-amendment-04-d9j-provenance.md` | `v2/refs/D9m-prereg-amendment1-d9j-provenance.md` | `1cc362c2be1705e8a8b424b348c13119685fd4c469caa8ee4bdd5e64e11896d5` |
| **05** | `v2/refs/D9n-prereg-amendment-05-paths-and-renames.md` | *（本件，新建）* | 见 anchor `f1e758a` 记录（本件后续有 v1.1 小改，见 §E-6） |
| —（数据） | `tools/d9n/narration_family_lexicon.json` | `tools/d9m/narration_family_lexicon.json` | v1.0 `9a87ebb5…` → **v1.1 `01e55338…`**（见 §E-5） |

> ⚠️ **单独说明（最易核错的一行）**：**04 的原文件名是 `D9m-prereg-amendment1-d9j-provenance.md`** —— 其中的 `amendment1` **没有连字符**（既不是 `amendment-1`，也不是 `amendment-01`）。这是我在 08:14 建件时的命名笔误，改名时**原样保留为历史证据**、未做「顺手修正」；核对时请用 `git log --diff-filter=R --summary 5a9b5a2` 看 `R100` 的旧名，不要凭记忆猜。

**编号映射（为何不是 01→01）**：`D9n-prereg-amendment-01.md` 已被「种子口径勘误 + 守卫来源 + 编号让位 + 判据六条」占用，故原 `D9m` 的 01/02/amendment1 顺延为 **02 / 03 / 04**，本件为 **05**。

**改名的副作用（必须知道）**：`D9n-prereg-amendment-01.md` §D-6 里写的 `tools/d9m/narration_family_lexicon.json` 路径**已过期**；路径权威以本件为准 ⇒ **`tools/d9n/narration_family_lexicon.json`**（amendment-01 内容按「只增不改」纪律不回改）。

---

## E-2 对照表（报告必须附，否则复算命令复制即错）

| 概念 | 报告里应写的路径 | 历史内文/旧称 | 说明 |
|---|---|---|---|
| 预登记主件 | `v2/refs/D9n-prereg-narration-example-rotation.md` | 曾名 `…/D9m-prereg-narration-rotation.md` | 内容 sha256 始终 `0d104502…6643`；**内文仍有 8 处写「D9m」、7 处写 `tools/d9m/`**（见 E-3） |
| 增补 01（种子/守卫/让位/六条） | `v2/refs/D9n-prereg-amendment-01.md` | 原名无（D9n 时代新建） | sha256 `3b055ffa518e07e61375d2f2b0c1c9259c4ec47d21f8fdd46100a4afc602bbd9` |
| 增补 02（守卫阈值来源 + 修恒假） | `v2/refs/D9n-prereg-amendment-02-guard-thresholds.md` | `D9m-prereg-amendment-01.md` | 见 E-1 |
| 增补 03（族词表内容 + meta 口径） | `v2/refs/D9n-prereg-amendment-03-family-lexicon.md` | `D9m-prereg-amendment-02-family-lexicon.md` | 见 E-1 |
| 增补 04（D9j 版本化勘误） | `v2/refs/D9n-prereg-amendment-04-d9j-provenance.md` | `D9m-prereg-amendment1-d9j-provenance.md` | 见 E-1 |
| 本件 | `v2/refs/D9n-prereg-amendment-05-paths-and-renames.md` | — | 路径权威 |
| **族词表（唯一权威路径）** | **`tools/d9n/narration_family_lexicon.json`** | 曾 `tools/d9m/…` | `9a87ebb5…` |
| 实现件（impl-2 交付） | `tools/d9n/narration_family.py`、`tools/d9n/narration_example_seq.py` | — | 以 impl 交付的 `impl_sha256` 为准 |
| 片段仪器（已版本化） | `tools/d9i/narration_stats.py` | — | `8ddb9111…` |
| 并行线（**不引用**） | `v2/refs/D9m-prereg-narration-action-diversity.md`（master `0938f14`） | — | A+B 双改动，非单变量；本轮裁决为 **A only**，二者不可互引 |

---

## E-3 主件内文的「D9m」残留清单（不改主件，报告按此映射）

主件按「一个字节不改」纪律**不回改**，残留与替换规则如下：

| 主件位置 | 残留文本 | 报告/复算时按此读 |
|---|---|---|
| 件头·标题与 §0/§3/§9 等 8 处 | `D9m` | 读作 **D9n** |
| §4.0 仪器表、§4.8、§11.2、§8 等 7 处 | `tools/d9m/…` | 读作 **`tools/d9n/…`** |
| **§11.1 / 附「可复算命令」8 处：`v2/refs/D9m-prereg-narration-rotation.md`**（实测报出点：`:414`，另含 §11.1 的 `sha256sum` 自检命令） | 旧**主件路径** | **该路径已随 rename 失效（文件不存在）** ⇒ 读作 `v2/refs/D9n-prereg-narration-example-rotation.md` |
| §4.8 词表身份 | `NARRATION_EXAMPLE_LEXICON_VERSION = "narration-rotation-v1"` | **不变**（常量名与版本号是代码身份，不随编号改名） |

> **「照抄即错」示例（至少两条，报告须点名）**：
> 1. 主件 `:414` 的 `sha256sum v2/refs/D9m-prereg-narration-rotation.md` —— 路径已不存在，直接复制会 `No such file`；正确命令见 §E-2 第 1 行。
> 2. 主件 §4.0/§4.8/§11.2 里 `python3 tools/d9m/narration_family.py …` —— 目录已移为 `tools/d9n/`，照抄会 `can't open file`。
>
> **失效项合计 8 类点**：1 类旧**主件路径**（含 `sha256sum` 自检）+ 7 处 `tools/d9m/`；未失效但易误读 1 类：8 处 `D9m` 编号。三者**全部靠本表消解，不回改主件**。

复算命令一律用 `tools/d9n/` 与 D9n 新路径（见 §E-2），**不要照抄主件里的旧路径**。

---

## E-5 族词表 v1.1 勘误（跑前，2026-10-30 08:28）

**问题（我自己发现的）**：lexicon v1.0 的 `baseline_reference.coverage` 写成 `40/205 = 0.19512`，那是**只算闭表 8 动词、且把「指头」折进「手」**的旧口径；而本词汇表 `V_judge` 实为 **21 动词**。实测（`tools/d9n/narration_family.py` 在历史 ON 日志上跑）为 **66/205 = 32.195%**。⇒ 两条守卫的锚与门限一并错。

| 项 | v1.0（错） | **v1.1（更正，已冻结）** |
|---|---|---|
| `coverage` 基线 | 40/205 = 0.19512 | **66/205 = 0.321951** |
| `unassigned_verb_rate` 基线 | 0.80488 | **0.678049** |
| `coverage` 门限（规则不变：≥60%×基线） | 0.11707（≥24 片段） | **0.193171（≥40 片段）** |
| `unassigned` 门限（规则不变：≤基线+10pp） | 0.90488 | **0.778049** |
| sha256 | `9a87ebb5…` | **`01e5533870f0f6b43300e6be6422130d958a01497a90d610620916f454489ed0`** |

**只改了锚与门限，没改尺子**：21 个动词、`parts_6`、`objs_13`、顺序、规则 R1–R8 **一字未动**（`family_spot_checks` 里的 `蹭|手 8`、`蹭|锉刀 9` 等逐项不变，已用工具复现）。
**方向是收紧不是放宽**：`coverage` 门限 11.707% → **19.317%**（更严），`unassigned` 门限 90.488% → **77.805%**（更严）。规则（60% / +10pp）本身**未动**，只是锚错了。

---

## E-6 本件自身的修订记录

- **v1.0 → v1.1（2026-10-30 08:2x，跑前）**：按 Leader 指示把 §E-1 改成**四列一一对应表**（新编号 / 新路径 / 原文件名 / 内容 sha256）+ 加「`amendment1` 无连字符」单独说明行；§E-3 补上旧**主件路径**失效项（8 类点全覆盖）；新增 §E-5（lexicon v1.1 勘误）。**判据、阈值规则、三态条件一律未改。**
- 本件 sha256 由 `5c465b0e83acc5766a6cb63ac2a45031095fa66dfb468c823ccb3a2f108252d9`（v1.0）变为 v1.1 新值，两值均已进 `D9n-prereg-commit-anchor.txt`。

---

## E-7 本件不做的事

- 不改主件、不改任何被改名文件的内容（sha256 全表核对相同）。
- 不引入新判据、不改任何阈值/三态条件。
