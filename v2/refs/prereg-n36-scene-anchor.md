# 预登记 · N-36「F-8 处境锚（scene-anchor）」同 sha 双盲配对臂判据（R21 修正版）

> **状态**：**已冻结，早于本轮任一臂起跑**（本文件 commit 时 `v2/evidence/n36-*` 两臂目录均不存在）。
> **性质**：判据、守卫与陷阱阈值**事前写死**；事后任何调整须在 §9 记 Amendment，并声明「未看数据/已看数据」，后者降级为 exploration。
> **前身**：`v2/refs/prereg-r21-scene-anchor.md`（sha256 `0fc91070…`）。本文件**不是**重跑 R21，而是**修正 R21 §5.1 的结构性缺陷后**做一次同 sha 配对复验。

---

## 0. 为什么要修正 R21 判据（本轮必须先说清）

R21 §5.1「不可判」档写有否决条：任一项满足即判不可判，其中一条是

```
F-8a = not_applicable
```

而 `F-8a` 的分子/分母**只在 `ctx.scene.activity` 存在时可算**（`tools/d5/dialogue_metrics.py::compute_f8`，
`not_applicable_if_zero="no_ctx_scene"`），`ctx.scene` 又**只在 `LIFE_PROMPT_SCENE=1` 时产出**
（`code/life/scene_anchor.py:29` + `code/life/agent.py:1548-1569`）。

⇒ **OFF 臂必然 `F-8a = not_applicable`**（R21 实测 OFF 臂 `ctx.scene` 覆盖 0/191）。
⇒ 「任一臂 F-8a = not_applicable ⇒ 不可判」这条**在单变量设计下恒真**，「成立」在数学上不可达。
这与 `R15` 的「F1/F2 结构互斥」同型：**否决条写成了一个由设计本身保证成立的条件**。

**本轮修正（本文件即修正件）**：

| R21 原条 | 本轮处置 |
|---|---|
| 否决条 `F-8a = not_applicable` | **删除**。改为：`F-8a` 是 **ON-only 描述性通道**，不进配对判定、不进否决条；报告须单列 ON 臂 `F-8a` 分子/分母/率，并说明「该通道在 OFF 臂结构性不可测，不得参与配对比较」 |
| 其余否决条（CI 重叠 / 分母 <30 / 守卫击穿） | **保留**，并把「守卫击穿」逐条写成可复算的阈值（见 §6） |
| 主判据（F-8t_core 与 F-8p_place 双项 Δ≥+3.0pp 且 CI 不重叠） | **保留为分项判据**；**新增**总口径 `F-8`（三通道并集，per-message，den=全部 MSG）作为**主报读数**，两者同屏 |

> 关键点：**总口径 `F-8` 在 OFF 臂是可测的**（R21 之外的新批实测：n15-off 基线 `F-8 = 18/686 = 2.62%`），
> 因此它可以承担「主报读数」；而 `F-8a` 只作 ON 侧归因，不再有权否决整轮结论。

---

## 1. 文件身份

| 项 | 值 |
|---|---|
| 预登记时间 | 2026-10-31T04:04+08:00（两臂起跑前，见本文件 commit） |
| 仓库根 | `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment` |
| 分支 | `exp/n36-scene-anchor`（父提交 `1d0bc9a`，即 `feat/n15-addr-evolve` HEAD） |
| 指标真源 | `tools/d5/dialogue_metrics.py` sha256 `1d914735f3a13cf4e1640bd694f1d0e070096c9f50abfdefa7359417df551271` |
| F-8 词表 | `tools/d5/f8_lexicon.json` sha256 `004f3bca138e7800a0fc0ac7e0f1c0f0bdb9b0a862432fa53f65b152bdb2ddd3`（`f8-lexicon-v3`） |
| F-8 实现 | `code/life/scene_anchor.py` sha256 `6088a40cc603d67eaba9577e2cafda606b0d2be3fbd952dd13ebb7834f336b70`；接线 `code/life/agent.py` sha256 `e323a7ef05a112e46b0354a3fc6955cbc9e551cff808f06476e3fdab8d64e105` |
| 本轮行为代码改动 | **零改动**：`code/{life,engine,orchestration,config}` 一个字节不改（纯开关开通；见 §2） |

---

## 2. 唯一变量与两臂（同 code_sha 硬要求）

| 臂 | 目录 | `LIFE_PROMPT_SCENE` |
|---|---|---|
| **A · scene-OFF（基线）** | `v2/evidence/n36-off_n16r84_s42/` | **不设该环境变量**（不是空串） |
| **B · scene-ON** | `v2/evidence/n36-on_n16r84_s42/` | `=1` |

- 两臂**必须同 `code_sha`**：本预登记 commit 后**不再向仓库提交任何代码或文档**，直到两臂全部收批；
  `meta.code_sha` 两臂都必须等于**本文件所在 commit**（R21 §2.2 已登记 `meta.code_sha` 语义 = 生成 meta 时 HEAD 快照，
  故本轮**禁止跑批期间提交**，以此把该缺陷的影响压到零）。
- **允许差异仅三项**：① `LIFE_PROMPT_SCENE`；② `out_dir`；③ `side_root`。其余全等：`seed=42`、`agents=16`、`rounds=84`、`flush_every=2`、
  其它 `LIFE_PROMPT_*` / `HITT_*` 一律不设（`code/.env.local` 实测仅 `HITT_LLM_PROVIDER` + `LLM_API_KEY`）。
- 禁用 R21 的 `run_scene_anchor_{on,off}_seed42_n16r24` 作对照（异 sha `3bb4430` / `e878a6e`），也禁用 `n15-off/n15-on`（异 sha `fff3e2da` / `0c94bcf2`）。

---

## 3. 样本口径

```text
seed=42  agents=16  rounds=84  flush_every=2   （= 1 模拟周，WEEK_ROUNDS=84）
launcher=tools/d2/run_batch.sh（内建 preflight 串行闸 + meta 生成 + wc -l 自检 + obs llm-cost 门禁）
side_root=/tmp/n36_{on,off}_side（两个不同空目录）
```

- 单 seed、单模拟周 ⇒ **全部数字只作点估计、不可外推**。
- 分母纪律（R1 §2.5）：per-message 分母 < 30 ⇒ 只报事件数、不报百分比；本轮主口径 den=全部 MSG（预期 ~686，≥30）。

---

## 4. 机制闸（先过闸，再谈效果）

| 编号 | 判据 | 通过条件 | 复算 |
|---|---|---|---|
| **M1** | 提示词接线：ON 提示词原样减掉那一行后与 OFF 逐字节相等 | `code/life/tests/test_scene_anchor.py` 全绿（本轮实测 **28 passed**） | `cd code && python3 -m pytest life/tests/test_scene_anchor.py -q` |
| **M2** | ON 臂 MSG payload 带 `ctx.scene` | ON ≥ 95% 的 MSG（阈值从 R21 的 100% 放宽到 95%，理由：`wv is None` 的退化路径按设计不产 scene） | `dialogue_metrics.py` 的 `F-8_scene_anchor.diagnostics` 与 `F-8a` 的 `n_scene_present` |
| **M3** | OFF 臂 `ctx.scene` 键不出现 | **= 0** | 同上 |
| **M4** | `ctx.scene.line_sha256` 可反解（ON） | `n_line_recovered > 0` 且反解率 ≥ 90% of `n_scene_activity` 之外的 scene 条数（只作机制证据，不参与效果判定） | `F-8t_exact_injected_word.denominator` |
| **M5** | 真跑 | `obs llm-cost --require-provider openai_compat` **rc=0**、`provider_guard.ok=true`、`degraded=0`、`dialogue.cached=0` | §7 |

M1–M5 任一不过 ⇒ 结论写「**机制未生效/批次无效**」，不得写「F-8 无效」。

---

## 5. 主判据

### 5.1 主报读数（新增，可两臂对测）

`F-8`（`tools/d5/dialogue_metrics.py::compute_f8` 的 `"F-8"` 键）：
**num = 正文命中本人当回合处境（时段档内词 / 自身地点 `name_cn` / 活动 任一）的 MSG_* 条数；den = 全部 MSG_***。
基线（n15-off，同工具同词表）实测 `18/686 = 2.62%`，Wilson95 `[1.67%, 4.11%]`。

### 5.2 分项判据（沿用 R21 §5.1 的双项结构，逐项独立判定）

令 `Δ = 100 × (ON − OFF)`（pp）：

| 分项 | 口径 | 达标条件 |
|---|---|---|
| `F-8t_core` | 档内时段词（本人当回合 slot，排除 `slot_agnostic`「这会儿」）；den=有 slot 的 MSG | `Δ ≥ +3.0pp` **且** 两臂 Wilson95 CI 不重叠 |
| `F-8p_place` | 只认 `places.json::name_cn`（含可接受简称），要求「本人 place」；den=有 `payload.place` 的 MSG | 同上 |

`F-8a`（活动）**只作 ON 侧归因**，不进判定（理由见 §0）。

### 5.3 判定档

| 判定 | 条件 |
|---|---|
| **成立** | `F-8`（§5.1）Δ ≥ +3.0pp 且 CI 不重叠，**且** `F-8t_core` 与 `F-8p_place` **两项都**达标，**且** 未触发 §6 任一否决 |
| **部分成立（单项）** | `F-8` 达标，但 `F-8t_core` / `F-8p_place` 只有一项达标 → **必须写明是哪一项**，不得合并成「成立」 |
| **未达标** | `F-8` Δ < +3.0pp |
| **不算改善** | `F-8` 达标但触发 §6 的**陷阱 1（旁白同步上升）**或**陷阱 2（L-7 恶化）** → 一律判「不算改善」，不得写「提升/改善」 |
| **不可判** | 两臂 CI 重叠 / 任一分项分母 < 30 / 机制闸 M1–M5 未过 / 出现未登记的额外变量 |

---

## 6. 否决条与陷阱阈值（**逐条可复算，且两臂都可测**）

| 编号 | 判据 | 阈值 | 基线（n15-off） | 说明 |
|---|---|---|---|---|
| **V1** | 陷阱 1：旁白率同步上升 | `L-2_narration_rate_proxy(ON) − (OFF) ≥ +3.0pp` ⇒ 判「用旁白换生活气息」，**不算改善** | `0.886297`（88.63%） | 同时并列 `L-3_paren_block_any`（0.946064）作交叉验证 |
| **V2** | 陷阱 2：L-7 撞车率恶化 | `L-7_dup_ngram8_rate(ON) − (OFF) ≥ +3.0pp` ⇒ 取消改善 | `0.44898`（44.90%） | 必须与 F-8 同屏 |
| **V3** | 守卫：内部 id 泄漏 | `place_id_in_body(ON) > 0` ⇒ **硬失败**（L-8c 回归） | 0/686 | 场景锚一旦把 `plaza`/`farm` 递进正文即击穿 |
| **V4** | 守卫：L-13 token 泄漏 | `L-13(ON) > L-13(OFF)` ⇒ 不可判 | 0/686 | 不得高于基线 |
| **V5** | 守卫：F-7a 越界提及 | `F-7a(ON) − F-7a(OFF) ≥ +3.0pp` ⇒ 不可判 | 95/686 = 13.85% | 「F-7a 不得恶化」按 +3pp 同档执行 |
| **V6** | 机制：OFF 臂未关住 | OFF 臂 `ctx.scene` 出现条数 > 0 ⇒ 起跑无效 | — | 同 M3 |

> `+3.0pp` 阈值**借用** R21 §5.1 的既有档位（非本轮新造）；陷阱 1/2 的「同屏并列」纪律来自 `reports/R4-life-texture.md:88-90`。

---

## 7. 收批验收命令（第三方可照抄）

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment
# A. 三件套 + 行数
for arm in off on; do d=v2/evidence/n36-$arm\_n16r84_s42; ls -la $d; \
  python3 -c "import json,sys;m=json.load(open('$d/meta.json'));print(m['events'],m['code_sha'],m['duration_sec'])"; \
  wc -l < $d/run.jsonl; done
# B. 真跑门禁
cd code && for arm in off on; do python3 -m obs llm-cost --log ../v2/evidence/n36-$arm\_n16r84_s42/run.jsonl \
  --require-provider openai_compat | tail -1; echo "rc=$?"; done; cd ..
# C. 指标复算
for arm in off on; do python3 tools/d5/dialogue_metrics.py \
  --log v2/evidence/n36-$arm\_n16r84_s42/run.jsonl --meta v2/evidence/n36-$arm\_n16r84_s42/meta.json \
  --out-json /tmp/metrics_n36_$arm.json --out-md /tmp/metrics_n36_$arm.md; done
```

---

## 8. 结论边界（事前写死）

- 单 seed、单模拟周 ⇒ 只作**点估计**，不外推、不写「生活气息提升」。
- 本轮只测 `F-8` 一个维度；`L-7` / 旁白率 / `F-7a` / `L-13` 只作守卫，不作效果结论。
- ON 臂 F-8 增量中，若「逐字回声注入措辞」占比过高（`F-8t_exact_injected_word`），须在报告中单列该比例，说明增量性质。

## 9. Amendments

（暂无）
