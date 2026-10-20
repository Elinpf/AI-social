# G-1 形态测量脚本（g1_form_metrics.py）· 可信度自测与代码路径自测

> **性质声明**：本文件所有数字**不是本轮读数**，全部取自**既有恒温基线日志** `v2/evidence/run_d2_after_n16_seed42/run.jsonl`（A0 臂，n16r84，686 条，非本轮两臂）。
> 用途仅两项：① 证明 form 脚本的命中原语与 `g_metrics.py` **同源**；② 证明 M3 相关分支**不是恒值/恒 n/a**（三种分支各真实触发一次）。
> 采集时刻：2026-10-21 06:16–06:17 (+08:00)。跑批进程：`pgrep -fa "orchestration[ ]run"` → 空（rc=1）。零 LLM、零计费。

## 1. 与 g_metrics.py 同源（硬证明）

命令（仓库根）：

```bash
python3 v2/evidence/g1_form_metrics.py \
    --run v2/evidence/run_d2_after_n16_seed42/run.jsonl \
    --tag b0 --sha8 test0000 --no-list \
    --out-json /tmp/fm2.json --out-md /tmp/fm2.md
```

期望（独立复算已知值，report-writer 06:07 单独算得）：G-1 = **412 / 686**。

实际输出（原文）：

```
[ok] b0 msgs=686 hits=412 tie_agents=[] -> /tmp/fm2.json
```

⇒ `msgs=686`、`total_hits_all_agents=412`，与 `experiments/gossip-third-party/g_metrics.py` 的 A0 读数**逐位一致**。
命中原语复用了 `g_metrics.py` 的 `load_names / load_run / participants_of / names_in`（`importlib` 直接加载同一文件），因此不存在"另一套口径"。

## 2. M3 三分支与 M4 各真实触发一次（非恒值证明）

> **代码路径自测**：A0 提示词**没有**名单，因此下表 `order_score` 里的 `L` 是脚本为验证代码路径临时构造的（按 `sorted(display_name)` 码点序），**无任何语义，不得作为读数引用**。

命令：

```bash
python3 v2/evidence/g1_form_metrics.py \
    --run v2/evidence/run_d2_after_n16_seed42/run.jsonl \
    --tag treat --sha8 test0000 \
    --out-json /tmp/fm_treat.json --out-md /tmp/fm_treat.md
```

实际输出（原文，节选）：

| agent | total_hits | k | C(k,2) | M1 | M2 | order_score | 备注 |
|---|---|---|---|---|---|---|---|
| P001 老周 | 14 | 6 | 15 | 0.4286 | 0.2857 | **0.5333** | 正常算出（inv=7） |
| P002 老石 | 12 | 6 | 15 | 0.5 | 0.3333 | **n/a** | 并列首个命中 ⇒ tie_agents=['P002'] |
| P003 阿禾 | 20 | 9 | 36 | 0.45 | 0.3 | **0.6667** | 正常算出（inv=12） |
| P004 秀娘 | 28 | 14 | 91 | 0.5 | 0.2857 | n/a | 名单外命中共 2 条（见下） |

```
[ok] treat msgs=686 hits=412 tie_agents=['P002'] -> /tmp/fm_treat.json
```

三个分支各自触发：①`order_score` 正常算出（0.5333 / 0.6667 两个不同值 ⇒ 不是常数）；②并列 tie 判定真实生效（P002 → n/a）；③`hits_outside_hint` 非零（P004=2、P007=2，合计 **4 条消息**）。

## 3. M4 补充事实：A0 基线里的「未实例化名字」命中

- n16 世界实例化 `pids = sorted(personas)[:16]`（P001–P016）；未实例化 4 人：**书言 P017 / 弦歌 P018 / 石头 P019 / 阿散 P020**。
- A0（686 条）中命中未实例化名字的**提及次数**：`{'石头': 4}`（其余 3 人 0 次），按**消息条数**计为 `hits_outside_hint`：P004=2、P007=2 ⇒ 合计 4 条。
- 解释边界：说明「提未实例化名字」并非本轮两臂特有现象；该 4 人在本轮世界内**不存在、无位置事件** ⇒ 按「宁漏不虚增」不计入 G-1b 越界，故单独列。**A0 数据不参与本轮两臂任何比较。**

- **这条事实的作用（先验，决定 M4 的解释力）**：在**无名单**条件下（A0），未实例化名字 `石头` 也被提及 4 条 ⇒ 「未实例化名字被提到」不是本轮新现象，而是基线就存在的能力。
  因此 M4 只有在**两臂对比**下才有解释力：
  - A0/基线 > 0 且 G1 = 0 ⇒ 处理臂输出被名单**收窄**（模型改为照名单念，不再自发提世界外的人）；
  - 两臂皆 0 ⇒ 该列无信息（不是"干净"，只是没现象）；
  - G1 > 0 ⇒ 名单未压制自发提及，M4 不支持"读名单"解释。
  M4 一律**仅作形态登记**，不作 F5 判据、不作改善结论依据。

## 4. 复算入口（全部只读）

```bash
# 形态测量（本轮两臂，跑完才有正式数）
python3 v2/evidence/g1_form_metrics.py --run v2/evidence/run_g1_b0_n16r60_seed42/run.jsonl \
    --tag b0 --sha8 <sha8> --no-list --out-json v2/evidence/g1_form_metrics_b0_<sha8>.json
python3 v2/evidence/g1_form_metrics.py --run v2/evidence/run_g1_treat_n16r60_seed42/run.jsonl \
    --tag treat --sha8 <sha8> --out-json v2/evidence/g1_form_metrics_treat_<sha8>.json
# G 系列读数（含 ci95_pct，wilson 闭式）
python3 experiments/gossip-third-party/g_metrics.py \
    --run B0=v2/evidence/run_g1_b0_n16r60_seed42/run.jsonl \
    --run G1=v2/evidence/run_g1_treat_n16r60_seed42/run.jsonl \
    --out-json v2/evidence/g_metrics_g1_two_arms.json
```
