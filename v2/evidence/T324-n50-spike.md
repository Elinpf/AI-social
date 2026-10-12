# T324 · N=50 mock 复测（去全扫改造后）—— 先碎在哪里

**日期** 2026-10-13 · **作者** kernel-dev · **sha** `352e9a4` · **性质** 只诊断（未改 `code/`）
**口径**：**mock（非真 LLM）· 非证据级（参考值）**；`N50_VEC=0`；`ulimit -v 16G`；`/usr/bin/time -v` 采 peak RSS；独立进程。

## 0. 结论（先给）

1. **去全扫改造显著改善**：**N=50×24 现可完成**（368.3s / RSS 824MB / 373,818 事件）—— 而 **T223 旧读数 N=50×84 单核 >66min 未完成**。
   - 单回合：**N=20 0.82 s/round（新） vs 3.12 s/round（T223 旧）≈ 3.8×**；**N=50 15.35 s/round（新） vs >47 s/round（旧下界）⇒ ≥3.1×**。
   - 外推 N=50×84 ≈ **21.5 min**（旧 >66min 且未完成）⇒ **N=50 单核从"跑不完"变为"约 20 分钟/周"**。
2. **仍未线性**：N=20→50 事件数 ×7.19（≈O(N²)，与 T254 的 pairwise 根因一致）；**单回合墙钟 ×18.7 > 事件比** ⇒ 仍有**超线性**（内存/GC/常量），**N=50 内存 824MB@24r（旧 345MB@N20）**。
3. **先碎（当前树）= 计算仍集中在 `visibility` + 若干残余全扫**（见 §3）。**内存不是当前先碎点**（16G cap 未触，available 充裕）。

## 1. 实测（当前树 `352e9a4`，seed=42，rounds=24）

| | N=20 | N=50 | 比 |
|---|---:|---:|---:|
| **run 秒** | **19.69** | **368.32** | 18.7× |
| **s/round** | **0.82** | **15.35** | 18.7× |
| wall（含启动） | 0:24.15 | 6:40.47 | — |
| **peak RSS** | **144 MB** | **824 MB** | 5.7× |
| events | 52,006 | 373,818 | 7.19× |
| `unknown_event_types` | [] | [] | ✓ |

命令（可复现）：
```bash
cd social-experiment && ulimit -v 16777216
cd code && export N50_VEC=0
/usr/bin/time -v python -c "from orchestration.integration import run_e2e; print(run_e2e(seed=42,rounds=24,n=50,cleanup_side=False))"
```

## 2. 与 T223 / T254 旧读数对照

| 量 | T223/T254 旧（早于去全扫） | 本测（`352e9a4`） | 判定 |
|---|---|---|---|
| N=20 单回合 | 3.12 s/round（×84=261.8s） | **0.82 s/round** | **改善 ≈3.8×**（去全扫：T264/T295/T312）|
| N=50 单回合 | **>47 s/round（未完成）** | **15.35 s/round** | **改善 ≥3.1×**（下界比较）|
| N=50×84 可完成性 | **否（>66min）** | 外推 ≈21.5min | **从"不可接受"→"约 20min/周"** |
| 事件/`MEMORY_WRITE` 超线性 | ≈O(N²)（pairwise，T254） | 事件 ×7.19（≈O(N²)） | **未变**（属 life 语义，非去全扫范畴）|
| peak RSS | 345MB@N20×84 | 144MB@N20×24 / 824MB@N50×24 | N=20 更低；随 N/回合增长 |
| side 文件超线性 | ≈O(N²)（T223） | 未另测（`N50_VEC=0`） | 未变（同 `MEMORY_WRITE` 源）|

⇒ **去全扫改善的是"N=50 的墙钟可跑性"（3~3.8×）**；**未改善的是"O(N²) 的事件/记忆/侧存增长"（pairwise 根因，属 life 语义，T254 已定位的老账）**。

## 3. 当前热点（cProfile N=50×12，252s）

| 函数 | tottime | 备注 |
|---|---:|---|
| `dict.get` | **72.4s** | 全局底色 |
| `contracts/visibility.py::visible_events` | **31.4s** | 仍居首 ⇒ **仍有路径走 contracts 全扫**（非 T264 索引） |
| `contracts/visibility.py::visible` | 21.2s | |
| `contracts/visibility.py::_group_members` | **16.1s** | 每次重算群成员（O(事件)） |
| `engine/liquidity.py::recent_income` | **15.0s** | 已用累加器，但窗口需遍历窗口内每回合 seq |
| `contracts/visibility.py::location_of` | 7.5s | |
| `life/settlement.py::events_this_round` | 3.4s | **待 T319**（life 端口，已排）|
| `engine/hooks/econ.py::_round_ie_eff` | 3.1s | 已用累加器 |
| `life/memory.py::_tokenize` | 3.7s | 记忆分词 |

**新热点清单（只定位，不改码）**：
1. **`contracts/visibility.*` 仍为首（可见性全扫路径未完全走 T264 索引）** —— 疑似某些调用点仍直接调 `contracts.visible_events`（而非 orchestration 的索引 provider）；**待查哪条路径仍全扫**。
2. **`_group_members` 每次 O(事件) 重算** —— 可随 T312 同法做增量化（`GROUP_*` 折叠表）。
3. **`recent_income` 窗口遍历** —— 累加器已用，但窗口内逐回合 seq 遍历仍有成本；可加"按 agent 的收入标量累加器"。

## 4. 复现与装置

- sha `352e9a4`；命令见 §1；cProfile 见 `/tmp/t324_prof.log`（N=50×12）。
- **并发**：本测与 T319 `make verify` / T300 跑批**错开**（开跑时空载、available 16G）；**独立进程**；`ulimit -v 16G`，**未触上限**。
- **非证据级**：mock + 参考值；事件/内存随回合累积，**外推值标注为估计**。
