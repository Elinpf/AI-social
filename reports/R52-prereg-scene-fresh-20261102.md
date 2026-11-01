# R52 维度预登记卡：处境锚「取值时点」修复（B-8）· 两臂对照

- 卡片 ID：`R52-scene-fresh-prereg-20261102`
- 冻结时刻：**2026-11-02 00:2x +08:00**（本文件 commit 时间必须早于 `start_epoch.txt`，对账命令见 §9）
- 状态：**判据先于数据** —— 本卡在任何一臂 `run.jsonl` 落盘之前冻结；跑批启动后**不得修改本卡任何数字**
- 维度：C1 处境锚的**机制根因**（B-8：锚点取「本轮移动前」快照），不是新维度、不新开第二个生活气息维度
- 前置依据：`team-workspace/R52/state.md §3.3 推荐 1`、`docs/team-board.md:36/:68`、`v2/evidence/r46-c1-effect-metrics/metrics-table.md §2b`
- 尺子（本轮冻结）：
  - 机制层 + 效果层两臂对照：`tools/metrics/scene_fresh_rate.py`（`ruler_version = r52-scene-fresh-v1`）
  - 效果层词表：**直接 import** 既有冻结尺子 `tools/metrics/place_content_consistency.py`，
    `lexicon_sha256 = 7e514eba9f9de0e674875f40b9503e24490f5baf9b861d51bc8cfe68b074f22e`（改词表 ⇒ 本卡作废）
  - 提示词指纹探针：`tools/r52/prompt_hash_probe.py`（零 LLM，函数目录上证明 OFF 逐字节等价）

---

## 1. 缺陷事实（跑批前已定，逐条带证据）

| # | 事实 | 证据 |
|---|---|---|
| F1 | `ctx.scene.place` 取自 `WorldView.location`，即**本轮 perceive 阶段**的快照；消息落盘的 `payload.place` 取自 `orchestration/integration.py::_do_social` 的 `st.agents[id]["location"]`（COMMUNICATE 阶段实时值） | `code/life/agent.py::_scene_line`（当前树 `:1649` 起）、`code/orchestration/integration.py:888` |
| F2 | 两值在同一轮内该居民搬过地方时不一致：R46-A1 实测 **87/191 = 45.55%** | `v2/evidence/r46-c1-effect-metrics/anchor-stale-a1.txt` 首行 |
| F3 | 错位 100% 等于「同轮内前一次 `PLACE_MOVE.from_place`」，且「既非 from 也非 to」= 0（判伪反例为 0） | 同上第 2 行 |
| F4 | 该错位在两臂里**共担**（A0 无 scene 键；A1 有键且有错位），所以 R46 的「效果不成立」是在**给模型看了错误地点**的前提下测出来的 | `metrics-table.md §0`、§2b |
| F5 | 修复后必须只差一个变量：两臂都开 `LIFE_PROMPT_SCENE=1`，唯一差异 = `HITT_SCENE_FRESH` | 本卡 §3；`tools/r52/arm_inner.sh` |

> 术语纪律：以上都是**机制层事实**，不是效果结论。R46 的 A0/A1 数字与本轮**不做跨轮比较**（见 §8）。

---

## 2. 假设

- **H1（机制层）**：打开 `HITT_SCENE_FRESH`（装配消息时点重新 `perceive()`）后，`ctx.scene.place` 与
  `payload.place` 的一致率上升到 ≥ 95%（两者同源，理论上应接近 100%；留 5pp 余量吸收"消息落盘前又有一次移动"等边界）。
- **H2（效果层）**：锚点指对后，模型看到的场所与发言实际发生的场所一致，**处所-内容一致性率**相对 OFF 臂上升。
- **H0**：修复不改变一致率，读数差异来自噪声。

## 3. 两臂设计（单变量，逐字冻结）

| 项 | OFF 臂 | ON 臂 |
|---|---|---|
| 分支/树 | `feat/r52-scene-anchor-fresh`，同一 `HEAD` | 同左（同树） |
| `LIFE_PROMPT_SCENE` | `1` | `1` |
| `HITT_SCENE_FRESH` | **不设**（取 `WorldView` 快照 = 改动前语义） | **`1`**（装配时点重新 perceive） |
| `HITT_LLM_PROVIDER` | `openai_compat` | 同左 |
| `HITT_WORLD_SEED` | `42` | 同左 |
| 批参 | `--seed 42 --agents 16 --rounds 36 --flush-every 2` | 同左 |

- **唯一差异 = `HITT_SCENE_FRESH`**，由 `env_manifest.txt` 逐 key 双向比对核验（`scene_fresh_rate.py` 之外的人工对账项）。
- **r36 而非 r24 的理由（功效）**：r24 在基线 p≈0.34、可判定分母 174/165 下 MDE = **14.99pp**，
  只比预登记阈值 15pp 低 0.01pp ≈ 零余量；r36 把每臂可判定分母抬到 ≈260，MDE 降到 **12.04pp**（§4.2 复算命令）。
  **这是「同一口径下提升功效」，不是「沿用 R46 基线」**——阈值 15pp / 0.55 沿用理由见 §4.3。

## 4. 判据（冻结；事后不得下调）

### 4.1 机制层 M1（通过线）

- `anchor_fresh_rate(ON) ≥ 0.95`（分母 = 含 `ctx.scene` 键的对话条数）。
- 不成立 ⇒ 无论效果层数字如何，本轮判定只能是「**机制未接通**」。

### 4.2 效果层 E1（通过线）

- `consistency_rate(ON) − consistency_rate(OFF) ≥ +15.0pp`（绝对百分点）；
- **且** `consistency_rate(ON) ≥ 0.55`；
- 检验方法：两独立比例 2×2（相符/相悖 × 臂）**Fisher 精确检验双侧**，报 `p` 但不作为通过线（通过线是绝对阈值）；
- **MDE 复算（α=.05 / power=.80，仓库既有口径 `tools/metrics/need_to_speech.py::mde_pp`）**：

```bash
python3 -c "import sys;sys.path.insert(0,'tools/metrics');from need_to_speech import mde_pp;print('r24:',mde_pp(0.3394,174,165));print('r36:',mde_pp(0.34,260,260))"
# → r24: 14.99
# → r36: 12.04
```

⇒ 本轮 MDE = **12.04pp < 15.0pp 阈值**，判据在 r36 下**可判（有余量）**。

### 4.3 阈值沿用理由（必读，防"事后改口径"）

15pp / 0.55 沿用 `v2/refs/C1-scene-prereg-20261101.md §4` 的**先验判断**，沿用理由是"**口径不变（同一把词表尺子、同一分母定义），只是把样本量抬到能检出它**"，**不是**"沿用 R46 的旧基线数字"。
R46 的 A0/A1 读数在本轮**既不作基线、也不作对照**（§8）。

### 4.4 不可判条件（命中任一即写「不可判」，**不得写「不成立」**）

1. 任一臂可判定分母 `judged < 68`（照看板纪律：分母 <68 一律 `probe=true`，只报条数）；
2. 两臂 `env_manifest.txt` 差异**不止** `HITT_SCENE_FRESH` 一行（两臂不可比）；
3. 任一臂 `obs llm-cost --require-provider openai_compat` 的 `provider_guard.ok != true`、或 `run_batch.rc != 0`、或 `wc -l run.jsonl != meta.events`；
4. 两臂 `lexicon_sha256` 不一致（判据漂移）；
5. 两臂 `no_cue` 占比相差 ≥ 10pp ⇒ 主指标仍给，但降级为「不可判（子集构成漂移）」，除非分层读数同向（分层每组 `judged < 30` 只报条数）。

## 5. 手指令五条（跑批纪律，逐条可核验）

1. 起跑前 `pgrep` 三重探针（`orchestration[[:space:]]+run` / `[r]un_[b]atch` / `[n]ightly\.py`）无命中；
2. `flock -n /tmp/hitt.batch.lock` 全程持有（fd 9），拿不到立即退出码 22，不降级；
3. `tools/d5/check_clean_tree.py` 对 `code/{life,orchestration,config,engine}` 硬闸（本轮改了 `code/life`，**改动必须在起批前 commit**）；
4. 进程一律 `setsid` 起，批体内不长 sleep（仅 30s 心跳写时间戳，不参与判定）；
5. 两臂**串行**：OFF 收批（`run_batch.rc`）后才起 ON。

## 6. 读数与复算命令（他人照抄可复现）

```bash
# 0) 机制层 + 效果层两臂对照（Fisher / Wilson / 阈值机械比对）
python3 tools/metrics/scene_fresh_rate.py \
  --compare-off v2/evidence/r52-scene-fresh-off-<date>_n16r36_s42/run.jsonl \
  --compare-on  v2/evidence/r52-scene-fresh-on-<date>_n16r36_s42/run.jsonl \
  --out-json v2/evidence/r52-scene-fresh/compare.json

# 1) 冻结主指标原尺子（独立复核，数字须与上面 consistency 一致）
python3 tools/metrics/place_content_consistency.py --run <arm>/run.jsonl

# 2) 幂等自检（同一输入两次运行逐字节一致）
python3 tools/metrics/scene_fresh_rate.py --run <arm>/run.jsonl > /tmp/a.txt
python3 tools/metrics/scene_fresh_rate.py --run <arm>/run.jsonl > /tmp/b.txt
cmp /tmp/a.txt /tmp/b.txt && echo BYTE_IDENTICAL

# 3) 真 LLM 验真（在 code/ 下）
cd code && python3 -m obs llm-cost --log ../v2/evidence/<arm>/run.jsonl --require-provider openai_compat

# 4) OFF 逐字节等价（3 组夹具 × 2 装配点）
LIFE_PROMPT_SCENE=1 python3 tools/r52/prompt_hash_probe.py --label off --out-json /tmp/r52_off.json
python3 -c "import json;a=json.load(open('v2/evidence/r52-scene-fresh/prompt_hashes_pre_change.json'));b=json.load(open('/tmp/r52_off.json'));a.pop('label');a.pop('env');b.pop('label');b.pop('env');print('OFF==PRE:',json.dumps(a,sort_keys=True)==json.dumps(b,sort_keys=True))"
```

## 7. 已知局限（写清以便解释时不夸大）

1. **规则版尺子，未用 LLM judge**：结论强度弱于人工标注；同一 `run.jsonl` 两次运行逐字节一致是它的立身之本。
2. **词表覆盖有限**：`no_cue` 占比会随文体漂移（R46 两臂 8.90% vs 13.61% 已有先例）⇒ §4.4 第 5 条设了降级闸。
3. **场所"允许集"是先验设定**（如"在广场修陀螺"判相悖），非客观真理；两臂在同一张表下比较，比较本身成立。
4. **单 seed（42）**：无批间方差估计，差异只能作点估计，不外推到其他 seed。
5. **能力边界**：本修复只让锚点指对地方；**不保证**模型一定会顺着锚点说话。若 E1 未达标，只能说明"锚点指对了但没用上"，
   这仍是有效信息（把根因从"给了错位置"推进到"给了对位置但提示词影响力不足"）。

## 8. 与 R46 的可比性边界（Leader 闸门 2，必须写死）

- R46 每臂对话 191 条、可判定分母 174/165；**本轮每臂 ≈260 条，denominator 量级不同**。
- 因此：**不得**把 R46 的 `A0 0.3333 / A1 0.3394` 与本轮读数直接比较，**不得**写「比 R46 提升/下降 X pp」。
- 允许的引用方式：只把 R46 当**缺陷发现的外部证据**（87/191=45.55%、判伪反例 0），以及 MDE 复算的**基线 p 来源**（p≈0.34，仅用于功效计算，不用于效果比较）。
- 若必须提及跨轮方向，只能写成「量级一致/不一致的描述性观察，不构成比较结论」。

## 9. 时间戳对账（Leader 闸门 3，机械可核验）

```bash
# a) 本卡入库 commit 时间
git log -1 --format='%H %ci %s' -- reports/R52-prereg-scene-fresh-20261102.md
# b) 起批时刻（臂启动器写入）
cat v2/evidence/r52-scene-fresh-off-<date>_n16r36_s42/start_epoch.txt | xargs -I{} date -d @{} -Is
# 判定：a 的时间必须早于 b（报告 §5 贴两者原文）
```

## 10. 判定参与方

- 主指标**不使用 LLM judge**，为确定性规则版。
- 判定三档分开写：① 机制接通（M1）② 效果成立（E1）③ 生活气息提升（**本卡不判**：无人工盲评 / 无 judge / 单 seed）。
