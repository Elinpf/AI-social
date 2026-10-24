# D2.3 mock 验收（place 亲和的对端选择）——**5 项 + 1 个必须先解决的阻断项**

- 分支 `feat/d23-place-affinity`（worktree，基于 master `ac82a21`），实现 commit `80d2975`
- 预登记：`v2/refs/D23-prereg-place-affinity.md`（`ac82a21`）
- 时间：2026-10-24 08:xx (+08:00)
- **未跑任何真 LLM 批**（本卡不含跑批）；下面全部为 mock / 离线重放

## 0. 改动（严格 3 处 + 1 开关；`git diff --stat master` 只有 3 个文件）

| 文件 | 改动 |
|---|---|
| `code/life/planner.py` | 新增 `place_affinity_weight(count, alpha)`（纯函数）、`_weighted_pick(seed, options, weights)`（累积权重轴）；`Planner.__init__` 增 `place_peer_counts=None` / `place_affinity_alpha=3`；`_participants(tid, slot_id, place=None)`（`place is None` ⇒ 原 `_pick` 路径）；`plan_slot` 内先按同一式 `_pick(f"{agent}|{slot_id}|place", sorted(places))` 算 place 再传进去 |
| `code/life/agent.py` | 开关 `HITT_PARTNER_PLACE_AFFINITY`（缺省/`0`=关，`1`=开，其它抛 `ValueError`）；`_place_peer_counts(wv)` 只读快照；`_weekly_slots` 构造 `Planner` 时仅在开关开时传快照 |
| `code/life/tests/test_d23_place_affinity.py` | 10 例单测 |

## 1. A 复现自检 = **100%** ✅
`tools/d21/d22_place_feasibility.py`（复现式 `{agent}|day{round//12}-{SLOTS[(round%12)//3]}|{tid}|p0`）：
- **mock OFF 日志**（`/tmp/d23_off`，n=16×24，seed 42）：`n_init=45`，`self_check_orig_matches_actual_rate = **100.0%**`
- **T1-OFF 真日志**（`v2/evidence/run_d12c_off_n16r60_seed42`）：`n_init=114`，同样 **100.0%**
- 原始：`v2/evidence/d23_a_repro_mock.json`（sha256 见 §7）

## 2. place 直方图逐项相等 ✅（但**注意**：这次相等是"平凡相等"，见 §6 阻断项）
mock ON vs OFF（同 seed/同参数，均 n=16×24、events 均 33,556）：

| place | OFF | ON |
|---|---|---|
| bank / cafe / clinic / community_center / farm / kitchen | 7 / 30 / 2 / 11 / 8 / 1 | **逐项相同** |
| library / market / office / park / plaza / residence | 1 / 21 / 2 / 17 / 18 / 29 | **逐项相同** |
| school / town_hall / workshop / `None` | 4 / 2 / 8 / 29 | **逐项相同** |

⇒ **16 个 place 值（含 `None`）全部逐项相等**；且 `n_msgs`、`n_threads`、`n_init` 也相同。
**这不是"我们做对了"的正面证据**——它同时是"机制在 60 轮规模下根本没触发"的旁证（§6）。

## 3. 原路径逐字节不变 ✅（**并纠正一处锚点**）
- **主树 master 的 `prompt_fn_sha256` = `47623c9de7f418b003e3e2a2ffeb5647f260034bf721c094496afa55c3564f58`**
- **本分支（开关关）同值** ⇒ 逐字相同；
- ⚠ **卡里写的"D12 系列现行 T0 = `5cf08593…`"是另一棵树（D12 支线）的值**，在本分支/主树上算出的是 `47623c9d…`（master 已并入其它改动，提示词与 D12 支线不同）。**本臂的正确锚是"与 master 逐字一致"，不是 D12 的 T0**——已在证据里按前者判定。
- `_participants` 走原路径由单测钉住：`test_place_none_is_original_path`（与"原 `_pick` 实现复刻"逐项相同，含 3 个不同 slot_id），另测"即使传了 place，但 counts 为 None（关闭态）⇒ 仍走原路径"。

## 4. T1 映射自检：**59.65%（本实现口径）**；80.70% 是**另一种口径**的离线值
`tools/d23/t1_mapping_check.py`（本臂新增，纯离线重放，不改代码）：

| 口径 | 日志 | n_init | `change_rate_B_vs_C` |
|---|---|---|---|
| **本实现（加权，α=3 vs α=0）** | T1-OFF 真日志 | 114 | **59.65%** |
| 本实现（加权） | mock OFF（n16×24） | 45 | 51.11% |
| **同 place 池（离线工具的 B）** | T1-OFF 真日志 | 114 | **78.07%** ← 与 80.70% 只差 **2.63pp** |

⇒ **80.70%（±10pp）属于"同 place 池"口径**，而预登记 §2 的实现口径是**加权（`1+α·count`）**，两者不是同一个量：
池口径换池 ⇒ 选项集变了 ⇒ 换人率高；加权口径池不变、只挪落点 ⇒ 换人率天然更低。**这不是实现错**。
⇒ 按**预登记的 M1 阈值（≥20%）**：本实现 **59.65% ≫ 20%**，机制闸**通过**。
⇒ 建议把卡面/T1 锚改成"本实现口径在 T1-OFF 真日志上的实测值（59.65%）±10pp"，否则会误判。

## 5. 单测（先落盘再报）✅
```
$ python3 -m pytest life/tests/test_d23_place_affinity.py -v   → 10 passed in 0.13s
$ python3 -m pytest life/tests -q                              → 189 passed in 183.37s
```
覆盖：`place=None` 原路径（含 counts=None 时也走原路径）、`place` 无历史（count=0 ⇒ w=1）、`peers` 为空 ⇒ `None`、
α=0 与 α=3 的确定性（同 seed 同结果）、α=0 == 累积等权轴（与 `axis_pick` 同映射，200 抽样）、
α=3 在极化 counts 下 100% 偏向高频 peer（α=0 时 <20%）、开关值语义（空/`0`/`1`/非法）。

## 6. ⚠ **阻断项（跑真批前必须先解决）：60 轮 = 1 周 ⇒ 机制在计划期永不触发**

- `TIME_CONFIG`：`DAYS_PER_WEEK=7 × SLOTS_PER_DAY=4 × ROUNDS_PER_SLOT=3` ⇒ **一周 = 84 轮**；
- `plan_slot` 只在**每周一次**的计划期被调用：mock OFF 日志里 **PLAN 事件 16 条，全部发生在 `round=0`、`week=0`**；
- ⇒ 60 轮（甚至 84 轮以内）跑批**只有一次计划**，而那时该居民**还没有任何消息历史** ⇒
  `place_peer_counts = {}` ⇒ `w ≡ 1` ⇒ **ON 与 OFF 逐位相同**（§2 的"平凡相等"正是它的表现）。
- 离线 59.65%/80.70% 都是"用第 r 轮之前的历史"算的，**在本实现里历史只在计划期取一次**，所以**真跑不会出现那些换人**。

**可选处置（请裁决，我不擅自改设计/改规模）**：
1. **改规模到 ≥85 轮**（≥2 周，第二次计划时才有 week-0 历史）——成本 ×1.4，且与所有 60 轮历史对照不可直接比；
2. **改取历史时点**（如按 slot 刷新计划 / 周中重算对端）——这是**设计变更**，会动"单变量"论证；
3. **承认本臂在 60 轮下为 no-op，不跑**。

## 7. 文件与 sha256

| 文件 | sha256（前 16） |
|---|---|
| `v2/evidence/d23_a_repro_mock.json` | `82fc03eec4238680…` |
| `v2/evidence/d23_t1_mapping_mock.json` | `f61a28ca125ff0f6…` |
| `v2/evidence/d23_t1_mapping_t1off.json` | `df3058406007694e…` |
| `v2/evidence/d23_mock_off_meta.json` / `d23_mock_on_meta.json` | `7271a42900b5ed4e…` / `bfa80f0058bd498b…` |

mock 命令（可复跑，均 mock、不调真模型）：
```bash
bash tools/d2/run_batch.sh --mock --out-dir /tmp/d23_off --seed 42 --agents 16 --rounds 24 --side-root /tmp/d23_off_side
HITT_PARTNER_PLACE_AFFINITY=1 bash tools/d2/run_batch.sh --mock --out-dir /tmp/d23_on --seed 42 --agents 16 --rounds 24 --side-root /tmp/d23_on_side
python3 tools/d21/d22_place_feasibility.py --log /tmp/d23_off/run.jsonl
python3 tools/d23/t1_mapping_check.py --log v2/evidence/run_d12c_off_n16r60_seed42/run.jsonl
```

## 8. 附：D2.5a 的 override 接线速查（顺手做，不调模型）
- **参数是活的**：`LC.set_override({"dialogue": {"max_messages_per_slot": 3}})` ⇒ `DT.load_params()["dialogue"]["max_messages_per_slot"] == 3`；`clear_override()` ⇒ 回到 **2**（默认）。
  ⚠ 注意 API 形状：`set_override` 收的是 **`life_v2` 段内容**（`{"dialogue": {...}}`），**不是** `{"life_v2": {...}}`（后者会被 `override_for` 原样返回但键名不符 ⇒ **静默无效**，我实测确认过）。
- **当前的两个缺口（D2.5a 起跑前必须补）**：
  1. `python3 -m orchestration run` **没有 `--override` 参数**（只有 `tools/t271/run_override.py` 这条包装路径支持），`tools/d2/run_batch.sh` 也不透传；
  2. `emit_run_meta.py` **不记录 override / 生效参数**，`WORLD_INIT.config_components` 只有**文件 sha**（`life_v2.json = sha256:ff230d69…`）⇒ **meta.json 里读不到 `max_messages_per_slot=3`**，正是你列的"override 静默失败"高危项。
  ⇒ 最小改法：`run` 加 `--override` 透传到 `life.config.set_override`；`emit_run_meta` 增 `--override` 记录 + **运行时读回** `DT.load_params()["dialogue"]` 落到 `meta.life_v2_effective`（不动 config 文件 ⇒ 指纹不变）。
