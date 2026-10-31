# 预登记卡 · R41V · 公开面接话（public_talk）OFF/ON 验证批

> 执行人：`batch-operator`（跑批执行与度量工程师）
> 用途：把「R41 代码在位、从未验证」推到「有可复算读数 + 可展示现场截图」。**本卡先写死口径，跑完不得回改。**
> 本卡内容在**任一批次起跑之前**完成并落盘；跑批命令、读数命令、判据阈值、不可判情形全部预先写死。

| 项 | 值 |
|---|---|
| 预登记完成时间戳（本地，`date -Iseconds`） | **2026-11-01T02:04:30+08:00**（`date -Iseconds` 实测写入，见 §6；两臂起跑 epoch 必须晚于此） |
| 分支 | `feat/life-public-talk-r41-verify`（自 `b353cfe` 创建，未 stash/reset 任何 WIP） |
| 代码身份（本卡写就时的 HEAD） | 见 §6 `head_at_prereg`（实测写入） |
| 臂（唯一差异） | env `HITT_DIALOGUE_PUBLIC_REPLY`：**OFF = 变量不存在**；**ON = 变量 = `1`** |
| 实现位置（不在本轮改动） | `code/life/public_talk.py`、`code/life/agent.py:33/1147/1307/1341/1365`、`code/orchestration/integration.py:170-190/868-878` |
| 本轮禁改区 | `code/life`、`code/orchestration`、`code/config`、`code/engine` —— **零改动**（preflight 的 `check_clean_tree.py` 会独立复核） |

---

## 0. 一句话判据

**主判据只有一个**：ON 臂里「公开消息接住另一条消息」的比例差（p_ON − p_OFF）的 95% 区间下界 > 0（OFF 结构上恒为 0）。
其余判据是护栏（OFF 等价性、有界配额、可判性解锁、非塌陷），**不判「生活气息提升」**——本轮只做机制接线验证，不做质量判断。

---

## 1. 两臂参数（写死，不得临时改）

| 参数 | 值 |
|---|---|
| `--seed` | `42` |
| `--agents` | `16` |
| `--rounds` | `24` |
| `--flush-every` | `2` |
| `--side-root` | OFF：`/tmp/r41v_off_n16r24_s42_side`；ON：`/tmp/r41v_on_n16r24_s42_side`（**唯一允许不同的第二项，且只影响旁路存储路径**） |
| 起点脚本 | `tools/d2/run_batch.sh`（仓库单一真源，内含 `tools/d5/preflight.sh` 串行闸 + `emit_run_meta.py` + `obs llm-cost` 门禁） |
| 启动方式 | 外层 `setsid`（团队纪律；`run_batch.sh` 自身不含 setsid） |
| LLM provider | `HITT_LLM_PROVIDER=openai_compat`，端点/模型来自 `code/config/llm.json`（`http://172.16.3.41:31809/v1` / `DeepSeek-Flash`） |
| 串行 | **严格串行**：OFF 臂 `run_batch.rc == 0` 之后才允许起 ON 臂 |

产物目录（写死）：

```
v2/evidence/r41v_public_talk_n16r24_s42/off
v2/evidence/r41v_public_talk_n16r24_s42/on
```

## 2. 两臂唯一差异（单变量声明）

| 项 | OFF 臂 | ON 臂 |
|---|---|---|
| `HITT_DIALOGUE_PUBLIC_REPLY` | **不存在**（`unset`） | **`=1`** |
| `HITT_WORLD_SEED` | 两臂均显式 = `42` | 同 |
| `HITT_LLM_PROVIDER` | 两臂均 = `openai_compat` | 同 |
| 其它 `LIFE_PROMPT_*` / `HITT_*` | 两臂均不设置 | 同 |

允许不同的只有：开关、`--out-dir`、`--side-root`、systemd/setsid 单元名。发起脚本会在 `env_dump.txt` / `switch_proof.txt` 里做存在性断言（OFF 必须 `NO`，ON 必须 `YES` 且值 `1`），断言失败拒绝起跑。

## 3. 判据编号、阈值、分母口径、区间方法

**统一统计单位 M实例** = 一条 `type=="MSG_PUBLIC"` 的日志事件 = 1 行 jsonl = 1 次公开发言（沿用 `tools/public_talk/public_talk_metrics.py` 已钉死口径）。
**所有分母 = 该臂的 M实例 总数**，逐臂独立取；**不做两臂合并**。

| 编号 | 名称 | 分子 / 分母 | 阈值（预先写死） | 数据来源（字段） |
|---|---|---|---|---|
| **R41V-C1**（主判据） | 公开面接话率差 | 分子 = `reply_to_forms.forms.real_message_id`（`payload.reply_to` 命中真实 `msg_uid` 的 MSG_PUBLIC 条数）；分母 = M实例 | **p_ON − p_OFF 的 Newcombe 95% 双侧区间下界 > 0**，且 `k_ON ≥ 1`；OFF 侧必须 `k_OFF = 0` | `tools/public_talk/public_talk_metrics.py` 第 3 组 |
| **R41V-C2**（OFF 等价性，结构侧） | OFF 臂孤立节点保持 | OFF：`k_OFF = 0` 且 `msg_graph_degree.pub_out_degree_zero == true` | **必须成立**（否则判 OFF 臂不干净/开关泄漏） | 同上 + `msg_graph_degree` |
| **R41V-C3**（可判性解锁） | `place` 覆盖 | ON：`place_adjacency.nonnull_place_records / M实例 == 1.0`（100%）；OFF 期望 0% | ON **100%** 成立 ⇒ `place_adjacency.status` 从 `UNVERIFIED` 变为可判；OFF 保持 `UNVERIFIED` | `place_adjacency` |
| **R41V-C4**（有界配额护栏） | 配额不越界 | 逐 place×slot 统计 MSG_PUBLIC 条数最大值 ≤ `MAX_PER_PLACE_PER_SLOT=2`；逐 (agent, slot) 接话条数最大值 ≤ `MAX_PER_AGENT_PER_SLOT=1` | 两臂**均必须** ≤ 上限（OFF 侧自然为 0 接话） | 直接读 `run.jsonl`（命令写死在 §4） |
| **R41V-C5**（非塌陷） | 公开面不萎缩 | ON 臂 `MSG_PUBLIC` 条数 ≥ OFF 臂条数 − 0（允许相等或更多）；且两臂 `LLM_CALL` 事件数均 > 0 | **成立**为佳；若 ON < OFF 需在汇总里单列原因，不得静默 | `msg_public_total.value` + `obs llm-cost` |

### 3.1 置信区间方法（唯一真源，不自造公式）

- 单臂比例 Wilson 95% 区间：`tools/metrics/d9m_wilson_ci.py`（canonical 实现 = `tools/d5/dialogue_metrics.py::wilson_ci`，`z = 1.959964`，来源 `tools/d5/f8_lexicon.json::thresholds.wilson_z_95_two_sided`）。
- 两臂比例差 Newcombe 95% 区间：`tools/metrics/weather_readings.py::newcombe95`（Newcombe 1998 method 10，基于 Wilson score）。本轮由 `tools/public_talk/compare_arms.py` **import 该函数**，不重写公式（口径不分叉）。

### 3.2 分母纪律（沿用仓库既有硬约束）

- 分母 < **30** ⇒ 只报事件数、不报比率。
- 分母 < **68** ⇒ 一律标 `probe=true`，副读数不得作判据、不得写「显著」。
  （预期本批 M实例 在 20~40 量级，故 **C1 的结论措辞限定为「区间下界 > 0 的方向性结论 + probe 标注」**，不写「显著提升」。）

## 4. 读数器与命令（写死）

| 用途 | 路径 | 命令 |
|---|---|---|
| 单臂全量尺子 | `tools/public_talk/public_talk_metrics.py` | `python3 tools/public_talk/public_talk_metrics.py --log <ARM>/run.jsonl --meta <ARM>/meta.json --out <OUT>/readings_<arm>.json` |
| 两臂对比 + CI | `tools/public_talk/compare_arms.py`（本轮新增，纯只读、零 LLM、零跑批） | `python3 tools/public_talk/compare_arms.py --off v2/evidence/r41v_public_talk_n16r24_s42/off/run.jsonl --on .../on/run.jsonl --off-meta .../off/meta.json --on-meta .../on/meta.json --out v2/evidence/r41v_public_talk_readings/compare.json` |
| 配额护栏（C4） | 直接读 `run.jsonl` 的一行 python（命令原文写进 summary） | `python3 - <<'PY' ... PY`（按 `payload.place` / `payload.slot` / `payload.author` 分组计数，纯只读） |
| 成本验真 | `code/` 下 `python3 -m obs llm-cost` | `cd code && python3 -m obs llm-cost --log ../<ARM>/run.jsonl --require-provider openai_compat`（**必须在 `code/` 下执行**） |
| 截图 | `tools/metrics/render_shots.py` | `python3 tools/metrics/render_shots.py --run-dir <ARM> --batch-id R41V-<ARM> --outdir v2/evidence/r41v_public_talk_shots --views chat,rhythm` |

读数落盘目录：`v2/evidence/r41v_public_talk_readings/`（`readings_off.json` / `readings_on.json` / `compare.json` / `quota_guard.json`）。
截图落盘目录：`v2/evidence/r41v_public_talk_shots/`，每张 png 文件名必须含**本臂 `run.jsonl` 的 sha256 前 8 位**，并记录字节数与像素尺寸。

## 5. 「不可判 / 不成立」的预先定义（**跑之前写死**）

| 情形 | 判定 |
|---|---|
| 任一臂 `run_batch.rc != 0` | **本轮失败**（如实上报），不出读数、不出截图 |
| 任一臂 `obs llm-cost --require-provider openai_compat` rc != 0 | **本轮失败**（非真跑）；**禁止**用 `--mock` 或去掉 `--require-provider` 顶替 |
| 任一臂 preflight 非 PASS，或 `meta.json` 缺失，或 `wc -l run.jsonl != meta.events` | **本轮失败** |
| `code/{life,orchestration,config,engine}` 出现任何 modified/staged/untracked | **本轮失败**（`check_clean_tree.py` 复核） |
| OFF 臂 `k_OFF != 0`（出现接话） | C2 **不成立** ⇒ 判「OFF 臂开关泄漏」，整批读数作废 |
| ON 臂 M实例 = 0 | R41V-C1 **不可判**（分母为 0，不报假区间） |
| ON 臂 M实例 < 30 | C1 只报事件数与区间，**不报比率**；结论只能写成「方向性」 |
| 两臂 provider 不同 / 含非 `openai_compat` 调用 | **不可判**（真跑门禁失败） |
| `place_adjacency` 在 ON 臂仍 `UNVERIFIED` | C3 **不成立**（place 注入未生效），但不否决 C1 |

**明确不写的结论**：不写「生活气息提升」、不写「接话质量更好」、不写「显著」；C1 成立也只能写「公开面接话通道在 ON 臂被触发，比例差区间下界 > 0（probe 级样本）」。

## 6. 时间戳与代码身份（落盘时实测填写）

本卡的完成时间与当时 HEAD 由 shell `date -Iseconds` / `git rev-parse HEAD` 实测追加在下方代码块中，**提交时间必须早于两次 `run_batch.sh` 的 `start_epoch.txt`**（起跑时间以各臂 `start_epoch.txt` 为准，由第三方核对）。

```
prereg_written_at=<见下方「实测追加」>
head_at_prereg=<见下方「实测追加」>
branch_at_prereg=feat/life-public-talk-r41-verify
```

### 实测追加（由命令写入，不手抄）

<!-- PREREG-STAMP:BEGIN -->
prereg_written_at=2026-11-01T02:04:30+08:00
prereg_written_at_utc=2026-10-31T18:04:30Z
head_at_prereg=b353cfe2343379070671c842d326a06daf97cf3a
branch_at_prereg=feat/life-public-talk-r41-verify
prereg_sha256=<自指不写死：见 `sha256sum v2/refs/prereg-r41v-public-talk-verify.md`>
note=本时间戳由 `date -Iseconds` 实测写入；两臂 `start_epoch.txt` 的 epoch 必须晚于本时间戳（第三方可核对）。
<!-- PREREG-STAMP:END -->
