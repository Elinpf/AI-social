# R48 跨地点对话地理一致性 · 零跑批读数件（T3）

> 作者：仿真与跑批工程师｜2026-11-01 16:1x（+08:00）｜**读数件，非判定件**
> 脚本：`tools/r48/place_coherence.py`（新增，**只读**日志，不跑批、不调 LLM、不进冻结区）
> 当前树：`HEAD=a947cced518458102197d535c054af341ab550ab`，分支 `feat/r46-c1-effect-metrics`
> 本件不改任何 `code/life|orchestration|config|engine` 文件；未 commit

---

## 0. 先回答三个前置事实（决定 T4 走哪条路）

### 0.1 `payload.place` 在 DM 上有没有 null？

**没有。** 全部 112 个 `run.jsonl` 中，`MSG_DM` 的 `unknown_place` 恒为 `0`
（`place_from` / `place_to` 均可重建）。因此**不存在"把 null 当同地点"的污染**，
所有口径的分母都是完整可判子集。

| 量 | 值 |
|---|---|
| 扫描 `v2/evidence/*/run.jsonl` | 112 个 |
| 解析成功 / 校准通过 | 112 / 105（7 个为空批或无消息，标 `N/A`，非失败） |
| 其中 `MSG_DM` 总数 | 38,329 |
| `unknown_place`（DM 两端地点缺失） | **0** |

### 0.2 地点字段到底够不够用？——**够用，但需要重建**

`orchestration/integration.py::_do_social` 给消息落盘时写的是
`payload["place"] = st.agents[agent_id]["location"]`，即**只有发送方地点**。
接收方地点**不在消息事件里**。但它可以从 `PLACE_MOVE` / `PLACE_ARRIVED` 事件流
**按 `seq` 回放 100% 重建**。

**尺子自校准（本件最强的一条证据）**：重建出的"发送方地点"必须与消息里已写死的
`payload.place` 逐条相等。全库结果：**mismatch = 0**（无一条不符）。
`d9z-on` 单批 375/375、`r48-probe-mock` 161/161 全吻合。

⇒ 结论：**不是"字段缺失到测不了"**。字段可以直接用（发送方），接收方可靠重建。

### 0.3 当前树有没有 D9z（同回合可见性）？

| 检查 | 结果 |
|---|---|
| `grep -rn "INTRA_ROUND" code/` | **0 条命中** |
| 当前 HEAD | `a947cced`（`feat/r46-c1-effect-metrics`） |

⇒ D9z 属 `feat/d9z-intra-round@43a56c1`，**不在当前树**。

---

## 1. 决定性读数：当前树 gap=0 有多少？

**当前树 mock 批**：`v2/evidence/r48-probe-mock-n16r24-s42/`
（`sha256=61fce5ce…`，`code_sha=code_sha_end=a947cced…`，16 agents × 24 rounds，seed=42）

| 项 | 值 |
|---|---|
| 相邻往返总数（分母） | **116** |
| `gap=0`（同回合往返） | **0** |
| `gap=0` 且跨地点 | **0** |
| `gap=1` | 68（其中跨地点 39） |
| `gap>=2` | 48（其中跨地点 37） |
| 与之对照：DM 总数 / 跨地点 | 161 / **110（68.32%）** |

⇒ **当前树上 `gap=0` 跨地点 = 0 对，分母 116。**
跨地点对话本身极常见（68.32%），但**从不发生同回合往返**——它总是要等 ≥1 回合，
即"信件语义"，不是"当面说话"，也不是"瞬移传话"。

---

## 2. 多批并列：gap 分布 + 跨地点占比（每条附 sha8）

命令（仓库根）：

```bash
python3 tools/r48/place_coherence.py \
  --batch-dir v2/evidence/r48-probe-mock-n16r24-s42 \
  --batch-dir v2/evidence/c1-scene-a0-20261101_n16r24_s42 \
  --batch-dir v2/evidence/c1-scene-a1-20261101_n16r24_s42 \
  --batch-dir v2/evidence/d9t-on_n16r24_s42 \
  --batch-dir v2/evidence/d9z-on_n16r56_s42
```

| 批次 | sha8 | DM | 同地点 | 跨地点 | 跨地点占比 | gap=0 | gap=1 | gap>=2 | 分母(相邻对) | 校准 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|:--:|
| `r48-probe-mock-n16r24-s42`（**当前树**，mock） | `61fce5ce` | 161 | 51 | 110 | 68.32% | **0** | 68 | 48 | 116 | OK |
| `c1-scene-a0-20261101_n16r24_s42` | `1bfeb51d` | 161 | 60 | 101 | 62.73% | **0** | 72 | 43 | 115 | OK |
| `c1-scene-a1-20261101_n16r24_s42` | `c828b407` | 161 | 60 | 101 | 62.73% | **0** | 72 | 43 | 115 | OK |
| `d9t-on_n16r24_s42` | `af4c44d1` | 167 | 62 | 105 | 62.87% | **0** | 77 | 48 | 125 | OK |
| `d9z-on_n16r56_s42`（D9z 臂） | `1f0fec69` | 375 | 133 | 242 | 64.53% | **133** | 97 | 48 | 278 | OK |

**全库（105 个校准通过批次）汇总**

| 项 | 值 |
|---|---|
| DM 总数 | 38,329 |
| 同地点 / 跨地点 | 13,596 / 24,733（64.53%） |
| 相邻往返分母 | 28,234 |
| `gap=0` | **133（0.47%）** |
| `gap=1` | 20,482 |
| `gap>=2` | 7,619 |

**关键结构事实**：全库 133 条 `gap=0` **全部来自 `d9z-on` 一个批次**（`1f0fec69`）。
其余 104 个批次（含当前树 mock）`gap=0` **恒为 0**。
⇒ `gap=0` 是 D9z（`feat/d9z-intra-round`）引入的行为，**不是当前树的既有行为**。

---

## 3. 跨地点回复里，"回复方有没有真的走过去"

对跨地点回复（口径 A），查三件事：分子/同一分母并列，不叠乘。

| 读数 | 全库 | 当前树 mock |
|---|---|---|
| 跨地点回复分母 | 17,308 | 76 |
| (a) 截至回复时刻曾到过父条地点 | 8,735/17,308 = 50.47% | 21/76 |
| (b) 在 `[父轮, 回复轮]` 窗口内到过父条地点 | **155/17,308 = 0.90%** | **1/76** |
| (c) 回复那一轮完全没有 `PLACE_MOVE` | 9,705/17,308 = 56.07% | 39/76 |

⇒ 即使在"跨地点对话"这个大类里，**真正在窗口内走到对方所在地的比例 < 1%**。
这与 report-writer 的旁证方向一致。

**`gap=0` 专看（`d9z-on`）**：分母 74，窗口内到过父地点 **0/74**，该轮无位移 **44/74**。
（与 T2 独立复算的 `0/74`、`44/74` 完全一致。）

---

## 4. 两套口径必须分清（否则数字会被误用）

| 口径 | 判据 | `d9z-on` gap=0 | 语义 |
|---|---|---|---|
| **A（本工具主口径）** | 回复事件那一瞬间，双方是否同处（用重建位置） | 74 跨 / 133 | **时间正确**：回答"此刻在不在一个地方" |
| **B（既有 D9z 留档口径）** | 本条 `payload.place` vs 父条 `payload.place` | 74 跨 / 133（同） | 比较两个时点，会把"中间有人移动"混进来 |

**两口径在 `gap=0` 上恰好同值（74）**，但在 `gap=1` / `gap>=2` 上有差：

| gap | 口径A 跨 | 口径B 跨 | 差 |
|---|---:|---:|---:|
| 0 | 74 | 74 | 0 |
| 1 | 55 | 60 | 5 |
| >=2 | 44 | 46 | 2 |

**差异原因已逐条查证（不是猜测）**：7 条里 `口径B=跨` 但 `口径A=同`，全部是
**父条发言人自己移动到了回复方所在地**，例如

```
父 r4  P009@market   -> 回 r6  P016@cafe      收件人 P009@cafe
父 r8  P009@cafe     -> 回 r9  P016@residence 收件人 P009@residence
父 r14 P008@town_hall-> 回 r16 P011@market    收件人 P008@market
父 r20 P005@cafe     -> 回 r21 P007@residence 收件人 P005@residence
父 r29 P004@kitchen  -> 回 r30 P010@cafe      收件人 P004@cafe
父 r32 P003@cafe     -> 回 r33 P011@residence 收件人 P003@residence
父 r32 P009@cafe     -> 回 r33 P016@residence 收件人 P009@residence
```

即：**口径 B 会把"真的走过去碰面"误记为跨地点**。做物理一致性判断时应用口径 A；
与既有 `d9z-gap0-place-split` 留档对拍时用口径 B。

**与本件 278 分母的对拍**：`d9z-on` 口径 B 复算 = `278` 对、跨 180（74/60/46），
与 Leader 留档 `v2/evidence/d9z-gap0-place-split-20261101.md` **逐字一致**。

---

## 5. 与 report-writer 旁证的对拍（`d9t-on`，树 `cef1c58`，非 HEAD 祖先）

| 读数 | report-writer | 本件口径B 复算 | 一致 |
|---|---:|---:|:--:|
| 相邻对 | 125 | **125** | ✓ |
| 跨地点 | 89（71.20%） | **89（71.20%）** | ✓ |
| `[父轮,子轮]` 窗口内到过父条地点 | 1/89 | **1/89** | ✓ |
| 该轮无 `PLACE_MOVE` | 38/89 | **38/89** | ✓ |

差异只在一处且属**口径而非错误**：本件主口径（A）给 `d9t-on` 跨地点回复分母 **74**，
他的 **89** 是口径 B。同一个批同一份日志，两套口径各自自洽。

---

## 6. 边界与不可用声明

1. `r48-probe-mock-n16r24-s42` 是 **mock 批**：`meta.provider = "NON-REAL"`、`model = "mock-1"`、
   `llm_provider_in_events = {"mock": 2243}`。**此批 by_provider=mock，不可用于真跑验真**，
   只用于回答"当前树 gap=0 有多少"。它使用独立 `--side-root /tmp/r48_probe_mock_side`，
   未污染既有 freeze_cache；目录单独命名 `r48-probe-mock-*`，不入真跑批次命名族。
2. `d9z-on` / `d9t-on` 的**代码树不是当前树**（前者 `43a56c1`，后者 `cef1c58`，均非 HEAD 祖先）。
   它们只能证明"这种形态在历史上存在过"，**不能**当作当前树行为的证据。当前树读数以 §1 为准。
3. `gap` 用顶层 `round` 差计算，不是 `turn_index` 差。
4. 本件不设阈值、不给通过/不通过。

---

## 7. 复算入口（可原样重跑）

```bash
# 单批
python3 tools/r48/place_coherence.py --batch-dir v2/evidence/r48-probe-mock-n16r24-s42

# 全库 + 落 JSON
python3 tools/r48/place_coherence.py --glob 'v2/evidence/*/run.jsonl' --json-out /tmp/r48_all.json

# 当前树 mock 批的复现（如需重跑）
bash tools/d5/preflight.sh --tag r48-probe-mock
setsid bash tools/d2/run_batch.sh \
  --out-dir v2/evidence/r48-probe-mock-n16r24-s42 \
  --seed 42 --agents 16 --rounds 24 --mock \
  --side-root /tmp/r48_probe_mock_side > /tmp/r48_probe.log 2>&1 &
```
