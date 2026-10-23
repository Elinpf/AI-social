# D-2. 4 张截图溯源核验（**CYCLE-14 已入库图，非本周期新渲染**）

> **首要声明（必须与图同屏引用）**：本文件核验的 4 张 PNG 是 **CYCLE-14 已入库的展示材料**（首次落盘 `2026-10-24T04:05`，随 `4e20256`/`6c8a70d` 入库），**不是本周期（CYCLE-15）新渲染**。本周期**未起任何新渲染**（零 LLM、零跑批、零 Chromium 截图）。若需新渲染，必须先向 Leader 报备并另立证据名，**不得顶替原件**。

## D-2.0 目录与共同指纹

| 件 | 路径 | 实测 sha256 |
|---|---|---|
| 渲染报告 | `v2/evidence/d12i_readings_20261024/shots/render_report_D12-I.json` | `0e345dbaad9f1b305d5f9005992c3f30b6bb112c171f066d5698262710b9d8a6` |
| 渲染日志 | `v2/evidence/d12i_readings_20261024/shots/render.log` | `1c86e304a23714189b5ece10b111ec5a5f37bbc3ec75e5d5b65701134de51755` |
| threads 中间件 | `v2/evidence/d12i_readings_20261024/shots/threads_D12-I.json` | `312c4d7ca6cd97ad1037a45e233c81fcf1b983804273ee99a125c7ea8c5a1655`（6,053,846 B / 169 线程 / 510 消息） |
| 来源日志 | `.worktrees/d12i-aligned/v2/evidence/run_d12i_aligned_n16r60_seed42/run.jsonl` | `72c0ca97fe6e38632f67e3b2810c65126c0d15d296d068b521dfbb45c8f5d0c4` |

自洽性核验（本周期实跑）：

```bash
cd /root/.jiuwenswarm/agent/workspace/work/尝试/social-experiment/v2/evidence/d12i_readings_20261024
sha256sum -c SHA256SUMS | tail -20        # 期望 18 项全 OK（本周期实跑：18/18 OK）
sha256sum shots/*.png                     # 与下表逐位比对
```

`render_report_D12-I.json` 自陈字段：`log_sha256 = 72c0ca97…d0c4`（= 来源日志）、`threads_json_sha256 = 312c4d7c…1655`（= 中间件）、`ok_count = 4`、`fail_count = 0`、`generated_at = 2026-10-24T04:05:40+08:00`。三个 sha 与实物逐一相符 ⇒ **确为「真实日志 → gen_threads → 静态服务 → shot.py 现场截图」链路产物，非拼图、非手改**。

## D-2.1 逐图六元组

| # | 路径（`v2/evidence/d12i_readings_20261024/…`） | 视图 / 参数 | 尺寸 / 字节 | 图片 sha256 | 渲染来源日志 sha256 | 证据状态 |
|---|---|---|---|---|---|---|
| S-1 | `shots/D12-I-chat-72c0ca97.png` | `view=chat`，`--width 1400 --height 900` | 1400×900 / 290,381 | `d4883c4374886370141cff7931f9b1b171b9eb6d6e7efac273e4c75567eae5af` | `72c0ca97fe6e38632f67e3b2810c65126c0d15d296d068b521dfbb45c8f5d0c4` | **已验证（sha）/ CYCLE-14 已入库** |
| S-2 | `shots/D12-I-rhythm-72c0ca97.png` | `view=rhythm`，`1300×1050` | 1300×1050 / 282,110 | `2c942d858e917663ea1406819af1219bff72ad8c373564f212b35e2ebb1c7d8f` | 同上 | **已验证（sha）/ CYCLE-14 已入库** |
| S-3 | `shots/D12-I-spread-72c0ca97.png` | `view=spread`，`1400×1000`；**本批 refs 为空态** | 1400×1000 / 178,501 | `9f0a6bd660c15d691dd7e86e790bc7ae4c72758781f178805d36bf7ab84827f2` | 同上 | **已验证（sha）/ CYCLE-14 已入库** |
| S-4 | `shots/D12-I-chat_thread-72c0ca97.png` | `thread=TH-P004-P002-0`，`1200×1000` | 1200×1000 / 301,761 | `f14fbe84c4eed8974f6ce177533f78170fb73df9f8c9c8c40ef9e36b4f1ebc90` | 同上 | **已验证（sha）/ CYCLE-14 已入库** |

- 四张图 `pixel_selfcheck.status` 均 `OK`（`distinct_colors ≥ 200` 且 `top_color_frac ≤ 0.99`），逐图数值见 `render_report_D12-I.json.views[*].pixel_selfcheck`（例如 S-1：`distinct_colors=24216`、`top_color_frac=0.1417`、`non_bg_frac=0.582`）。
- 文件名后缀 `-72c0ca97` = 来源日志 sha8，可作为「图 ↔ 日志」的肉眼对应。
- S-4 的 `thread=TH-P004-P002-0` **正是** `dialogue_excerpts.md` 的案例 1（秀娘 × 老石 6 轮），可直接图文互证。

## D-2.2 两条残留限制（须与图同屏，沿用 CYCLE-14 原文口径）

1. **PNG 非逐位确定**：同一渲染链首轮 `chat = 7cf10530…`、`rhythm = 09142166…`，后续轮为 `d4883c43…` / `2c942d85…`（`spread` 三轮一致）；⇒ 图片指纹以 `render_report_D12-I.json` 与 `SHA256SUMS` 为准，**重跑可能出不同 sha 的等价图**。本文件核的是**已入库这一版**的实际 sha。
2. **四张图均不参与任何判据**（展示材料）。`spread` 视图因本批 `refs = []`（引用边为空）呈空态，属 `描述性读数（空态）`，**不得**读作「传播失败」。

## D-2.3 边界

- 本周期**未新增/未替换任何 PNG**，`v2/evidence/d22_partner_choice/` 下**不含**图片文件，避免以副本冒充新渲染。
- 本文件只做「sha 比对 + 三件自洽性」核验，**未复跑 Chromium**（复跑即为新渲染，需报备，故不做）。
- 证据状态：**已验证（sha 比对）/ 非本周期产物**。
