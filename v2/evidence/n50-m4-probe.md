# T254 · N=50 可跑性推进：M4 复探 + side/记忆写超线性根因（只定位）

> **不改 `code/`**（本文件全部为只读定位 + 探针）。探针 `[DIRTY — 参考值]`，sha 见 §4。
> 承接 T223 `c63fec3` 的证据级结论：**当前实现单核 60min 跑不完 N=50×84**；side/`MEMORY_WRITE` ≈ **O(N²)**。

## 0. 结论（先给）
1. **超线性根因已定位（证据）**：`MEMORY_WRITE` 的 **66% 由 `RELATION_CHANGE` 触发**，而 `RELATION_CHANGE{familiarity}` 是**逐"共处对"（pairwise）**产生的 —— **对数 O(N²)**；每条源头事件被 **~2.65 个 agent 各自观察并各写一条记忆**（观察扇出）。⇒ **`MEMORY_WRITE ≈ O(N²) × 常数扇出`**，`side` 文件（vec=0）≈ 1:1 随 `MEMORY_WRITE`。**这就是 N20→N50 `×5.93` 的来源。**
2. **M4（`schedule_enabled`）不是 mock 的墙钟解药**：mock 无 LLM 延迟；但 M4/M6 打开后**经 M6 降级少发 2/3 的 LLM 调用**（3678→1228），**时间只降 ~25%**（39.6→29.8s），**且 `state_hash` 变了（改行为）**。⇒ **M4 削的是"调用数/预算"，不是"side IO 墙"**；对 **N=50 的"跑不完"**，**主因是 side IO + O(N²) 计算**，M4 单独不够。
3. **周期 flush**：`run_e2e` **末尾才写日志** → 超时/被杀 = **0 日志**（T223 即如此）→ **建议并验证周期 flush（需改 code，待批）**。

## 1. 超线性根因（只定位；证据 = N=20 日志 `run_n50probe_n20.jsonl`）
| 事实 | 值 |
|---|---|
| `MEMORY_WRITE` 总数 | 47,742（**observation 47,322** + reflection 420） |
| 每 agent 写数 | 2,207–2,651（≈均匀，20 agent） |
| **observation 的源头事件类型** | **`RELATION_CHANGE` 31,361（66%）**、ACTIVITY_STARTED 5,280、PLACE_ARRIVED 5,006、RELATION_ENCOUNTER 2,905、MSG_PUBLIC 1,280 … |
| `RELATION_CHANGE` 总数 / 分维 | 16,649（**familiarity 15,090**、affinity 1,187、trust 319、respect 53） |
| **distinct familiarity 对** | **210**（N=20 上限 `C(20,2)=190`）→ **逐"共处对"** |
| **观察扇出** | **每条源头事件被 2.65 个 agent 各写一条**（distinct_src=17,883） |

**放大链（call chain）**：
```
每回合：agent 共处 → RELATION_CHANGE{familiarity} × 每对(≈C(N,2)) × 每 slot
        → 每个"看到"该事件的 agent 各写一条 MEMORY_WRITE{kind:observation}   (扇出≈2.65)
        → 每写 → 落 1 个 .txt（vec=0）  ⇒  O(N²) × 2.65 个文件
```
**验证 N20→N50**：对数比 `C(50,2)/C(20,2) = 1225/190 = 6.45` ≈ 实测 `6.26–5.93` ✓（pairwise 解释成立）。

**候选削减点**（**实现另开任务**，本任务只列）：
| # | 削减点 | 预期 | 备注 |
|---|---|---|---|
| a | **`familiarity` 降频**：只在**显著/跨阈值**变化时发 `RELATION_CHANGE`，不逐 slot 逐对 | 直接砍 O(N²) 主项 | 动 life 语义，须 08/审批 |
| b | **观察去重/合并**：同一 `RELATION_CHANGE` 被 2.65 agent 写 → 合并/引用一次 | ÷2.65 | 动 life 记忆语义 |
| c | **observation 类不落 `.txt` 每写一文件**（batch/合并/懒算） | 砍 side inode | T228 提过的 optional `.txt` by kind |
| d | **周期 flush / 批量写**（日志 + side） | 防"kill 丢全部"；IO 合并 | 见 §3 |
| e | **side 默认打包/懒算**（数据资产归档） | inode | T229 口径 |

## 2. M4 复探（mock，N=20×24，config-only 切 `llm_budget.schedule_enabled`）
| | **M4 OFF** | **M4 ON** |
|---|---:|---:|
| 墙钟 | 39.6 s | **29.8 s（−25%）** |
| events | 46,113 | 41,856 |
| **LLM_CALL** | 3,678 | **1,228（−67%）** |
| `MEMORY_WRITE` | 15,539 | 14,867 |
| **`DEGRADE`（M6 降级事件）** | 0 | **24（可观测 ✓）** |
| `state_hash` | `629f6cfb…` | **`e28ca8aa…`（变了）** |

**读法**：
- M4/M6 打开 ⇒ **经 M6 降级少发 2/3 调用、时间降 ~25%**，**降级可观测**（DEGRADE=24）。
- **但 `state_hash` 改变 ⇒ M4 是"改行为"的层，不是免费的加速**（用于 canonical 须显式标注+消融）。
- **对 N=50 的"跑不完"**：mock 墙钟瓶颈是 **side IO（~299k 文件）+ O(N²) 计算**；M4 减的是调用（mock 调用本就便宜），**单独不足以把 >66min 拉到 <60min**。→ **主攻应是 §1 的 O(N²) 削减 + 真并发，而非 M4。**
- **峰值并发"削平"**：mock 为**单核串行**，日志无法直接测"并发峰值"；且 M4 在此实现里是**确定性排序/跳过**、非真并行 → **【未验证】**（需 real-LLM 或真并发接线后测）。

## 3. 周期 flush（**需改 code → 待批**）
**问题**：`run_e2e` 在**结束**时 `write_log(records, out_path)` —— 被 kill/OOM/超时（T223 的 66min 停止）⇒ **日志 = 0**（本次 per-purpose 数据全丢）。
**建议**（**改 `orchestration/integration.py`，非我模块 → 须报 leader/kernel**）：**每 N 回合/flush 间隔周期性 append 写盘**（或 WAL），使中途可读；**side 同理**（批量 flush）。
**验证方式**：跑短 run 并在中途 kill → 断言**已落盘部分日志可读且事件数与回合对应**。**本任务未做（需 code 改）。**

## 4. 复现命令
```bash
cd code
# 根因（N=20 日志）
python -c "import json,collections;recs=[json.loads(l) for l in open('../v2/evidence/run_n50probe_n20.jsonl')];\
mw=[r for r in recs if r['type']=='MEMORY_WRITE'];print(collections.Counter((r.get('payload') or {}).get('kind') for r in mw))"
# M4 on/off（mock N=20×24）
M4=0 python /tmp/m4_probe.py ; M4=1 python /tmp/m4_probe.py
```
- 探针 `sha = 3fc9521`，`[DIRTY — 参考值]`；`run_m4probe_*.jsonl` 已 gitignore。

## 5. 【未验证】/ 待批
- **峰值并发削平**：mock 单核串行、M4 为确定性排序 → **未验证**（需真并发/real-LLM）。
- **N=50 接 M4 后能否 <60min**：mock 下**预计不能**（瓶颈是 side IO/O(N²)），**未实测**（>60min 成本高；建议先做 §1 削减再复探）。
- **周期 flush 效果**：**未做**（需改 `orchestration/`，待批）。
- **§1 候选 a/b 动 life 语义** → 须 08/审批，**未动**。

---

## 6. 补测（决策级）· 2026-10-12 14:xx · sha `d65abf1`（探针在后续工作区，见 §6.6）
### 6.1 CPU vs IO 隔离实验 —— **IO≈0，瓶颈是 CPU**
N=20×24 mock，仅改 side 落盘位置：
| side 位置 | 墙钟 | side 文件 |
|---|---:|---:|
| → **磁盘** | 90.0 s | 32,596 |
| → **/dev/shm（RAM）** | 89.2 s | 32,596 |
→ **IO 等待 ≈ 0.7 s（<1%）**。**写 3.2 万个小文件近乎免费**。
**结论修正**：N=50 的"跑不完"主因是 **O(N²) CPU**（per-agent 反复重扫事件），**不是 "side IO 墙"**；299k 文件的 inode 压力是**症状**、非主因。
### 6.2 CPU 热点与定位（cProfile，N=20×24）
- 头号：**`visible_events`（`life/visibility.py:42`）+ `location_of`（`:13`）** —— 每 (agent, 回合) 调用时**全量重扫 `records`（≤upto_round）** → **11.2M 次 `_visible`（`:26`）**、全局 **158M 次 `dict.get`**。
- 其余：`write_memories`(`settlement.py:570`) 23s；流动性 `credit_limit`/`recent_income` 13.5s；canonical 哈希 8–9s。
- **回合内也超线性**：N=20 墙钟 **R=24→~40s**、**R=84→390s**（回合 ×3.5 → 时间 ×9.75）：因**每回合重扫"增长的日志"** ⇒ 复杂度 ≈ `O(N × log_len × rounds)` ≈ **O(N²·rounds²)** 量级。
- engine 双胞胎 **`engine/perceive.py:41`（visible_events）/ `:28`（location_of）** 同型（`perceive` 每 agent 一次，l.108/111）。
- **同族提示**：`visible_events` 亦为"同一概念两处实现"（`engine/perceive` ↔ `life/visibility`），与 T257（两个 truth 模块）同族。
### 6.3 内存累积（**第二根因，已实证**）
N=20×84 RSS 采样（`ulimit -v 8G`）：
- **曲线**：20 → 85 → … → 448 MB（每 ~6 采样点），**peak 493 MB**；**单调上升、无平台**。
- **≈ 每回合 +5 MB（N=20）**；外推 N=50（且 O(N²)）→ **GB 级** → **与宿主 OOM（被杀进程 `anon-rss 23.2GB`）方向一致**。
- **判定**：**按回合无界累积**（疑记忆/side 缓冲），**比文件数超线性更危险**（会 OOM 宿主）。**只定位、未改**。
### 6.4 周期 flush —— **已由 T262 落地**（kernel-dev，sha `7ccd35e`）
`run_e2e(..., flush_every=N)`：每 N 回合原子落盘**已提交前缀**（临时文件+`os.replace`）；**默认 0 = 末尾写、字节不变**；真 `SIGKILL` 中途 → 前缀**非空且可 `replay`**（正向），旧行为 `flush_every=0` **丢全部**（反向，证明缺陷真实）。建议长跑 `--flush-every 12`。**本任务仅提供触发场景/复现（§3），实现归 kernel。**
### 6.5 削减候选 · **Leader 裁决**
| # | 候选 | 动语义? | 裁决 |
|---|---|---|---|
| **c2** | visibility **每回合索引一次**，消 11.2M 重扫 | 否 | **✅ 批准·首选**（实施另开任务；需 file:line 定位，见 §6.2） |
| c1 | 共享不可变源事件 + 每 agent 指针 | 否 | ✅ 批准（**等价搬迁：输出逐字节不变**） |
| c3 | 流动性 credit_limit/recent_income 每回合 memo | 否 | ✅ 批准（同上） |
| c4 | observation 类不逐写一文件（批量/懒算） | 否 | ✅ 批准（同上） |
| c5 | `familiarity` pairwise 稀疏化/阈值化 | **是** | ❌ 不批（等 T263 时间模型 + 08 登记 + 用户） |
| c6 | 观察扇出合并 2.65→1 | **是** | ❌ 不批（同上） |
| — | 多核/多进程（16 核） | — | **先记不做**（先消 O(N²)；多核与"全量日志"纪律有张力） |
### 6.6 运行环境记录
- 主机 **16 核 / 31 GiB**；探针前 `free -h`：used 12Gi / **avail ~20Gi**；`df -h /` 103G 空闲、`df -i` 46%。
- **停批纪律**：本补测未跑 >N=20 未加限的批次；内存探针加 `ulimit -v 8G`。**>N=20 必报 leader + 设 MemoryMax。**
