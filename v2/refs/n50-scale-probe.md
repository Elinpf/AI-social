# T223 · N=50 规模探测 —— 「到 50 会先碎在哪里」

> **状态：未跑（前置缺口阻塞）**。探测性跑批，**非证据级**。
> 运行登记：`[DIRTY — 参考值]`（并发编辑中，dirty_files≈34）· sha 见各命令 · provider=mock（计划）。
> **结论一句话：N=50 还没跑，就已经找到一个 50 规模的真缺口 —— 它自己跑不起来（inode）。**

---

## 1. 为什么没跑（前置缺口）
现状 `side` 存储：`life/memory.py:113-153 SideStore` 每个 memory 落 **2 个文件**：
- `side/mem/<agent>/<mem>.txt` = **内容正文（数据资产，留）**
- `side/mem/<agent>/<mem>.vec` = **嵌入（派生、可重算，可关）**

**实测标定**：N=20 canon `MEMORY_WRITE=47,742` → **≈95k 文件**；**N=50 → ≈187k 文件**（与本机实测 `side_n50_probe` 的 187,202 个文件吻合）。
→ **现状跑 N=50 必然再写 ~187k 文件，把 inode 吐满**（本机 fs 仅 1625 万 inode，且已被历史残留吃近 9 成）。
→ **前置 = `T228-side-persist-tier`（`.vec` 可分档关/懒算）**；**另需 life 层加 `side_persist` 开关**（现状 `side_root` 只能改目录、不能关）。

## 2. 开跑前预检（**按 N 估算**，替换原固定常量）
```
est_files = N × WRITES_PER_AGENT(2387) × FILES_PER_WRITE(2；T228 后=1)
est_bytes = est_files × 4KB + 200MB 余量
放行条件：free_inodes ≥ est_files×1.3  且  free_bytes ≥ est_bytes
```
**为何是"估算"而非"常量"**：**side 需求随 N 线性增长**，任何固定阈值（如原 `≥150k inode`）在规模变化时**必然失效** —— 这正是 T136 两次失败 + 本次危机的共同形状（**用一次性数字去挡一个会变大的量**）。
**反向验证**：用真实空闲 inode 跑预检 → `est_files=238,700`，`free_inodes=8,657` → **`PRECHECK FAIL`，成功拦下**（新预检真的会把 N=50 挡在门外）。

## 3. ⭐「50 规模缺什么」清单（按阻塞度排序）
| # | 缺口 | 阻塞度 | 证据/位置 | 归属 |
|---|---|---|---|---|
| **G1** | **side 每 memory 2 文件 → N=50 ~187k inode** | **阻塞：跑不起来** | `life/memory.py:113-153`；本机 `side_n50_probe`=187,202 文件 | **T228**（前置） |
| **G2** | **无 side 分档开关**（`side_root` 只改目录） | **阻塞：无法只关 `.vec`** | `orchestration/integration.py:680-684` | life 加 `side_persist` |
| **G3** | **临时 side 无清理**（`mkdtemp` 异常路径漏清） | 高：**漏一次毁整机** | `/tmp/hitt_side_*` 残留 **1431 万文件/3428 目录** | T228（owner 标记+sweeper） |
| **G4** | **成本 O(N²)**（`judge` 指数 1.64 / `importance` 2.64） | 高：真 LLM 下 N=50 很贵 | `v2/refs/scale-50-efficiency.md` §1-2 | **M2b/M1** |
| **G5** | **预检常量化失效**（固定阈值挡不住变大的量） | 中：**已修**（本文件 §2） | `/tmp/n50_probe.py` | obs（已办） |
| **G6** | 并发/分时调度未落地（同回合 N 个 decide 的尖峰） | 中：实时感 | T203 §3（M4） | 待立项 |
| **G7** | **未验证**：N=50 是否触发其它限额（内存 / 事件量 / 单机墙钟） | 未知 | **待真跑探测** | 本任务（跑后填） |
| **G8** | **未验证**：`expand_personas(50)` 生成人设的质量（5 个种子 → 50 人是否同质） | 未知 | `orchestration/integration.py` | 待验证 |

## 4. 下一步
1. 等 **T228**（`.vec` 分档）落地 → **`N50_VEC=0`** 再跑（inode 需求≈减半）；
2. 跑 mock **N=50×84**：填 **G7**（内存/事件量/墙钟/SYSTEM_ERROR/是否碎在别处）+ 复核 **G4** 的 N=50 实测点；
3. 产出「**缺什么**」终版（本文件 §3 升级为实测版）。
> **注意**：本文件是**探测性**，跑出的值标 **`[DIRTY — 参考值]` + sha**，**不作为结论**。

---
_产出：obs-stats-dev · 前置与预检 commit 见 `obs/` 相应 sha；前置阻塞 `T228`。_
