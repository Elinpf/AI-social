# 预登记 · R21「处境锚（scene-anchor）」配对臂判据

> **状态**：**已冻结，早于 OFF 臂起跑与任何 OFF 臂读数**（本文件 commit 时 OFF 臂目录尚不存在）。
> **性质**：判据与守卫**事前写死**；任何一项事后调整须在本文件 §10 记 Amendments 并说明「未看数据」还是「已看数据」，后者一律降级为 exploration。
> **口径纪律**：只引用仓库既有冻结口径（R4 §3.1 F-8 三分解、`tools/d5/dialogue_metrics.py` 的 `compute_f8`、`tools/d5/f8_lexicon.json` v3、R1 §2.5 分母纪律、D12-B/R13/R14 先例阈值），**不新造阈值**；凡借用先例阈值，均标「借用 + 出处」。

| 项 | 值 |
|---|---|
| 预登记时间 | 2026-10-23T08:2x+08:00（OFF 臂起跑前；见本文件 commit 时间戳） |
| 仓库根（主树） | `/root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment` |
| 跑批树（worktree） | `<主树>/.worktrees/scene-pair-r21` |
| 分支 | `feat/scene-pair-r21` |
| **固定 sha（两臂同树）** | `3bb44308291c8ea61d71ae0c595ff2e8b09b5502`（`3bb4430`） |
| provider | 真 LLM `openai_compat`（`obs llm-cost --require-provider openai_compat` rc=0 为唯一判决） |
| 被测维度 | **F-8 处境/场景锚定**（本轮唯一维度） |

## 1. 唯一变量与两臂

| 臂 | 目录 | 开关状态 |
|---|---|---|
| **ON（已有，不重跑）** | `v2/evidence/run_scene_anchor_on_seed42_n16r24/` | `LIFE_PROMPT_SCENE=1` |
| **OFF（本轮补跑）** | `v2/evidence/run_scene_anchor_off_seed42_n16r24/` | `LIFE_PROMPT_SCENE` **不存在**（不是空串） |

- 被测单变量 = `LIFE_PROMPT_SCENE`（见 `code/life/scene_anchor.py:29 SCENE_ENV`，默认 OFF）。
- **两臂允许差异清单（只有三项）**：① `LIFE_PROMPT_SCENE`（off=不存在 / on=1）；② 臂序调度参数 `ORDER`；③ `out_dir` / `side_root`。其余必须全等：`code_head`、`code/config/*.json` 逐文件 sha256、其它 `LIFE_PROMPT_*` / `HITT_*`、`seed`、`agents`、`rounds`、`flush_every`。
- **禁止**叠加第二个 env（`LIFE_PROMPT_TOPIC_LABEL` / `GOSSIP_G1` / `MEMORY_F6` / `LIFE_PROMPT_L7_STRUCT` / `LIFE_PROMPT_TOPIC_BREADTH` 等一律不动）。若 OFF 臂起跑时的 `code/.env.local` 含任何 `LIFE_PROMPT_*` ⇒ **拒绝起跑**（沿用 ON 臂 launcher 闸门 2b）。

## 2. 为什么必须固定 `3bb4430`（同树前提）

- 主树 HEAD `a6d6be0` 含 `882e5dd`「L-13 人话映射默认生效」，`git diff --stat 3bb4430 HEAD -- code/life` 显示 `code/life/agent.py` +14/−3 ⇒ 主树跑 OFF 会与 `3bb4430` 的 ON 臂构成**双变量**。
- 因此两臂一律在 `3bb4430` 上跑；`code/life/agent.py` 与 `code/life/scene_anchor.py` 的 sha256 必须与 ON 臂 `env_dump.txt` 的 `FROZEN` 行逐字一致（收批时核对）。

## 3. 样本口径（写死）

```text
seed=42  agents=16  rounds=24  flush_every=2
launcher=tools/d2/run_batch.sh（产出 meta.json + [d2] OK 收尾 + 内建 obs llm-cost 门禁）
side_root=/tmp/scene_anchor_off_side
规模上限：LLM 调用量应与 ON 臂同量级（ON 臂实测 2252 次，见其 host.log 末行 by_provider）
```

- **单 seed**；OFF 臂被中断 ⇒ 作废重跑，不使用 `--resume-from`。
- 分母纪律（R1 §2.5）：per-message 指标分母 < 30 ⇒ **只报事件数，不报百分比**；per-message 分母 < 68 ⇒ 不用消息级 B2 档，改报 Wilson CI 并标「本规模下无法判定」。

## 4. 机制闸（**先过闸，再谈效果**；不过闸 ⇒ 效果一律「不可判」）

| 编号 | 判据 | 通过条件 | 复算 |
|---|---|---|---|
| **M1** | 提示词接线：ON 提示词**原样减掉那一行**后与 OFF 提示词逐字节相等 | 单测全绿（`code/life/tests/test_scene_anchor.py`，含「OFF 逐字节不变 / ON 只插一行 / 人话不泄 id / 确定性 / 审计键」五条） | `cd code && python3 -m pytest life/tests/test_scene_anchor.py -q` |
| **M2** | ON 臂 MSG payload 带 `ctx.scene` | `>= 100%`（ON 臂实测 191/191；OFF 臂必须 `0/191`） | 见 §7 命令 `scene_cover` |
| **M3** | OFF 臂 `ctx.scene` 键不出现 | `= 0`（出现即说明开关没关住 ⇒ 起跑无效） | 同上 |
| **M4** | `ctx.scene.line_sha256` 与该行正文一致（ON） | 抽检一致率 100%（`dialogue_metrics.py` 的 `F-8a` 依赖它恢复行文本） | `compute_f8` 的 `n_line_recovered` |
| **M5** | 真跑 | `obs llm-cost rc=0`、`provider_guard.ok=true`、`degraded=0` | §7 |

**处置**：M1–M5 任一不通过 ⇒ 结论写「**机制未生效/批次无效**」，**不得**写「F-8 无效」。

## 5. 主判据：F-8 三分解（口径冻结，不改词表）

**唯一实现**：`tools/d5/dialogue_metrics.py::compute_f8`（`F-8t` 时段 / `F-8p` 地点 / `F-8a` 活动），词表 `tools/d5/f8_lexicon.json` v3（外置冻结，sha 记录在 `v2/evidence/f8_metrics_selfcheck.txt`）。**本轮不改这两份文件的任何字节**（改了等于改判据）。

主读三项（沿用 CYCLE-06 §P-2 的验收要求，逐项给分子/分母）：

| 指标 | 口径（冻结实现原文） | 分母 |
|---|---|---|
| `F-8t_core` | 档内时段词（本人当回合 slot，排除 `slot_agnostic` 通用指示词） | 有 slot 的 MSG |
| `F-8t_all` | 档内 + 通用指示词（宽口径，仅登记不判主） | 同上 |
| `F-8p_place` | 只认 `places.json::name_cn`（含可接受简称），要求「本人 place」 | 有 `place` 的 MSG |
| `F-8a` | 渲染措辞 ∪ 语义等价项，**仅在 `ctx.scene.activity` 存在时可算**；缺失 ⇒ `not_applicable`（不填 0） | 有 `ctx.scene.activity` 的 MSG |

### 5.1 判定档（写死）

令 `Δ = 100 × (ON − OFF)`（pp）：
`F-8p_place` 与 `F-8t_core` 各自独立判定，主判定取**两者都达标**为「成立」：

| 判定 | 条件（全部满足） |
|---|---|
| **成立** | `Δ(F-8t_core) ≥ +3.0pp` **且** `Δ(F-8p_place) ≥ +3.0pp` **且** 两项各自两臂 **Wilson 95% CI 不重叠** |
| **部分成立（单项）** | 仅其中一项满足上述三条，另一项不满足；**必须在结论中写明是哪一项**，不得合并成「成立」 |
| **未达标** | 两项 `Δ < +3.0pp` |
| **不可判** | 任一：两臂 Wilson 95% CI 重叠 / 分母 < 30 / `F-8a = not_applicable` / 任一守卫击穿（§6） |

- **`+3.0pp` 是借用阈值**，出处：`v2/evidence/d12b_prereg_skeleton.md §3`（「具体性 ON − OFF ≥ +3pp」）与本仓库 R12/R13/R14 的「+3pp 量级」先例。**本预登记未新造阈值**。
- **上界（B2 噪声带）**：冻结带文件 `v2/evidence/d5_noiseband_bootstrap_t300_t355.json` 的 `B2_band_by_denom` **只覆盖 `item:L-*` / `pair:K1_*` / `thread:*`，不含 F-8 三项**（`tools/d5/dialogue_noiseband_bootstrap.py::item_flags` 的 item 集不含 F-8）。⇒ **不借用他项带宽**（借用会把别人的抽样性质安到 F-8 头上），改用**两臂各自 Wilson 95% CI 是否重叠**作为上界替代，并在报告中如实写「B2 未覆盖 F-8，故用 Wilson CI 重叠判定」。
- **`F-8t_all` / `F-8t_sens_add` / `F-8t_pre_am2` 只登记、不判主**（宽口径易膨胀，`f8_lexicon.json` 已警告）。

### 5.2 已知功效限制（**事前登记，防止事后找借口**）

- ON 单臂 MSG **191** 条（`run_scene_anchor_on_seed42_n16r24/run.jsonl` 的 `MSG_DM 167 + MSG_PUBLIC 24`）⇒ 消息级分母 ≈ 191。
- 参照 `v2/evidence/f8_metrics_selfcheck.txt` 的工具自检量级（`F-8t_all 5/191 = 2.6178%`），若 OFF 基线在 3% 上下，则 **+3pp 增量在 n≈191 下 Wilson 95% 半宽约 ±4pp** ⇒ 两臂 CI 大概率重叠、判定落到「不可判」。
- **这是本轮样本量与判据之间的已知冲突**：必须在报告中直写「本规模下无法判定」，**不得**为了得到结论而临时下调阈值或换口径。若结果确为「不可判」，那是**诚实结论**，不是失败。

## 6. 守卫（任一击穿 ⇒ 效果判「不可判」，沿用 R13 §3 / R14 §0.3 先例）

| 编号 | 守卫 | 击穿条件 | 出处/依据 |
|---|---|---|---|
| **G1** | **L-13 内部 token 泄漏**（`L-13_token_leak`，事件数不报率） | ON 臂条数 **> OFF 臂条数**（「不得高于基线」） | R13 §4.3 预注册守卫原文；分母纪律见 R12 §274 |
| **G2** | **L-7 8-gram 重复率** | `Δ(ON − OFF) > +9.043pp`（冻结带 `item:L-7` 的 **denom=188 档** `hi_97.5`；本轮消息分母 191 取最接近档 188，报告中写明「最接近档」） | `v2/evidence/d5_noiseband_bootstrap_t300_t355.json`；击穿判法沿用 R14 §0.3 |
| **G3** | **L-1 长度** | `len_p50(ON) < 0.90 × len_p50(OFF)`（不降 >10%）；`len_p50/p90` 只登记 | D12-B 预登记 §3 借用 |
| **G4** | **结构三项** | `MSG` / 线程数 / ≥3 轮线程数 两臂差 **> ±5%** | D12-B 预登记 §3 借用 |
| **G5** | **真跑** | `obs llm-cost rc≠0` / `provider_guard.ok≠true` / `degraded≠0` | R1 §3「rc 即判决」；`code/obs/llmcost.py` |

- **G2 说明**：场景锚只插一行（+30~50 字符，`scene_anchor.py` 头注释），理论上不该推动 8-gram 重复；若仍超带，说明「单行插入也把句式拉齐了」，必须当场认、不得只引正面样例（R14 §0.3 教训）。
- **禁止**：不许因为「G1/G2 是既存缺陷」就跳过；`L-13` 在 R12/R13 三臂均 > 0，属既存缺陷，但本轮判法仍是「不得高于基线」。

## 7. 复算命令（写死，第三方可照抄）

```bash
# 0) 树与串行（起跑前，人工确认；不要用带裸 run_batch 字样的命令行调 preflight，会假阳性 rc=9）
cd <worktree> && git rev-parse HEAD        # 期望 3bb44308291c8ea61d71ae0c595ff2e8b09b5502
pgrep -f "[o]rchestration run"             # 期望无输出（rc=1）

# 1) 机制闸 M2/M3：ctx.scene 覆盖率（两臂各跑一次，只读）
python3 - <<'EOF'
import json,sys,collections
p=sys.argv[1]; n=0; sc=0; act=0; plc=0
for line in open(p):
    line=line.strip()
    if not line: continue
    e=json.loads(line)
    if str(e.get("type","")).startswith("MSG"):
        n+=1; c=((e.get("payload") or {}).get("ctx") or {}).get("scene") or {}
        sc += bool(c); act += bool(c.get("activity")); plc += bool(c.get("place"))
print({"msgs":n,"with_scene":sc,"with_activity":act,"with_place":plc})
EOF
#   用法: python3 上面这段 <run_dir>/run.jsonl

# 2) 指标（唯一真源，两臂各一份）
python3 tools/d5/dialogue_metrics.py --log <run>/run.jsonl --meta <run>/meta.json \
  --out-json v2/evidence/d5_metrics_<tag>.json --out-md v2/evidence/d5_metrics_<tag>.md
#   或一键: bash tools/d5/run_batch_eval.sh <run_dir> <tag> 3bb4430

# 3) 真跑（G5）
cd code && python3 -m obs llm-cost --log ../<run>/run.jsonl --require-provider openai_compat

# 4) F-8 交叉复算（非真源，只作交叉校验）
python3 tools/d9/f8_crosscheck.py --log <run>/run.jsonl --meta <run>/meta.json

# 5) 单测（M1）
cd code && python3 -m pytest life/tests/test_scene_anchor.py -q
```

## 8. 处置规则（一句话）

> **M1–M5 任一不过 ⇒ 「机制未生效/批次无效」；G1–G5 任一击穿 ⇒ 效果「不可判」；两项主判据 CI 重叠 ⇒ 「不可判」。三种「不可判」含义不同，报告里必须分别写明是哪一条触发。**

## 9. Amendments（修订登记；供 `tools/d5/f8_lexicon.json:7` 的「§9 Amendment 1」引用）

| 编号 | 时间 | 内容 | 是否已见 OFF 臂读数 |
|---|---|---|---|
| **Amendment 1** | 2026-10-23T08:09+0800 | **无**（本轮未对词表、判据档、守卫阈值做任何增补或修改；`f8_lexicon.json` v3 与 `compute_f8` 一律照用） | **否** |

> 说明：本文件首版 commit（`e878a6e`）时 §9 为「不做什么」、Amendments 在 §10；为对齐 `f8_lexicon.json:7` 已冻结的引用链（「§2 + §9 Amendment 1」），**只做章节位对调**，判据与守卫一字未改：`git diff e878a6e -- v2/refs/prereg-r21-scene-anchor.md` 只含 §9/§10 章节标题与本节登记表的新增行，§1–§8 正文零差异。

## 10. 不做什么（硬边界）

- ❌ 不改 `code/{life,engine,orchestration,config}` 任何字节（`3bb4430` 原样跑）；`make verify` / `tools/tree_fingerprint.sh` 的冻结区指纹作旁证。
- ❌ 不改 `tools/d5/dialogue_metrics.py`、`tools/d5/f8_lexicon.json`（口径冻结）。
- ❌ 不引入第二个 env；不做天气/季节、WD 剂量、F-5 口径扩展（R21 范围外）。
- ❌ 不在本轮写「提升/改善」类定性词；只写数值与判定（成立 / 部分成立 / 未达标 / 机制未生效 / 不可判）。


