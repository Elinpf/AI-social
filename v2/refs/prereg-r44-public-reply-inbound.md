# 预登记卡 · R44 · 公开面接话（public reply）—— 尺子修正 + 开场白/接话配额分桶

> 填写人：`dimension-dev`（本轮唯一实现方）
> 用途：把 C-1「公开面接话」从「读数被尺子缺陷掩盖 + 接话被开场白配额吃掉」推到「有可复算读数 + 可复算的机制级变色」。
> **本卡在任何批次起跑之前写死并落盘；跑完不得回改口径与阈值。** 若阈值未达成，照实写「未成立」。

| 项 | 值 |
|---|---|
| 预登记完成时间戳 | **2026-11-01T08:05:46+08:00**（`date -Iseconds` 实测） |
| 分支 | `feat/r44-public-reply-inbound`（自 `8854264` 创建） |
| base sha | `8854264ebac5bf5675cac7d6f26109490de1911a` |
| 对照（基线）批 | `v2/evidence/d47-ruler-f2-20261101_n16r24_s42`（`code_sha=8f42eee…`，`HITT_DIALOGUE_PUBLIC_REPLY=1`，seed42 / n16 / r24 / flush2） |
| 本轮试验批 | 同参数单臂 ON：seed42 / agents16 / rounds24 / flush_every 2，`HITT_DIALOGUE_PUBLIC_REPLY=1` |
| 臂（唯一差异） | 相对基线批：**只有本轮 commit 的代码改动**（尺子新增字段 + 配额分桶）；env 与规模不变 |
| 本轮禁改区 | 跑批期间 `code/{life,orchestration,config,engine}` 零改动（`tools/d5/check_clean_tree.py` 独立复核） |

---

## 0. 为什么必须先补这张卡

`reports/CYCLE-46` F-3 已判：`R41V-C4`（冻结版：逐 `place×slot` 公开消息总条数 ≤ 2，**无 day 维度**）在修后静态回放**仍判不成立**，且该口径**不得私改**。
本卡**不回溯解释也不推翻** `R41V-C4` 的历史裁决（它仍是不成立）；本卡只是**为 R44 这一个新的单变量改动**重新登记口径，并显式声明它**替代** R41V-C4 作为本维度后续判据的计数方式，理由见 §2。

---

## 1. 口径版本（写死）

| 版本串 | 位置 | 含义 |
|---|---|---|
| `public-talk-deg/2` | `tools/public_talk/public_talk_metrics.py::msg_graph_degree` | 新增 `pub_in_degree_total_any`：**任一**消息事件（`MSG_DM` / `MSG_PUBLIC` / `MSG_GROUP`）的 `reply_to` 命中某条 `MSG_PUBLIC` 的 `msg_uid` 的边数。旧字段 `pub_in_degree_total`（**只数 DM 边**）保留不改语义，降级为 `*_dm_only` 口径的兼容字段 |
| `r44/1` | `life/public_talk.py::GATE_VERSION` | 场所配额拆成两个独立桶：`opener`（开场白）与 `reply`（线程内接话），各有自己的上限 |

**分类函数（唯一实现 `life/public_talk.py::kind_of`）**：`payload.reply_to` 非空 **或** `payload.turn_index > 0` ⇒ `reply`；否则 ⇒ `opener`。

---

## 2. 缺陷陈述（可复算，先于改动）

在**基线批 d47**（`run.jsonl`，sha `5d1a3f72…`）上复算（命令见 §5）：

| 事实 | 读数 |
|---|---|
| `MSG_PUBLIC` 总条数 | 17 |
| 其中开场白（`turn_index=0` 且 `reply_to=null`） | 13 |
| 其中线程内接话（`reply_to` 指向公开消息的 `msg_uid`） | 4 |
| 旧尺子 `pub_in_degree_total`（只数 DM 边） | **0** |
| 真入度（任一消息 `reply_to` 命中 PUB `msg_uid`） | **4** |
| `place×day×slot` 细胞中「开场白 = 2」（开场白配额已满）的细胞数 | **4**（`bank/d0/afternoon`、`library/d0/morning`、`bank/d1/afternoon`、`office/d1/morning`） |
| 上述细胞中「仍有接话」的细胞数 | **0** |
| 该批 `DROPPED{quota_place}` 条数 | **13** |

⇒ 两个**并列**缺陷（缺一不可，不许只提一个）：
- **D-1（尺子）**：`pub_in_degree_total` 只统计 DM 边，把「公开面被公开面接住」这一类边**整体漏掉** ⇒ 0 是尺子缺陷，不是行为事实。这与 CYCLE-47 修的 F-2（`reply_to` 装 `msg_uid`）同类，但 F-2 只修了 `real_message_id`，没修入度。
- **D-2（机制）**：场所配额的唯一判定函数把**开场白与接话放在同一个桶里数**（`place_slot_count` 不分类）。一个 `place×day×slot` 里两人各说一句开场白（=2）之后，**第三句（恰好是接话）被确定性丢弃** ⇒ 「两个人当着面你一句我一句」在结构上被配额掐断。`life/public_talk.py` 原文注释写该配额的目的是「防止 16 个 agent 同处一地时瞬间刷屏」——防的是**开场白刷屏**，接话不是刷屏。

---

## 3. 本轮改动（单变量，最小可回滚）

1. `tools/public_talk/public_talk_metrics.py`：新增 `pub_in_degree_total_any` / `pub_in_degree_by_channel` / `pub_replied_uid_count` / `pub_in_degree_zero_any` / `isolated_nodes_any`（**只追加**，旧字段语义不变）。
2. `code/life/public_talk.py`：`MAX_PER_PLACE_PER_SLOT = 2`（**开场白**上限，数值不变）+ 新增 `MAX_PLACE_REPLIES_PER_SLOT = 2`（**接话**上限，独立桶）；`kind_of()` / `place_slot_count(..., kind=)` / `place_quota_gate(..., kind=)` / `place_quota_ok(..., kind=)`；`GATE_VERSION = "r44/1"`。
3. `code/orchestration/integration.py`：写入口 `_do_social()` 的 `scope=="global"` 分支按 `PT.kind_of(p)` 传入 `kind`，`DROPPED{quota_place}` 增加 `kind` 字段。
4. 单测：`code/life/tests/test_r41_public_talk.py` 增补分类与分桶用例；OFF 等价性用例**不得改动断言**（仍须绿）。

**不改**：`MAX_PER_AGENT_PER_SLOT=1`、`is_replyable_public` 的四条有界条件、`reply_window_rounds`、`max_messages_per_slot`、任何提示词字面量。

---

## 4. 判据（阈值写死；分母不足则只报事件数）

统计单位：`MSG_PUBLIC` 事件条数（1 条 = 1 行 jsonl = 1 次公开发言）。分母纪律沿用仓库：分母 < 30 **只报事件数、不报比率**；< 68 一律 `probe=true`。

| 编号 | 名称 | 取法 | 阈值 | 基线值 |
|---|---|---|---|---|
| **R44-C0** | 尺子缺陷可复算（同一日志） | 对 d47 `run.jsonl` 用新尺子复算 `pub_in_degree_total_any` | **必须 = 4**，且旧字段 `pub_in_degree_total` 仍 = 0 | 0 / 4 |
| **R44-C1a**（主判据·结构） | 配额分桶真的解开了「开场白满 ⇒ 不能接话」这一格 | 试验批中 `opener==2` 且 `reply>=1` 的 `place×day×slot` 细胞数 | **≥ 1**（基线 0） | 0 |
| **R44-C1b**（副判据·事件数） | 公开面入度条数 | 试验批 `pub_in_degree_total_any` | **≥ 5**（= 基线 4 + 1）；分母 13 开场白 < 30 ⇒ 只报事件数 | 4 |
| **R44-C2**（防刷屏护栏，必须两臂都成立） | 配额不越界 | 逐 `place×day×slot`：`opener ≤ 2` 且 `reply ≤ 2`；逐 `(agent, slot)` 接话 ≤ 1 | **必须成立**；任一越界 ⇒ 本轮改动判「引入缺陷」 | 基线 opener max 2 / reply max 1 |
| **R44-C3**（非塌陷） | 公开面不萎缩 | 试验批 `MSG_PUBLIC` 总条数；`obs llm-cost` 的 `degraded`、`provider_guard.ok` | `MSG_PUBLIC ≥ 13`；`degraded = 0`；`provider_guard.ok = true` | 17 / 0 / true |
| **R44-C4**（不可宣称声明） | 不判「生活气息提升」 | —— | 本轮**不得**出现「更自然 / 效果提升」字样；单 seed 点估计、不写显著、不给 CI | —— |

**不可判情形**（事先声明）：若试验批 `MSG_PUBLIC` 开场白数 < 8，或 `opener==2` 细胞数为 0，则 `R44-C1a` 记「不可判（分母为空）」，不得改判为通过。

---

## 5. 复算命令（写死，可直接照抄）

```bash
REPO=/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
BASE=$REPO/v2/evidence/d47-ruler-f2-20261101_n16r24_s42/run.jsonl
# C0：同一日志上新旧入度
cd $REPO/code && python3 -m obs --help >/dev/null
python3 $REPO/tools/public_talk/public_talk_metrics.py --log $BASE --out /tmp/r44_base_readings.json
python3 - <<'PY'
import json; d=json.load(open('/tmp/r44_base_readings.json'))
g=d['msg_graph_degree']
print('old_pub_in_degree_total', g['pub_in_degree_total'])
print('any_pub_in_degree_total', g['pub_in_degree_total_any'])
print('by_channel', g['pub_in_degree_by_channel'])
PY
```

细胞口径复算（`opener` / `reply` 分类 + 每细胞计数）的脚本随报告落盘：`assets/round-1/public_reply_cells.py`。

---

## 6. 起跑闸（写死）

```bash
ps -eo pid,args | grep -E 'orchestration run|run_batch\.sh|nightly\.py' | grep -v grep; echo rc=$?   # 期望 rc=1
bash tools/d5/preflight.sh --tag r44
```

任一不满足 ⇒ 不起跑，改报告为「未执行」。

---

## 7. 与既有卡的关系（不销号、不回溯）

- `R41V-C4` 仍为「不成立」，本卡不重新解释它；自本卡起，公开面配额的**计数方式**改为「开场白 ≤2 + 接话 ≤2（两个独立桶）」。
- `R41V-C1`（接话率差）仍为「不可判」，本卡不复活它；本卡只登记事件数口径的 `R44-C1b`。
- `CYCLE-46` 的 `F-2` / `F-3` / `F-4` 等未决项保持原状，本卡不代为销号。
