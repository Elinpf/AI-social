# D9n 预登记 · 增补 05（路径与编号对照表 + 改名留痕）

> 立件：exp-designer｜时刻：2026-10-30 08:24 +08:00（**跑前**）
> 目的：Leader 2026-10-30 08:18 指示「两份增补件文件名仍是 `D9m-*` 必须 rename 为 `D9n-*`；lexicon 路径改 `tools/d9n/`」。**只增不改**：所有被改名文件**内容一个字节未动**，sha256 前后逐一相同（见下表）。
> 本件同时给 verifier 要求的「路径(D9n) ↔ 内文编号(D9m) ↔ 实际交付路径」对照表。

---

## E-1 本件生效的改名（内容未动，sha256 不变）

| 旧路径 | 新路径 | sha256（**改名前 = 改名后**） |
|---|---|---|
| `v2/refs/D9m-prereg-amendment-01.md` | `v2/refs/D9n-prereg-amendment-02-guard-thresholds.md` | `401617edc2bbb5dcb04e8291df30e8df315200bd9af676146a4108b959988095` |
| `v2/refs/D9m-prereg-amendment-02-family-lexicon.md` | `v2/refs/D9n-prereg-amendment-03-family-lexicon.md` | `fa5af47dc53f8a272dde9238b741db67a69fa9ac00537ad8bf6cb944862898cf` |
| `v2/refs/D9m-prereg-amendment1-d9j-provenance.md` | `v2/refs/D9n-prereg-amendment-04-d9j-provenance.md` | `1cc362c2be1705e8a8b424b348c13119685fd4c469caa8ee4bdd5e64e11896d5` |
| `tools/d9m/narration_family_lexicon.json` | `tools/d9n/narration_family_lexicon.json` | `9a87ebb5ee80bb8d991d2c54e1562e312810ed23f1081141e30b98b3f9933edd` |

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
| §4.8 词表身份 | `NARRATION_EXAMPLE_LEXICON_VERSION = "narration-rotation-v1"` | **不变**（常量名与版本号是代码身份，不随编号改名） |

复算命令一律用 `tools/d9n/`（E-2 表），**不要照抄主件里的旧路径**。

---

## E-4 本件不做的事

- 不改主件、不改任何被改名文件的内容（sha256 全表核对相同）。
- 不引入新判据、不改任何阈值/三态条件。
