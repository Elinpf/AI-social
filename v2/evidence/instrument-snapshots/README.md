# 仪器历史快照（只读留档，不得用于新读数）

## 为什么有这个目录

`tools/d9n/` 与 `tools/d9s/` 直到 `73cbbf2`/`0472980` 才进入 master。
此前所有读数引用的是**工作区版本**，一旦被覆盖即永久丢失（R-10 的后遗症）。

本目录保存**已被覆盖但仍有判定件引用**的版本，唯一目的：**让历史读数可复算**。

## 已留档

| 文件 | sha256 | 曾被谁引用 |
|---|---|---|
| `narration_family.py.3dbca76f-20261030` | `3dbca76f1f387cd7df6bd1810cb1a0dcd1e347fb17c26d9f23ea9654628ee636` | `d9m-*`、`d9s-*` 全部判定的归族读数（截至 2026-10-30 21:xx） |
| `narration_family_lexicon.json.01e55338-20261030` | `01e5533870f0f6b43300e6be6422130d958a01497a90d610620916f454489ed0` | 同上（**v1.1，21 词，无 `verbs_expansion_22`**） |

⇒ **两者必须成对引用**：`d9m`/`d9s` 的归族读数 = `3dbca76f`（仪器）+ `01e55338`（词表）。**只给仪器不给词表，仍不可复算。**

**⚠ 两层都只在 worktree 有副本**（`worktree` 被 prune 即永久丢失）⇒ 本目录是唯一留档。

## 当前版本（**新读数只能用这个**）

| 文件 | sha256 | 变化 |
|---|---|---|
| `tools/d9n/narration_family.py` | `ba645ea6f0c49b350d529350fd8bc1ae065427b19a32871b6d2985855662414c` | 支持 `verbs_expansion_22`（顺序：closed_8 → rotation_13 → **expansion_22 追加末尾**）+ 长度/重复校验 |
| `tools/d9n/narration_family_lexicon.json` | `c9e8924c0b0f170540deb1ef5758e8da261ffe2a44770f980262532909fad859` | v2.0，43 词 |

## 规则

1. **快照仅供复算历史读数**，不得作为新判据的输入；
2. 新旧版差异见 `narration_family.py` 第 83–96 行（`verbs_expansion_22` 读取与顺序注释）；
3. 引用快照时必须写「基于 `narration_family.py` sha `3dbca76f…`（快照）」。
