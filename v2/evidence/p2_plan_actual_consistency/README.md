# P2 证据件：「计划同伴 vs 实际同处」一致率 + 缺口档（只读）

> **证据状态**：`描述性读数（无判据编号）`
> **产生方式**：只读既有 `run.jsonl`，**零跑批、零 LLM 调用、零冻结区修改**。
> **取数时刻**：2026-10-24（本轮 CYCLE-17 前置读数）｜**绑定 commit**：`26ecb4fcf9b85612a5a2298ae4dbd45d43aa908f`（`26ecb4f`，master）
> **本目录不含任何截图**；本轮不出图（页面截图链由 `report-writer` 的 `v2/evidence/cycle17_shots/` 承担）。

## 1. 件清单与三重标注

| 件 | sha256 | 说明 |
|---|---|---|
| 主批日志 `v2/evidence/run_f3_off_n16r60_seed42/run.jsonl` | `19d5cb03de2f0203e3b8aa1c9160adfbef787a159f961713f40b88027931d305` | **图源批次（主批）**；116,336 行 / 52,232,012 B；`meta.json.run_sha256` 与本值相等（自洽） |
| 主批 `meta.json` | 见仓内原件 | `code_sha = 6b7ae8a98694dd87d2ea26d14e663705eab69e92`（`code_sha_end` 相同 ⇒ 跑批期间代码未变）；`events = 116336`；`seed = 42`；`rounds = 60`；`n = 16`；`model = DeepSeek-Flash` / `provider = openai_compat`；`degraded_calls = 0`；`mock_precalib_msg_count = 0`；`duration_sec = 2415` |
| 副批日志 `v2/evidence/run_f4_on_n16r60_seed42/run.jsonl` | `faeba580cfc5ae00d43a168ad5c8da67532e3825b0885aa13da78737fb4bf93a` | **副批**；116,277 行；`meta.code_sha = 6b7ae8a98694…`（与主批同）、`seed = 42`、`rounds = 60`；**臂不同**（见 §4） |
| 读数 JSON `p2_plan_actual_consistency.json` | `6cb345b339cddb557a01de82ff42a2526f36f6254dfcc9ce823dd286d1fbbc85` | 本目录内的确定性输出 |
| 出数器 `tools/p2/plan_actual_consistency.py` | `2b8a5631c4615b41c315fe8bc7e1d8d08462ce998044d45833d2e5068f49d96a` | 新建（`tools/p2/`），不改既有脚本语义 |

**开关真值口径（诚实边界）**：两批进程均已结束，`/proc/<pid>/environ` 式的开关真值**不可再取**。
本文件对「主批 = F-3 情绪呼应 OFF 臂」「副批 = F-4 对话修复 ON 臂」的判定依据是
①目录命名（`run_f3_off_…` / `run_f4_on_…`）、②主批 `meta.json.git_dirty_code_files` 含
`M code/life/agent.py` + `?? code/life/emotion_echo.py` + `?? code/config/emotion_echo.json`
（F-3 臂改动的痕迹）。**这属于间接证据，不是进程环境真值**。

## 2. 口径（先写死，再出数）

- **计划同伴对实例**：一条 `ACTIVITY_STARTED` 行 `(agent A, day, slot)` 的 `payload.participants`
  里除 A 自身之外的每个 B，构成一个有向对实例 `(A→B)`。双方互列则计 2 个实例（另给去重无向口径）。
- **实际所在**：同一 `(agent, day, slot)` 格的 `ACTIVITY_STARTED.payload.place`。这是日志里唯一全覆盖的落点字段
  （16×5×4 = 320 格 ↔ 320 行，无缺口）；`PLACE_ARRIVED.place` 仅覆盖发生位移的 299 格，只用于交叉校验。
- **时间对齐**：以 `(day, slot)` 对齐，**不以 round 对齐**。`ACTIVITY_STARTED` 本身挂在 slot 上；
  槽内位移只发生在槽首，round 级对齐不增加信息量。
- **一致**：`place(B, day, slot) == place(A, day, slot)`。一致 = 空间共处，**不等于**两人互动过（互动另由 `msg_lens` 报）。
- **分母**：可判定的计划对端**有向对实例数**（不是 agent 数、不是 slot 数）。本批不可判定 0 个。
- **排除事件**：`MSG_DM`/`MSG_PUBLIC`（只进 `msg_lens` 辅助段）、`GROUP_CREATED`（只进第 5 项对账）、
  `RELATION_ENCOUNTER`、`OBSERVATION`（非本人落点）。
- **缺口互斥主类**（命中即停）：`peer_at_residence` → `peer_planner_gate_skip_fallback`
  （B 同槽无 `template` 且复刻 `planner.py:102-104` 1/3 门判为跳过）→ `peer_planned_elsewhere_with_own_group`
  （B 自己列为 ≥2 人活动）→ `peer_planned_elsewhere_solo`（B 自己 ≤1 人）。

## 3. 能证明什么 / 不能证明什么

### 能证明什么

1. 在**主批**这份日志上，「某个 agent 计划里的同伴，在同一 `(day,slot)` 是否也把落点记成同一地点」
   的可判定对实例是 **218**，其中一致 **74**（`74/218 = 33.94%`），去重无向口径 `67/210 = 31.90%`。
2. 缺口 **144** 个可按事件流事实**互斥归因**：门跳过兜底 **61**（42.36%）、对端另组 **50**（34.72%）、
   对端独自在别处 **33**（22.92%）、对端在家 `residence` **0**；**无法归因 0 条**（主类层面）。
3. **双向互列**的对实例只有 **16** 个（占 218 的 7.3%），其中一致 **14**（`14/16 = 87.5%`）；
   单方列名的 202 个实例一致 **60**（`60/202 = 29.70%`），明显低于双向的 87.5% ⇒ 「计划同伴」在本批中**绝大多数是单方名单**，且单方名单的兑现率显著更低。
4. `GROUP_CREATED` 共 17 条、**每一条的成员集合都恰好对应 1 条**（不是 8 条）`ACTIVITY_STARTED` 行
   （`groups_with_exactly_one_matching_activity_row = 17`）⇒ CYCLE-16 §3.2 P2 的「17 vs 17」是
   **计数口径差异 + 字段语义差异，不是真实矛盾**。
5. 两批的 `ACTIVITY_STARTED` 规划流（`agent/day/slot/place/participants/template`）指纹**完全相同**
   （`43cf39e047ea706e62f683e0276fe08a92b3ea323d5f8411a9dc00840d106136`）⇒ 规划层在该臂对上**逐字段确定**。

### 不能证明什么

1. **不能**说明「计划同伴不一致」导致对话变差或生活气息变弱——本轮**无判据编号、无闸线**，
   不得写因果判断词，也不得把 33.94% 与任何历史百分比相比。
2. **不能**把「一致」读成「互动」：一致的 67 个无向对里只有 **36** 个（53.7%）在同槽出现过对话连接，
   但「同处未说话」也**不等于**关系冷淡（可能是槽内时机错开，本口径不可见）。
3. **不能**把缺口归因为「对端故意不去」：日志能证明的只是「对端自己这一格记录了别的落点」与「是否门跳过」，
   **动机层不可归因**。
4. **不能**用 `meta.json: assertions.participants_consistent=true` / `participants_violations=0`
   来支持本读数：那是「参加者集合内部自洽」的日志断言，与「计划同伴 = 实际同处」的**不是一回事**。
5. **不能**把副批当作独立复现：两批规划流逐字段相同（见上 §3-5），副批只是「同一份计划重跑尺子」，
   因此 `same_magnitude_as_primary = true` 的强度是「尺子确定性一致」，**不是「跨计划稳定」**。
6. **不能**做跨批横向比较：副批是 F-4 ON 臂，不是同臂重跑（`N-4` 挂账口径）。

## 4. 复算命令（可原地重放，零 LLM、零跑批）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
# 1) 核日志身份（期望与 §1 两个 sha 相同）
sha256sum v2/evidence/run_f3_off_n16r60_seed42/run.jsonl \
          v2/evidence/run_f4_on_n16r60_seed42/run.jsonl
# 2) 重放读数（期望 stdout: primary consistency 74/218 = 0.3394 | gaps 144）
python3 tools/p2/plan_actual_consistency.py \
    --run v2/evidence/run_f3_off_n16r60_seed42/run.jsonl \
    --secondary-run v2/evidence/run_f4_on_n16r60_seed42/run.jsonl \
    --out /tmp/p2_replay.json --stable
# 3) 字节一致性（期望两行 sha256 相同：6cb345b339cddb557a01de82ff42a2526f36f6254dfcc9ce823dd286d1fbbc85）
sha256sum v2/evidence/p2_plan_actual_consistency/p2_plan_actual_consistency.json /tmp/p2_replay.json
```

实测：两跑 sha 相同，**字节级可重放**。

## 5. 已知边界

- `run.jsonl` 受 `.gitignore:8`（`**/*.jsonl`）排除 ⇒ **不在 git 对象里**（`Q-17`）：可验 sha、可按命令复算，
  **不可从零重建**。
- 本读数只对「这 320 个 agent-槽格」成立（n16 × 5 天 × 4 槽 = 1 个模拟周），不外推到更大规模。
- 夜槽（`night`）可判定对实例为 **0**（80 行全部单人 `rest/residence`），因此读数完全由白天三槽承载。
